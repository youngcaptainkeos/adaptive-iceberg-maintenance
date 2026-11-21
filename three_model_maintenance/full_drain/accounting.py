"""Raw full-population response and rewrite obligation reconstruction.

This report alone certifies no engine, host-counter or correctness gate.
"""
import csv
import json
from pathlib import Path
from three_model_maintenance.research.common import decode, integer, read, require, sha, utc
from three_model_maintenance.research.accounting import _area, nearest_rank
from .contract import validate
from .study import verify_study


def reconstruct(directory):
    root=Path(directory);cfg=validate(read(root/'config.json'))
    mapped=list(csv.DictReader((root/'mapped_arrivals.csv').open()))
    require(sha(root/'mapped_arrivals.csv')==cfg['inputs']['mapping']['sha256'],'Mapping differs')
    require(len(mapped)==cfg['arrival_count'] and len({r['source_query_id'] for r in mapped})==len(mapped),'Wrong cohort')
    source={r['source_query_id']:r for r in mapped};events=[decode(s) for s in (root/'events.jsonl').read_text().splitlines()]
    protocols=[e for e in events if e['kind']=='full_drain_protocol']
    require(len(protocols)==1 and protocols[0]['configuration']==cfg and protocols[0]['protocol_sha256']==sha(root/'config.json'), 'Raw protocol differs')
    study=verify_study(cfg)
    require(utc(study['registered_utc'])<utc(protocols[0]['recorded']['utc']),'Retrospective study registration')
    require(all(r['experiment_id']==cfg['experiment_id'] for r in events),'Mixed experiment ledger')
    require(not any(r['kind'] in ('statement_failed','statement_not_submitted','full_drain_failed',
                'full_drain_thread_failed','spark_rest_failed') for r in events),'Failed/incomplete episode')
    clocks=[r for r in events if r['kind']=='full_drain_clock'];require(len(clocks)==1,'Missing/duplicate clock')
    clock=clocks[0];lo=integer(clock['start_monotonic_ns'],'start');hi=integer(clock['arrival_end_monotonic_ns'],'arrival end')
    cutoff=integer(clock['dispatch_end_monotonic_ns'],'dispatch cutoff')
    require(hi-lo==cfg['horizon_ns'] and hi<cutoff,'Boundary contract differs')
    requests={};calls={};states={};times={};mids={};order=[];active=None
    for e in events:
        kind=e['kind']
        if kind=='statement_requested':
            mid=e['measurement_id'];require(mid not in requests,'Duplicate request');requests[mid]=e
        elif kind=='statement_completed':
            mid=e['measurement_id'];require(mid not in calls,'Duplicate completion');calls[mid]=e
        elif kind=='queue_transition':
            row=e['source'];sid=row['source_query_id'];state=e['state'];old=states.get(sid)
            require(sid in source and row==source[sid] and old==e['previous_state'],'Queue/source mismatch')
            require((old,state) in ((None,'offered'),('offered','queued'),('queued','dispatched'),('dispatched','completed')),
                    'Illegal/failed/incomplete queue chain')
            ns=integer(e['actual_transition']['monotonic_ns'],'transition')
            require(ns<=integer(e['recorded']['monotonic_ns'],'publication'),'Future transition')
            due=lo+int(row['offset_ns']);require(lo<=due<hi and due==e['scheduled_monotonic_ns'],'Retimed source')
            mid=e['measurement_id']
            if state=='offered':
                require(ns>=due and mid not in mids.values(),'Arrival/identity mismatch');mids[sid]=mid;times[sid]={}
            require(mids[sid]==mid and ns>=max([due,*times[sid].values()]),'Changed identity/reversed clock')
            if state=='dispatched':
                require(active is None and ns<cutoff,'Busy/late serial dispatch');active=sid;order.append(sid)
            require(e['session_id']==('query_0' if state in ('dispatched','completed') else None),'Changed foreground session')
            if state=='completed':require(active==sid,'Wrong active slot');active=None
            states[sid]=state;times[sid][state]=ns
    require(set(requests)==set(calls),'Unfinished/unrequested statement in terminal ledger')
    require(active is None and set(states)==set(source) and all(s=='completed' for s in states.values()),'Full cohort not drained')
    require(order==[r['source_query_id'] for r in mapped],'FIFO changed')
    trace={m:c for m,c in calls.items() if c['role']=='trace_query'}
    require(set(trace)==set(mids.values()),'Extra/missing trace completion')
    rows=[];intervals=[]
    for sid in order:
        mid=mids[sid];c=trace[mid];req=requests[mid];t=times[sid];a=lo+int(source[sid]['offset_ns'])
        start=integer(c['client_execute_start']['monotonic_ns'],'call start');end=integer(c['fetch_end']['monotonic_ns'],'fetch end')
        require(req['role']==c['role'] and req['marker']==c['marker'],'Call binding differs')
        require(req['query_id']==c['query_id']==int(source[sid]['query_id']),'Query mapping differs')
        require(t['offered']<=t['queued']<=t['dispatched']<=start<end<=t['completed'] and start<cutoff,'Invalid call chronology')
        require(utc(c['client_execute_start']['utc'])<utc(cfg['no_new_operation_after_utc']),'Query started after SQL cutoff')
        service=end-start;require(service==integer(c['client_elapsed_ns'],'client elapsed'),'Service clock mismatch')
        rows.append(dict(source_query_id=sid,measurement_id=mid,query_id=c['query_id'],arrival_ns=a,
                         response_ns=end-a,wait_ns=start-a,service_ns=service,
                         generator_lateness_ns=t['offered']-a,finished_ns=end))
        intervals.append((a,end))
    actions=[c for c in calls.values() if c['role']=='maintenance']
    require(len(actions)==cfg['required_rewrites']==1,'Required rewrite missing or duplicated')
    action=actions[0];a=action['client_execute_start']['monotonic_ns'];b=action['fetch_end']['monotonic_ns']
    require(lo+cfg['action_offset_ns']<=a<=lo+cfg['latest_action_offset_ns'] and a<cutoff and a<b,'Action start window differs')
    require(utc(action['client_execute_start']['utc'])<utc(cfg['no_new_operation_after_utc']),'Rewrite started after SQL cutoff')
    require(action['client_elapsed_ns']==b-a,'Rewrite duration clock mismatch')
    require(action['rows'] and len(action['rows'])==1 and type(action['rows'][0][0]) is int
            and action['rows'][0][0]>0,'No useful physical rewrite result')
    decision=[e for e in events if e['kind']=='full_drain_action_due'];require(len(decision)==1,'Missing/duplicate start decision')
    require(decision[0]['registered_offset_ns']==cfg['action_offset_ns'] and
            lo+cfg['action_offset_ns']<=decision[0]['recorded']['monotonic_ns']<=a,'Action decision chronology differs')
    finished=[e for e in events if e['kind']=='full_drain_work_complete'];require(len(finished)==1,'Completion boundary missing')
    query_end=max(e for _,e in intervals);operation_end=max(query_end,b)
    require(finished[0]['offered']==finished[0]['completed']==len(mapped) and finished[0]['completed_rewrites']==1,'Completion counts differ')
    require(finished[0]['recorded']['monotonic_ns']>=operation_end,'Operational boundary ended before required work')
    response=sum(r['response_ns'] for r in rows);wait=sum(r['wait_ns'] for r in rows);service=sum(r['service_ns'] for r in rows)
    require(response==wait+service==_area(intervals),'Full-cohort conservation failed')
    initial=[e for e in events if e['kind']=='full_drain_initial_state'];final=[e for e in events if e['kind']=='full_drain_final_state']
    require(len(initial)==len(final)==1,'Layout boundaries missing')
    require(initial[0]['file_state']['file_count']==cfg['initial_file_count'] and
            initial[0]['file_state']['record_count']==final[0]['file_state']['record_count'],'Initial/terminal population differs')
    checks=[e for e in events if e['kind']=='full_drain_multiset']
    require(len(checks)==2 and {c['snapshot_id'] for c in checks}=={initial[0]['snapshot_id'],final[0]['snapshot_id']},'Missing initial/final multiset proof')
    for check in checks:
        c=calls[check['measurement_id']];require(c['rows']==[[0]],'Nonzero multiset difference')
    return dict(status='reconstructed_full_cohort_and_rewrite_only',experiment_id=cfg['experiment_id'],
                comparison_id=cfg['comparison_id'],block_id=cfg['block_id'],source_family=cfg['source_family'],
                offered=len(mapped),completed=len(rows),failed=0,unfinished=0,required_rewrites=1,completed_rewrites=1,
                sum_response_ns=response,sum_wait_ns=wait,sum_service_ns=service,outstanding_area_ns=_area(intervals),
                mean_response_seconds=response/len(rows)/1e9,
                response_quantiles_seconds={str(p):nearest_rank([r['response_ns'] for r in rows],p)/1e9 for p in (.5,.95,.99)},
                arrival_horizon_seconds=(hi-lo)/1e9,post_arrival_query_drain_seconds=max(0,query_end-hi)/1e9,
                work_completion_after_start_seconds=(operation_end-lo)/1e9,
                recorded_work_boundary_after_start_seconds=(finished[0]['recorded']['monotonic_ns']-lo)/1e9,
                post_arrival_work_drain_seconds=max(0,operation_end-hi)/1e9,
                actual_action_start_seconds=(a-lo)/1e9,action_start_lag_ns=a-(lo+cfg['action_offset_ns']),
                rewrite_service_seconds=(b-a)/1e9,initial_layout_signature=initial[0]['layout_signature'],
                initial_file_state=initial[0]['file_state'],final_file_state=final[0]['file_state'],
                mapping_sha256=sha(root/'mapped_arrivals.csv'),events_sha256=sha(root/'events.jsonl'),
                study_registration_sha256=cfg['study_registration']['sha256'],
                query_suite_sha256=cfg['query_suite_sha256'],observer_contract_sha256=cfg['observer_contract_sha256'],
                rewrite_options=cfg['rewrite_sql_options'],source_preparation_sha256=cfg['inputs']['source_preparation']['sha256'],
                source_config_sha256=cfg['inputs']['source_config']['sha256'],
                attributable_cpu_core_seconds=None,physical_io_bytes=None,resource_coverage='not_certified_by_response_accounting',
                physical_episode_accepted=False,training_eligible=False,queries=rows)
