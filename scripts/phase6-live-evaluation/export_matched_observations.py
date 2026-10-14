#!/usr/bin/env python3
"""Export only bound measured fields from an accepted diagnostic pilot, never training."""
import argparse,csv,json,shutil
from pathlib import Path
from experiment_validation import require,sha256,verified_file
from run_correctness_pilot import canonical,query_templates
from statement_timing import completed_statements,TIMING_FIELDS,DURATION_FIELDS
from query_observation_binding import verify_observations
from engine_label_binding import read_engine_ledgers,rewrite_evidence,query_exposure
from action_order_binding import verify_action_order


def export(pilot_directory,result_hash,output_directory):
    source=Path(pilot_directory).resolve();receipt=source/'result.json';require(sha256(receipt)==result_hash,'Pilot result not pinned/changed')
    result=json.loads(receipt.read_text());require(result['status']=='accepted_matched_measurement_integrity_only','Accepted diagnostic measurement required')
    cfg=json.loads((source/'config.json').read_text());events=source/'events.jsonl';event_hash=sha256(events)
    records=[json.loads(line) for line in events.open()];require(all(r['experiment_id']==cfg['experiment_id'] and r['schema_version']=='physical_event_v1' for r in records),'Mixed raw pilot scope')
    protocol=[r for r in records if r['kind']=='matched_protocol'];require(len(protocol)==1 and protocol[0]['configuration']==cfg and protocol[0]['code_revision']==result['code_revision'],'Raw protocol/result mismatch')
    for name,digest in protocol[0]['code_sha256'].items():require(sha256(source/'code'/name)==digest,'Frozen physical code changed')
    completed=completed_statements([events]);checks=verify_observations(records,cfg);require(checks==result['query_observation_checks'],'Reported observation checks differ')
    order_check=verify_action_order(records,cfg)
    if order_check is not None:require(order_check==result['action_order_check'],'Raw registered action order differs from result')
    requests={r['measurement_id']:r for r in records if r['kind']=='statement_requested'}
    # Reconstruct correctness from the raw completed statements, not acceptance flags.
    observations=[r for r in records if r['kind']=='query_observation']
    baseline=None
    for observed in observations:
        state=result['compacted' if observed['role']=='compacted_layout' else 'original']
        require(all(observed[k]==state[k] for k in ('table','snapshot_id','file_state')),'Query state differs from actual matched layout')
        expected_sql=query_templates(result['table'])[cfg['query_id']].replace(f"FROM {result['table']}",f"FROM {result['table']} VERSION AS OF {state['snapshot_id']}")
        require(requests[observed['measurement_id']]['sql']==expected_sql,'Changed query semantics across matched probes')
        actual=canonical(completed[(cfg['experiment_id'],observed['measurement_id'])]['rows'])
        if baseline is None:baseline=actual
        require(actual==baseline,'Raw matched query results differ')
    preparation=verified_file(cfg['preparation_result'],Path(__file__).resolve().parents[2]/'docs'/'experiment_protocols')
    prep=json.loads(preparation.read_text())
    require(prep['status']=='accepted_correctness_source','Unaccepted physical source')
    table=result['table']; source_table=prep['table']; source_snapshot=prep['snapshot_id']
    difference_sql=f"SELECT count(*) FROM ((SELECT * FROM {source_table} VERSION AS OF {source_snapshot} EXCEPT ALL SELECT * FROM {table}) UNION ALL (SELECT * FROM {table} EXCEPT ALL SELECT * FROM {source_table} VERSION AS OF {source_snapshot})) AS differences"
    differences=[r for r in requests.values() if r['role']=='full_multiset_validation']
    require(len(differences)==1 and differences[0]['sql']==difference_sql,'Missing exact bidirectional source/current multiset statement')
    require(completed[(cfg['experiment_id'],differences[0]['measurement_id'])]['rows']==[[0]],'Raw full multiset validation did not preserve rows')
    decisions=[r for r in records if r['kind']=='maintenance_decision_observation']
    if cfg.get('decision_feature_contract')=='pre_action_windows_v1':
        decision_checks=verify_observations(records,cfg,kind='maintenance_decision_observation')
        require(decision_checks==result['decision_observation_checks'] and len(decisions)==1,'Pre-action feature/result binding mismatch')
        require(all(decisions[0][k]==result['original'][k] for k in ('table','snapshot_id','file_state')),'Action state changed from matched original')
    else:
        require(not decisions,'Unregistered pre-action context')
    ledgers=read_engine_ledgers([events]);raw=ledgers[cfg['experiment_id']]
    maintenance=[key for key,value in raw['requests'].items() if value['role']=='maintenance'];require(len(maintenance)==1,'One complete actual rewrite required')
    maintenance_id=maintenance[0];_,rewrite,tasks=rewrite_evidence(raw,maintenance_id,result['table']);require(rewrite==result['rewrite_result'],'Physical rewrite differs from result')
    original=result['original']['file_state']; compacted=result['compacted']['file_state']
    require(original['record_count']==compacted['record_count']==prep['record_count'] and compacted['file_count']==original['file_count']-rewrite['rewritten_data_files_count']+rewrite['added_data_files_count'],'Raw metadata conservation differs')
    declared={q['measurement_id']:q for q in result['task_exposures']};observations=[r for r in records if r['kind']=='query_observation'];rows=[]
    for observed in observations:
        identity=observed['measurement_id'];statement=completed[(cfg['experiment_id'],identity)];exposure=query_exposure(raw,identity,tasks)
        require(dict(measurement_id=identity,**exposure)==declared[identity],'Saved exposure differs from raw Spark tasks')
        require(exposure['verified_task_lifetime_overlap']==(observed['role']=='during_rewrite'),'Unexpected control/treatment exposure')
        windows={w['window_seconds']:w for w in observed['windows']};state=observed['file_state']
        row={'measurement_id':identity,'experiment_id':cfg['experiment_id'],'query_id':observed['query_id'],'role':observed['role'],'table':observed['table'],'snapshot_id':observed['snapshot_id'],'spark_app_id':cfg['spark_app_id'],**state,'average_file_bytes':state['total_bytes']/state['file_count'],'snapshot_measurement_id':observed['snapshot_measurement_id'],'file_inventory_measurement_id':observed['file_inventory_measurement_id'],'timing_contract':statement['timing_contract'],'query_start_utc':statement['client_execute_start']['utc'],'query_end_utc':statement['fetch_end']['utc'],'client_latency_ms':statement['client_elapsed_ns']/1000000,'verified_task_lifetime_overlap':exposure['verified_task_lifetime_overlap'],'task_overlap_seconds':exposure['overlap_seconds'],'maintenance_measurement_id':maintenance_id if exposure['verified_task_lifetime_overlap'] else None}
        row.update({field:statement[field] for field in DURATION_FIELDS});row.update({field+'_monotonic_ns':statement[field]['monotonic_ns'] for field in TIMING_FIELDS})
        for seconds,window in windows.items():
            for field in ['window_start_monotonic_ns','window_end_monotonic_ns','last_available_sample_end_monotonic_ns','covered_seconds','freshness_seconds','cpu_busy_fraction','memory_used_fraction','read_bytes_per_second','write_bytes_per_second']:row[f'{field}_{seconds}s']=window[field]
        rows.append(row)
    require(len(rows)==4 and {r['role'] for r in rows}=={'control_before','during_rewrite','control_after_original_snapshot','compacted_layout'},'Incomplete matched probes')
    require(result['multiset_difference_count']==0,'Rows not preserved')
    output=Path(output_directory).resolve();output.mkdir(parents=True,exist_ok=False);shutil.copy2(__file__,output/'export_code.py');shutil.copy2(receipt,output/'source_result.json');shutil.copy2(source/'config.json',output/'source_config.json')
    shutil.copy2(preparation,output/'source_preparation_result.json')
    with (output/'query_observations.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    require(sha256(receipt)==result_hash and sha256(events)==event_hash,'Physical inputs changed during export')
    if decisions:
        (output/'decision_observations.json').write_text(json.dumps(decisions,indent=2)+'\n')
    manifest={'pre_action_observation_count':len(decisions),'schema_version':'diagnostic_physical_query_observations_v1','status':'exported_bound_measurements_only','origin':'physical_spark_iceberg_verified_sf1','row_count':len(rows),'source_result_sha256':result_hash,'source_events_sha256':event_hash,'export_code_sha256':sha256(Path(__file__)),'observations_sha256':sha256(output/'query_observations.csv'),'code_revision_of_physical_run':result['code_revision'],'scope':'Four actual probe observations from one matched episode. Fractions/bytes/monotonic durations preserved; no imputed intensity/small-file eligibility, split labels, future state, counterfactual cost or training approval. Old trainer schema intentionally incompatible.','limitations':result['limitations']}
    require(sha256(preparation)==cfg['preparation_result']['sha256'],'Preparation receipt changed during export')
    manifest.update(source_preparation_sha256=cfg['preparation_result']['sha256'],raw_correctness_checks=['current_snapshot_sql','matched_query_sql_and_result_equality','original_and_compacted_state_binding','bidirectional_source_current_multiset','record_and_rewritten_file_conservation'])
    manifest['action_order_check']=order_check
    (output/'export_record.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pilot-directory',required=True);p.add_argument('--result-sha256',required=True);p.add_argument('--output-directory',required=True);a=p.parse_args();export(a.pilot_directory,a.result_sha256,a.output_directory)
