#!/usr/bin/env python3
"""Raw-verified candidate query/rewrite/episode tables; no calibrated fitting or causal labels."""
import argparse,csv,json,shutil,importlib
from pathlib import Path
from experiment_validation import load_json,verified_file,require,sha256
from run_trace_queue_diagnostic import audit
from statement_timing import completed_statements

WINDOW_FIELDS=('cpu_busy_fraction','memory_used_fraction','read_bytes_per_second','write_bytes_per_second','covered_seconds','last_available_sample_end_monotonic_ns')


def export(config):
    cfg,base=load_json(config);require(cfg['schema_version']=='physical_cost_candidate_export_v1','Unregistered export')
    names=('run_trace_queue_diagnostic','common_horizon_binding','offered_queue_ledger','prepare_trace_benchmark_mapping','physical_measurements','experiment_validation','statement_timing','query_observation_binding','telemetry_binding','run_correctness_pilot','engine_overlap','engine_archive')
    dependencies={name:Path(importlib.import_module(name).__file__).resolve() for name in names};dependency_hashes={name:sha256(path) for name,path in dependencies.items()}
    queries=[];rewrites=[];episodes=[];inventory=[];seen=set();inputs={}
    for spec in cfg['successful_arm_results']:
        receipt=verified_file(spec,base);directory=receipt.parent;source_hash=sha256(receipt)
        report=audit(directory);physical=json.loads(receipt.read_text());arm_cfg=json.loads((directory/'config.json').read_text())
        require(physical['status']=='audited_real_arrival_queue_diagnostic_only' and report['events_sha256']==physical['events_sha256'] and report['common_horizon_arm'] is not None,'Unaccepted/changed physical arm')
        rows=[json.loads(line) for line in (directory/'events.jsonl').open()];identity=arm_cfg['experiment_id'];require(identity not in seen,'Duplicate physical episode');seen.add(identity)
        measured=completed_statements([directory/'events.jsonl']);requests={r['measurement_id']:r for r in rows if r['kind']=='statement_requested'}
        done={r['measurement_id']:r for r in rows if r['kind']=='statement_completed'}
        observation={r['measurement_id']:r for r in rows if r['kind']=='query_observation'}
        clock=[r for r in rows if r['kind']=='replay_clock'][0];mapping=json.loads((directory/'mapping_record.json').read_text())
        exposures={r['measurement_id']:r for r in report['common_horizon_arm']['query_task_exposures']}
        for query in report['queries']:
            mid=next(r['measurement_id'] for r in rows if r['kind']=='queue_transition' and r['state']=='offered' and r['source']['source_query_id']==query['source_query_id'])
            observed=observation[mid];statement=measured[(identity,mid)];feature_ns=observed['recorded']['monotonic_ns'];past=[r for r in rows if r['kind']=='queue_transition' and r['recorded']['monotonic_ns']<=feature_ns]
            state={}
            for event in past:state[event['source']['source_query_id']]=event['state']
            pending=[r for r in requests.values() if r['role']=='maintenance' and r['recorded']['monotonic_ns']<=feature_ns and (r['measurement_id'] not in done or done[r['measurement_id']]['recorded']['monotonic_ns']>feature_ns)]
            row={'experiment_id':identity,'measurement_id':mid,'source_query_id':query['source_query_id'],'source_interval_start_utc':mapping['source_interval_start_utc'],'source_interval_end_utc':mapping['source_interval_end_utc'],'query_id':query['query_id'],'feature_monotonic_ns':feature_ns,'query_start_utc':statement['client_execute_start']['utc'],'table':observed['table'],'snapshot_id':observed['snapshot_id'],**observed['file_state'],'maintenance_client_pending_at_feature_time':bool(pending),'queue_depth_at_feature_time':sum(v=='queued' for v in state.values()),'service_target_ms':statement['client_elapsed_ns']/1e6,'client_elapsed_ns':statement['client_elapsed_ns'],'actual_task_overlap_diagnostic_only':exposures[mid]['verified_task_lifetime_overlap'],'completed_within_horizon_diagnostic_only':query['completed_within_horizon'],'generator_lateness_ms_diagnostic_only':query['generator_lateness_ms'],'queue_delay_ms_diagnostic_only':query['queue_to_dispatch_ms']}
            require(feature_ns<=statement['client_execute_start']['monotonic_ns'],'Future features')
            for window in observed['windows']:
                seconds=window['window_seconds']
                for field in WINDOW_FIELDS:row[f'{field}_{seconds}s']=window[field]
                coverage_ns=feature_ns-clock['start_monotonic_ns'];row[f'offered_history_complete_{seconds}s']=coverage_ns>=seconds*1000000000
                offers=[r for r in past if r['state']=='offered' and feature_ns-seconds*1000000000<r['recorded']['monotonic_ns']<=feature_ns]
                row[f'offered_count_{seconds}s']=len(offers) if row[f'offered_history_complete_{seconds}s'] else None
            queries.append(row)
        maintenance=report['common_horizon_arm']['maintenance']
        if maintenance is not None:
            mid=maintenance['measurement_id'];decision=[r for r in rows if r['kind']=='maintenance_decision_observation' and r['measurement_id']==mid][0];statement=measured[(identity,mid)]
            row={'experiment_id':identity,'measurement_id':mid,'source_interval_start_utc':mapping['source_interval_start_utc'],'source_interval_end_utc':mapping['source_interval_end_utc'],'feature_monotonic_ns':decision['recorded']['monotonic_ns'],'table':decision['table'],'snapshot_id':decision['snapshot_id'],**decision['file_state'],'rewrite_service_target_ms':statement['client_elapsed_ns']/1e6,'actual_rewritten_files_target':maintenance['rewrite_result']['rewritten_data_files_count'],'actual_added_files_target':maintenance['rewrite_result']['added_data_files_count'],'actual_rewritten_bytes_target':maintenance['rewrite_result']['rewritten_bytes_count']}
            for window in decision['windows']:
                for field in WINDOW_FIELDS:row[f'{field}_{window["window_seconds"]}s']=window[field]
            rewrites.append(row)
        episodes.append({'experiment_id':identity,'action_arm_diagnostic_only':arm_cfg['action_arm'],'source_interval_start_utc':mapping['source_interval_start_utc'],'source_interval_end_utc':mapping['source_interval_end_utc'],'horizon_ns':mapping['horizon_ns'],'offered':report['offered'],'completed_within_horizon':sum(q['completed_within_horizon'] for q in report['queries']),'dispatched':report['dispatched'],'queued_at_final':report['final_states'].get('queued',0),'maintenance_at_horizon':report['common_horizon_arm']['maintenance_at_horizon'],'final_file_count':report['common_horizon_arm']['final_file_state']['file_count'],'final_bytes':report['common_horizon_arm']['final_file_state']['total_bytes'],'boundary_observation_lateness_ms':report['boundary_observation_lateness_ms']})
        inputs[identity]={'registered_result_spec':spec,'result_sha256':source_hash,'events_sha256':report['events_sha256'],'config_sha256':sha256(directory/'config.json')};inventory.append({'experiment_id':identity,'status':'successful_raw_audited_candidate_only'})
        require(sha256(receipt)==source_hash,'Physical receipt changed while exporting')
    for spec in cfg['attempt_inventories']:
        path=verified_file(spec,base);cohort=json.loads(path.read_text())
        for attempt in cohort['attempts']:
            if attempt['status']!='passed_physical_and_raw_audit_only':inventory.append({'experiment_id':attempt['experiment_id'],'status':attempt['status'],'included_in_candidate_rows':False})
        inventory.append({'inventory_sha256':sha256(path),'unattempted_episodes':cohort.get('unattempted_episodes',0)})
    require(queries and len({r['measurement_id'] for r in queries})==len(queries),'Empty/duplicate query observations')
    out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False);shutil.copy2(config,out/'config.json');shutil.copy2(Path(__file__),out/'export_code.py')
    code=out/'code';code.mkdir()
    for name,path in dependencies.items():
        require(sha256(path)==dependency_hashes[name],'Runtime verifier changed during export');shutil.copy2(path,code/path.name)
    for name,data in [('queries',queries),('rewrites',rewrites),('episodes',episodes)]:
        with (out/f'{name}.csv').open('x',newline='') as f:
            require(data,'Empty declared candidate table');writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    (out/'attempt_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    predictors=['query_id','file_count','record_count','total_bytes','maintenance_client_pending_at_feature_time','queue_depth_at_feature_time']+[f'{field}_{seconds}s' for seconds in (60,300) for field in WINDOW_FIELDS[:4]]
    manifest={'schema_version':cfg['schema_version'],'status':'raw_verified_candidates_only_not_accepted_training','query_rows':len(queries),'rewrite_rows':len(rewrites),'episodes':len(episodes),'query_predictor_allowlist':predictors,'query_target':'service_target_ms','rewrite_target':'rewrite_service_target_ms','calibrated_training_accepted':False,'scheduler_authorized':False,'source_evidence':inputs,'export_code_sha256':sha256(Path(__file__)),'verification_dependency_sha256':dependency_hashes,'artifact_sha256':{str(p.relative_to(out)):sha256(p) for p in out.rglob('*') if p.is_file()},'limitations':cfg['limitations']}
    (out/'export_record.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:manifest[k] for k in ('status','query_rows','rewrite_rows','episodes','calibrated_training_accepted')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);export(p.parse_args().config)
