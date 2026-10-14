"""Raw physical arm evidence; measured outcomes, never counterfactual labels."""
from datetime import datetime
from experiment_validation import require
from statement_timing import completed_statements
from query_observation_binding import verify_observations
from engine_overlap import task_intervals,overlap_evidence


def audit_arm(rows,cfg,measured,requests,jobs,stages,rest,lo,hi,registered_source):
    table=cfg['destination_table'];arm=cfg['action_arm']
    initial=[r for r in rows if r['kind']=='common_horizon_initial_state'];final=[r for r in rows if r['kind']=='common_horizon_final_state']
    require(len(initial)==len(final)==1,'Missing arm state boundaries')
    initial,final=initial[0],final[0]
    def files(state):
        mid=state['file_inventory_measurement_id'];snap=state['snapshot_measurement_id']
        require(requests[mid]['sql']==f'SELECT file_path, record_count, file_size_in_bytes FROM {table}.files' and requests[snap]['sql']==f'SELECT snapshot_id FROM {table}.history ORDER BY made_current_at DESC LIMIT 1','Unbound arm inventory')
        data=measured[(cfg['experiment_id'],mid)]['rows'];require(measured[(cfg['experiment_id'],snap)]['rows']==[[state['snapshot_id']]],'Snapshot summary differs')
        require(state['file_state']=={'file_count':len(data),'record_count':sum(r[1] for r in data),'total_bytes':sum(r[2] for r in data)},'File state summary differs')
        return data
    before,after=files(initial),files(final)
    require(initial['file_state']['record_count']==final['file_state']['record_count'],'Row count changed')
    validations=[r for r in rows if r['kind']=='common_horizon_multiset_validation'];require(len(validations)==2,'Missing original/final multiset proofs')
    sources=[r for r in rows if r['kind']=='common_horizon_source'];require(len(sources)==1,'Missing/extra registered source')
    source=sources[0];require(source['table']==registered_source['table'] and source['snapshot_id']==registered_source['snapshot_id'],'Source identity differs from preparation receipt')
    require(initial['file_state']['record_count']==registered_source['record_count'] and initial['file_state']['file_count']==cfg.get('initial_file_count',registered_source['file_count']),'Initial layout differs from source declaration')
    for validation,state in zip(validations,(initial,final)):
        mid=validation['measurement_id'];expected=f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {table} VERSION AS OF {state['snapshot_id']}) UNION ALL (SELECT * FROM {table} VERSION AS OF {state['snapshot_id']} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences"
        require(validation['snapshot_id']==state['snapshot_id'] and requests[mid]['sql']==expected and measured[(cfg['experiment_id'],mid)]['rows']==[[0]],'Raw multiset proof differs')
    checkpoints=[r for r in rows if r['kind']=='common_horizon_checkpoint']
    require([r['offset_ns'] for r in checkpoints]==cfg['metadata_checkpoint_offsets_ns'],'Missing/extra checkpoint schedule')
    for checkpoint in checkpoints:require(checkpoint['recorded']['monotonic_ns']>=lo+checkpoint['offset_ns'],'Checkpoint before registered time')
    actions=[r for r in requests.values() if r['role']=='maintenance']
    observations=[r for r in rows if r['kind']=='query_observation']
    known={initial['snapshot_id'],final['snapshot_id']}
    require(all(r['table']==table and r['snapshot_id'] in known for r in observations),'Unbound query snapshot')
    maintenance=None;rewrite_tasks=[]
    if arm=='no_maintenance':
        require(not actions and initial['snapshot_id']==final['snapshot_id'] and sorted(before)==sorted(after),'Null arm changed or maintenance occurred')
    else:
        require(len(actions)==1,'Missing/extra actual maintenance call')
        action=actions[0];record=measured[(cfg['experiment_id'],action['measurement_id'])]
        offset=cfg['action_offset_ns'];require(lo+offset<=record['client_execute_start']['monotonic_ns']<hi,'Action outside registered horizon')
        require(initial['snapshot_id']!=final['snapshot_id'],'No actual snapshot transition')
        decisions=verify_observations(rows,cfg,kind='maintenance_decision_observation');require(len(decisions)==1 and decisions[0]['snapshot_id']==initial['snapshot_id'],'Missing original fresh actual action decision')
        values=dict(zip(record['columns'],record['rows'][0]));require(values['rewritten_data_files_count']>0 and values['rewritten_bytes_count']>0,'No useful rewrite; preserve attempt, refuse successful transition claim')
        require(final['file_state']['file_count']==initial['file_state']['file_count']-values['rewritten_data_files_count']+values['added_data_files_count'],'File conservation failed')
        rewrite_tasks=task_intervals(jobs,stages,rest,rewrite_table=table,request=record)
        maintenance={'measurement_id':action['measurement_id'],'registered_offset_ns':offset,'actual_start_offset_ms':(record['client_execute_start']['monotonic_ns']-lo)/1e6,'client_elapsed_ms':record['client_elapsed_ns']/1e6,'completed_within_horizon':record['fetch_end']['monotonic_ns']<=hi,'rewrite_result':values,'decision_observation_checks':decisions}
    exposures=[]
    for observation in observations:
        query=measured[(cfg['experiment_id'],observation['measurement_id'])]
        exposure=overlap_evidence(task_intervals(jobs,stages,rest,marker=query['marker']),rewrite_tasks) if rewrite_tasks else {'verified_task_lifetime_overlap':False,'overlap_seconds':0,'meaning':'No maintenance call in registered null arm'}
        exposures.append(dict(measurement_id=query['measurement_id'],snapshot_id=observation['snapshot_id'],**exposure))
    available=[initial]+[r for r in rows if r['kind'] in ('common_horizon_checkpoint','common_horizon_state_published') and r['recorded']['monotonic_ns']<=hi]
    latest=available[-1]
    boundary_maintenance='not_attempted' if maintenance is None else ('completed' if maintenance['completed_within_horizon'] else 'in_flight')
    return {'maintenance_at_horizon':boundary_maintenance,'available_layout_at_horizon':latest['file_state'],'available_snapshot_at_horizon':latest['snapshot_id'],'action_arm':arm,'initial_file_state':initial['file_state'],'final_file_state':final['file_state'],'initial_layout_signature':sorted([r[1:] for r in before]),'initial_snapshot_id':initial['snapshot_id'],'final_snapshot_id':final['snapshot_id'],'maintenance':maintenance,'query_task_exposures':exposures,'accepted_for_cost_training':False,'scope':'Registered physical arm diagnostic, not causal counterfactual or scheduler/model approval'}
