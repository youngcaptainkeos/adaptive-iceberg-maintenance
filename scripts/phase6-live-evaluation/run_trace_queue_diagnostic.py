#!/usr/bin/env python3
"""Real offered arrivals, one FIFO physical SQL client; no maintenance or training."""
import argparse,csv,fcntl,json,queue,shutil,subprocess,threading,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from experiment_validation import load_json,verified_file,require,sha256
from physical_measurements import EventLog,StatementRecorder,SparkEvidence,TelemetrySampler,stamp
from offered_queue_ledger import OfferedQueueLedger
from run_correctness_pilot import query_templates,canonical
from query_observation_binding import verify_observations
from statement_timing import completed_statements
from engine_overlap import task_intervals,engine_time
from common_horizon_binding import audit_arm
from engine_archive import merged_engine_frames,capture_completed_query_tasks,ArchivedTaskEvidence


class PreparationSampleUnavailable(Exception):
    def __init__(self,checked,last):
        self.checked=checked;self.last=last


def audit(directory):
    directory=Path(directory);cfg=json.loads((directory/'config.json').read_text());rows=[json.loads(s) for s in (directory/'events.jsonl').open()]
    mapped=list(csv.DictReader((directory/'mapped_arrivals.csv').open()));mapping=json.loads((directory/'mapping_record.json').read_text())
    require(sha256(directory/'mapped_arrivals.csv')==mapping['mapped_arrivals_sha256'] and len(mapped)==mapping['arrival_count'],'Mapped input changed')
    protocols=[r for r in rows if r['kind']=='trace_queue_protocol'];require(len(protocols)==1 and protocols[0]['configuration']==cfg,'Raw protocol differs')
    for name,digest in protocols[0]['code_sha256'].items():require(sha256(directory/'code'/name)==digest,'Frozen code differs')
    require(sha256(directory/'mapping_record.json')==cfg['mapping_record']['sha256'] and sha256(directory/'mapping_audit.json')==cfg['mapping_audit']['sha256'],'Mapping receipt/audit differs')
    start=[r for r in rows if r['kind']=='replay_clock'];require(len(start)==1,'Missing/duplicate clock')
    start=start[0];lo=start['start_monotonic_ns'];hi=start['end_monotonic_ns'];require(hi-lo==mapping['horizon_ns'],'Horizon changed')
    not_sent=[r for r in rows if r['kind']=='statement_not_submitted'];not_sent_by_id={r['measurement_id']:r for r in not_sent}
    require(len(not_sent)==len(not_sent_by_id)<=1,'Duplicate/multiple terminal unsubmitted intents')
    if not_sent:require(cfg.get('rpc_boundary_contract')=='guarded_rpc_start_requeue_v1','Unregistered unsubmitted RPC boundary')
    transitions=[r for r in rows if r['kind']=='queue_transition'];states={};slots={};expected={r['source_query_id']:r for r in mapped};identities={};times={}
    for r in transitions:
        identity=r['source']['source_query_id'];state=r['state'];previous=states.get(identity)
        require(identity in expected and r['source']==expected[identity] and r['previous_state']==previous,'Source/state chain differs')
        ns=r['actual_transition']['monotonic_ns'];require(ns<=r['recorded']['monotonic_ns'],'Future transition stamp')
        requeued=(previous,state)==('dispatched','queued') and r['measurement_id'] in not_sent_by_id
        if requeued:require(r.get('reason')=='horizon_before_rpc' and ns>=not_sent_by_id[r['measurement_id']]['recorded']['monotonic_ns']>=hi,'Unsubmitted requeue differs')
        require(requeued or (previous,state) in ((None,'offered'),('offered','queued'),('queued','dispatched'),('dispatched','completed'),('dispatched','failed')),'Illegal actual queue chain')
        require(r['scheduled_monotonic_ns']==lo+int(expected[identity]['offset_ns']),'Retimed source arrival')
        if state=='offered':
            require(ns>=r['scheduled_monotonic_ns'],'Offered before source arrival');identities[identity]=r['measurement_id'];times[identity]={}
        require(identities[identity]==r['measurement_id'],'Measurement UUID changed')
        if times[identity]:require(ns>=max(times[identity].values()),'Queue clock reversal')
        times[identity][state]=ns
        if state=='dispatched':
            require(r['session_id']=='query_0' and r['session_id'] not in slots and ns<hi,'Busy/late dispatch');slots[r['session_id']]=identity
        if state in ('completed','failed') or requeued:
            require(slots.get(r['session_id'])==identity,'Outcome session differs');del slots[r['session_id']]
        states[identity]=state
    require(set(states)==set(expected) and len(set(identities.values()))==len(expected),'Missing offered arrivals or reused measurement UUID')
    require(not slots and all(s in ('queued','completed','failed') for s in states.values()),'In-flight final state')
    offered=[r['source']['source_query_id'] for r in transitions if r['state']=='offered']
    dispatched=[r['source']['source_query_id'] for r in transitions if r['state']=='dispatched']
    require(offered==[r['source_query_id'] for r in mapped] and dispatched==offered[:len(dispatched)],'FIFO order differs')
    dispatch_attempt_count=len(dispatched)
    measured=completed_statements([directory/'events.jsonl']);requests={r['measurement_id']:r for r in rows if r['kind']=='statement_requested'}
    for mid,event in not_sent_by_id.items():
        matches=[identity for identity,identity_mid in identities.items() if identity_mid==mid]
        require(len(matches)==1 and states[matches[0]]=='queued' and matches[0]==dispatched[-1],'Unsubmitted request must be final FIFO admission retained queued')
        require(event['latest_start_monotonic_ns']==hi and hi<=event['checked_at']['monotonic_ns']<=event['recorded']['monotonic_ns'],'RPC cutoff/clock differs')
        require((cfg['experiment_id'],mid) not in measured and mid in requests,'Unsubmitted query has a completed call or no intent')
        require(sum(r['previous_state']=='dispatched' and r['state']=='queued' and r['measurement_id']==mid for r in transitions)==1,'Missing unique unsubmitted requeue')
        observations=[r for r in rows if r['kind']=='query_observation' and r['measurement_id']==mid]
        require(len(observations)==1 and observations[0]['recorded']['monotonic_ns']<=requests[mid]['request_start']['monotonic_ns'],'Unsubmitted observation chronology differs')
        require(requests[mid]['query_id']==int(expected[matches[0]]['query_id']),'Unsubmitted source/query identity differs')
    dispatched=[identity for identity in dispatched if identities[identity] not in not_sent_by_id]
    require(dispatched==offered[:len(dispatched)],'Executed FIFO prefix differs')
    for event in (r for r in rows if r['kind']=='query_preparation_deferred'):
        require(cfg.get('submission_availability_contract')=='release_and_wait_for_real_sample_v1','Unregistered submission deferral')
        mid=event['measurement_id'];checked=event['checked_at']['monotonic_ns'];last=event['last_available_sample_end_ns']
        require(identities.get(event['source_query_id'])==mid and checked<=event['recorded']['monotonic_ns'],'Unknown/deferred clock identity')
        require(last is None or (checked-last)/1e9>cfg['telemetry']['max_age_seconds'],'Deferral did not observe expired sample')
        require(mid not in requests or checked<requests[mid]['request_start']['monotonic_ns'],'Deferral after SQL intent')
    abandoned=[r for r in rows if r['kind']=='query_observation_not_dispatched']
    abandoned_ids={r['measurement_id'] for r in abandoned}
    if abandoned:
        require(cfg.get('boundary_preparation_contract')=='retain_queued_unsubmitted_observation_v1' and len(abandoned)==len(abandoned_ids)==1,'Unregistered/duplicate boundary abandonment')
        for abandon in abandoned:
            mid=abandon['measurement_id'];identity=abandon['source_query_id']
            observations=[r for r in rows if r['kind']=='query_observation' and r['measurement_id']==mid]
            require(identity in expected and identities[identity]==mid and states[identity]=='queued' and mid not in requests,'Abandoned query was unknown/dispatched/submitted')
            require(len(observations)==1 and observations[0]['query_id']==int(expected[identity]['query_id']),'Abandoned observation identity differs')
            require(abandon['horizon_end_monotonic_ns']==hi and abandon['reason']=='horizon_reached_before_dispatch' and hi<=abandon['checked_at']['monotonic_ns']<=abandon['recorded']['monotonic_ns'] and observations[0]['recorded']['monotonic_ns']<=abandon['checked_at']['monotonic_ns'],'Abandonment not bound to actual boundary crossing')
    bound_rows=[r for r in rows if not(r['kind']=='query_observation' and r['measurement_id'] in (abandoned_ids|not_sent_by_id.keys()))]
    observed=[r for r in bound_rows if r['kind']=='query_observation'];require(len(observed)==len(dispatched)>0,'Missing actual query evidence')
    verify_observations(bound_rows,cfg)
    if cfg.get('expected_spark_master'):
        environments=[r['payload'] for r in rows if r['kind']=='spark_rest' and r['resource']=='environment']
        require(len(environments)==1 and dict(environments[0]['sparkProperties']).get('spark.master')==cfg['expected_spark_master'],'Actual raw parallelism differs')
    source=json.loads((directory/'preparation_result.json').read_text());require(sha256(directory/'preparation_result.json')==cfg['preparation_result']['sha256'],'Source receipt changed')
    refs=json.loads((directory/'expected_query_results.json').read_text()); rebuilt_refs={}
    for i,spec in enumerate(cfg['expected_query_ledgers']):
        path=directory/f'expected_ledger_{i}.jsonl';require(sha256(path)==spec['sha256'],'Expected result ledger changed')
        candidates=[r for r in completed_statements([path]).values() if r['role']=='control_before'];require(len(candidates)==1,'Ambiguous expected result reference')
        ref=candidates[0];rebuilt_refs[str(ref['query_id'])]=canonical(ref['rows'])
    require(refs==rebuilt_refs,'Expected results differ from raw references')
    arm=cfg.get('schema_version')=='common_horizon_arm_pilot_v1'
    observed_by_id={r['measurement_id']:r for r in observed}
    table=cfg['destination_table'] if arm else source['table']
    allowed_markers=[r['marker'] for r in requests.values()]
    latencies=[];rests=[r for r in rows if r['kind']=='spark_rest'];jobs,stages=merged_engine_frames(rows)
    for mid in not_sent_by_id:
        require(not any(requests[mid]['marker'] in str(j.get('description','')) for j in jobs),'Unsubmitted query has actual Spark jobs')
    def RecordedREST():return ArchivedTaskEvidence(rows)
    for identity in dispatched:
        mid=identities[identity];r=measured[(cfg['experiment_id'],mid)];qid=int(expected[identity]['query_id'])
        require(requests[mid]['query_id']==qid and requests[mid]['sql']==query_templates(table)[qid].replace(f'FROM {table}',f"FROM {table} VERSION AS OF {observed_by_id[mid]['snapshot_id']}"),'Dispatched SQL differs')
        require(times[identity]['dispatched']<=r['client_execute_start']['monotonic_ns']<hi and r['fetch_end']['monotonic_ns']<=times[identity]['completed'],'Call/outcome boundary differs')
        require(canonical(r['rows'])==refs[str(qid)],'Benchmark result differs')
        task_intervals(jobs,stages,RecordedREST(),marker=r['marker'])
        a=datetime.fromisoformat(r['client_execute_start']['utc']).timestamp();b=datetime.fromisoformat(r['fetch_end']['utc']).timestamp()
        active=[j for j in jobs if engine_time(j['submissionTime'])<b and (not j.get('completionTime') or engine_time(j['completionTime'])>a)]
        require(active and all((any(marker in str(j.get('description','')) for marker in allowed_markers) or (str(j.get('description','')).startswith('Rewriting ') and str(j.get('description','')).endswith(' in '+table))) if arm else r['marker'] in str(j.get('description','')) for j in active),'Foreign Spark work')
        latencies.append({'source_query_id':identity,'query_id':qid,'service_ms':r['client_elapsed_ns']/1e6,'generator_lateness_ms':(times[identity]['offered']-(lo+int(expected[identity]['offset_ns'])))/1e6,'queue_to_dispatch_ms':(times[identity]['dispatched']-times[identity]['queued'])/1e6,'completed_within_horizon':r['fetch_end']['monotonic_ns']<=hi})
    boundaries=[r for r in rows if r['kind']=='queue_boundary'];require(len(boundaries)==1 and boundaries[0]['horizon_end_monotonic_ns']==hi,'Missing fixed boundary')
    boundary=boundaries[0];prior=[r for r in transitions if r['recorded']['monotonic_ns']<boundary['recorded']['monotonic_ns']];at={}
    for r in prior:at[r['source']['source_query_id']]=r['state']
    require(boundary['observed_states']==at,'Boundary census differs from raw ledger')
    from collections import Counter
    require(boundary['observed_counts']==dict(Counter(at.values())),'Boundary counts differ')
    arm_evidence=None
    if arm:
        arm_evidence=audit_arm(bound_rows,cfg,measured,requests,jobs,stages,RecordedREST(),lo,hi,source)
    else:
        inventories=[r for r in measured.values() if requests[r['measurement_id']]['sql']==f"SELECT file_path, record_count, file_size_in_bytes FROM {source['table']}.files"]
        snapshots=[r for r in measured.values() if requests[r['measurement_id']]['sql']==f"SELECT snapshot_id FROM {source['table']}.history ORDER BY made_current_at DESC LIMIT 1"]
        require(len(inventories)==2 and sorted(inventories[0]['rows'])==sorted(inventories[1]['rows']) and len(snapshots)==2 and all(r['rows']==[[source['snapshot_id']]] for r in snapshots),'Source state changed')
        require(not any('rewrite_data_files' in r['sql'].lower() for r in requests.values()),'Maintenance in diagnostic')
    horizon_states={}
    for r in transitions:
        if r['actual_transition']['monotonic_ns']<=hi:horizon_states[r['source']['source_query_id']]=r['state']
    require(sha256(directory/'code'/'run_correctness_pilot.py')==mapping['source_sha256']['sql_template_code'], 'Executed SQL vocabulary differs from mapped template source')
    summary={'common_horizon_arm':arm_evidence,'horizon_actual_transition_counts':dict(Counter(horizon_states.values())), 'horizon_not_yet_offered_ids':[k for k in expected if k not in horizon_states], 'status':'audited_real_arrival_queue_diagnostic_only','offered':len(mapped),'dispatched':len(dispatched),'final_states':dict(Counter(states.values())),'unfinished_queued_ids':[k for k,v in states.items() if v=='queued'],'boundary_observed_counts':boundary['observed_counts'],'boundary_observation_lateness_ms':(boundary['recorded']['monotonic_ns']-hi)/1e6,'queries':latencies,'events_sha256':sha256(directory/'events.jsonl'),'cost_training_accepted':False,'limitations':cfg['limitations']}

    if cfg.get('boundary_preparation_contract')=='retain_queued_unsubmitted_observation_v1':summary['prepared_but_not_dispatched_measurement_ids']=sorted(abandoned_ids)
    if cfg.get('rpc_boundary_contract')=='guarded_rpc_start_requeue_v1':
        summary.update(queue_admission_attempts=dispatch_attempt_count,unsubmitted_intent_measurement_ids=sorted(not_sent_by_id),
                       horizon_dispatch_census_meaning='Raw client admissions include preparing intents; unsubmitted intent IDs remain explicit queue debt, never executed query labels')
    return summary


def run(config,revision):
    cfg,base=load_json(config);repo=Path(__file__).resolve().parents[2]
    arm=cfg['schema_version']=='common_horizon_arm_pilot_v1'
    require(cfg.get('rpc_boundary_contract') in (None,'guarded_rpc_start_requeue_v1'),'Unknown RPC boundary contract')
    require(cfg.get('rpc_boundary_contract') is None or cfg.get('query_preparation_contract')=='serialized_durable_submission_v1','RPC cutoff requires serialized durable preparation')
    require(cfg['schema_version'] in ('trace_queue_diagnostic_v1','common_horizon_arm_pilot_v1') and cfg['client_count']==1 and cfg['boundary_rule']=='no_dispatch_after_horizon_natural_inflight_completion','Unregistered diagnostic')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==revision,'HEAD mismatch')
    require(subprocess.run(['git','diff','--exit-code','HEAD','--','scripts/phase6-live-evaluation/*.py'],cwd=repo,capture_output=True).returncode==0,'Dirty experiment code')
    record_path=verified_file(cfg['mapping_record'],base);mapping=json.loads(record_path.read_text());mapping_audit_path=verified_file(cfg['mapping_audit'],base);mapping_audit=json.loads(mapping_audit_path.read_text());require(mapping_audit['status']=='audited_complete_real_arrival_benchmark_mapping_only' and mapping_audit['mapping_record_sha256']==sha256(record_path),'Unaudited mapping');mapped_path=record_path.parent/'mapped_arrivals.csv';require(sha256(mapped_path)==mapping['mapped_arrivals_sha256'],'Mapped arrivals changed')
    mapped=list(csv.DictReader(mapped_path.open()));require(mapped and mapping['status']=='mapped_real_arrivals_no_physical_replay','Unaccepted mapping')
    source_path=verified_file(cfg['preparation_result'],base);source=json.loads(source_path.read_text());require(source['status']=='accepted_correctness_source','Unaccepted SF1')
    expected={}
    for spec in cfg['expected_query_ledgers']:
        raw=verified_file(spec,base);records=completed_statements([raw]);matches=[r for r in records.values() if r['role']=='control_before'];require(len(matches)==1,'Ambiguous expected SQL results');r=matches[0];expected[str(r['query_id'])]=canonical(r['rows'])
    require(set(expected)==set(str(q) for q in range(4)),'Missing query correctness references')
    deadline=datetime.fromisoformat(cfg['no_new_operation_after_utc'])
    def guard():require(datetime.now(timezone.utc)<deadline,'Operational cutoff; no new statement')
    guard();lock=(repo/'results'/'.physical_correctness.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False);code=out/'code';code.mkdir()
    for name in ('run_trace_queue_diagnostic.py','offered_queue_ledger.py','prepare_trace_benchmark_mapping.py','physical_measurements.py','experiment_validation.py','statement_timing.py','query_observation_binding.py','telemetry_binding.py','run_correctness_pilot.py','engine_overlap.py','common_horizon_binding.py','engine_archive.py'):shutil.copy2(Path(__file__).parent/name,code/name)
    for src,name in ((Path(config),'config.json'),(source_path,'preparation_result.json'),(record_path,'mapping_record.json'),(mapping_audit_path,'mapping_audit.json'),(mapped_path,'mapped_arrivals.csv')):shutil.copy2(src,out/name)
    for i,spec in enumerate(cfg['expected_query_ledgers']):shutil.copy2(verified_file(spec,base),out/f'expected_ledger_{i}.jsonl')
    (out/'expected_query_results.json').write_text(json.dumps(expected,indent=2)+'\n')
    log=EventLog(out/'events.jsonl',cfg['experiment_id']);rec=StatementRecorder(log);rest=SparkEvidence(cfg['spark_rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log);sampler=TelemetrySampler(log,cfg['telemetry']['interval_seconds'],asynchronous_persistence=cfg.get('telemetry_persistence_contract')=='independent_counter_sampling_durable_publish_v1');connections=[];errors=[];threads=[];safe_to_close=False
    log.emit('trace_queue_protocol',configuration=cfg,code_revision=revision,code_sha256={p.name:sha256(p) for p in code.iterdir()})
    from pyhive import hive
    try:
        for _ in range(3 if arm else 2):connections.append(hive.Connection(**{k:cfg['engine'][k] for k in ('host','port','username')}))
        cursors=[c.cursor() for c in connections];metadata,query=cursors[:2]
        maintenance_cursor=cursors[2] if arm else None
        def execute(sql):guard();return rec.execute(metadata,sql,role='metadata')
        require(not rest._capture('jobs?status=running'),'Other active Spark jobs')
        require(execute('SELECT version()')['rows'][0][0].split()[0]==cfg['engine']['expected_version'],'Engine mismatch');environment=rest.capture('environment')
        if cfg.get('expected_spark_master'):require(dict(environment['sparkProperties']).get('spark.master')==cfg['expected_spark_master'],'Registered parallelism environment differs')
        table=source['table']
        if arm:
            import re
            table=cfg['destination_table'];require(re.fullmatch(r'local\.experiment\.integrity_horizon_[a-z0-9_]+',table),'Dedicated isolated arm required')
            require(cfg['action_arm'] in ('no_maintenance','compact_now','compact_later') and cfg['metadata_checkpoint_offsets_ns']==[0,mapping['horizon_ns']//2],'Registered arm/checkpoints required')
            require(cfg['action_offset_ns']=={'no_maintenance':None,'compact_now':0,'compact_later':mapping['horizon_ns']//2}[cfg['action_arm']],'Registered action offset differs')
            require(not any(r[1]==table.split('.')[-1] for r in execute('SHOW TABLES IN local.experiment')['rows']),'Never overwrite a target')
            require(execute(f"SELECT snapshot_id FROM {source['table']}.history ORDER BY made_current_at DESC LIMIT 1")['rows'][0][0]==source['snapshot_id'],'Source changed')
            count=cfg.get('initial_file_count',source['file_count']);require(isinstance(count,int) and not isinstance(count,bool) and count>1,'Register real original file-count intervention')
            execute(f"CREATE TABLE {table} USING iceberg AS SELECT /*+ REPARTITION({count}) */ * FROM {source['table']} VERSION AS OF {source['snapshot_id']}")
            log.emit('common_horizon_source',table=source['table'],snapshot_id=source['snapshot_id'])
        current_inventory_end_ns=[None]
        def inventory():
            snap=execute(f"SELECT snapshot_id FROM {table}.history ORDER BY made_current_at DESC LIMIT 1");files=execute(f"SELECT file_path, record_count, file_size_in_bytes FROM {table}.files")
            current_inventory_end_ns[0]=files['fetch_end']['monotonic_ns']
            if not arm:require(snap['rows'][0][0]==source['snapshot_id'],'Source snapshot changed')
            return {'table':table,'snapshot_id':snap['rows'][0][0],'snapshot_measurement_id':snap['measurement_id'],'file_inventory_measurement_id':files['measurement_id'],'file_state':{'file_count':len(files['rows']),'record_count':sum(r[1] for r in files['rows']),'total_bytes':sum(r[2] for r in files['rows'])}}
        state=inventory();initial_state=state
        require(state['file_state']['record_count']==source['record_count'] and state['file_state']['file_count']==cfg.get('initial_file_count',source['file_count']),'Source/initial layout differs')
        if arm:log.emit('common_horizon_initial_state',**state)
        sampler.start();time.sleep(cfg['telemetry']['warmup_seconds']);guard()
        lo=time.monotonic_ns();hi=lo+mapping['horizon_ns'];log.emit('replay_clock',start_monotonic_ns=lo,end_monotonic_ns=hi,source_interval_start_utc=mapping['source_interval_start_utc'],source_interval_end_utc=mapping['source_interval_end_utc'])
        ledger=OfferedQueueLedger(log,mapped,lo,hi,allow_unsubmitted_requeue=cfg.get('rpc_boundary_contract')=='guarded_rpc_start_requeue_v1');pending=queue.Queue();identities={r['source_query_id']:uuid.uuid4().hex for r in mapped}
        def wait_until(ns):time.sleep(max(0,(ns-time.monotonic_ns())/1e9))
        def offer():
            try:
                for r in mapped:
                    wait_until(lo+int(r['offset_ns']));identity=r['source_query_id'];mid=identities[identity]
                    ledger.transition(identity,'offered',measurement_id=mid);ledger.transition(identity,'queued',measurement_id=mid);pending.put(r)
            except Exception as e:
                errors.append(e);log.emit('trace_queue_thread_failed',error_type=type(e).__name__,error=str(e))
        def boundary():
            try:wait_until(hi);ledger.boundary()
            except Exception as e:
                errors.append(e);log.emit('trace_queue_thread_failed',error_type=type(e).__name__,error=str(e))
        for func in (offer,boundary):
            thread=threading.Thread(target=func);threads.append(thread);thread.start()
        state_lock=threading.Lock();actions=[]
        def action_schedule():
            nonlocal state
            try:
                for offset in cfg['metadata_checkpoint_offsets_ns']:
                    wait_until(lo+offset);guard()
                    refreshed=execute(f'REFRESH TABLE {table}');current=inventory()
                    log.emit('common_horizon_checkpoint',offset_ns=offset,**current)
                    with state_lock:state=current
                    if offset!=cfg['action_offset_ns']:continue
                    mid=uuid.uuid4().hex;t=cfg['telemetry']
                    windows=[sampler.window(seconds=w,max_interval_seconds=t['max_interval_seconds'],max_age_seconds=t['max_age_seconds']) for w in t['window_seconds']]
                    current=dict(current,decision_refresh_measurement_id=refreshed['measurement_id'])
                    log.emit('maintenance_decision_observation',measurement_id=mid,query_id=None,role='maintenance',windows=windows,**current)
                    guard();require(time.monotonic_ns()<hi,'No action after horizon')
                    require((time.monotonic_ns()-current_inventory_end_ns[0])/1e9<=cfg['metadata_max_age_seconds'],'Fresh action inventory expired')
                    action=rec.execute(maintenance_cursor,f"CALL local.system.rewrite_data_files(table => '{table.removeprefix('local.')}', strategy => 'binpack', options => map('partial-progress.enabled','false'))",role='maintenance',measurement_id=mid);actions.append(action)
                    execute(f'REFRESH TABLE {table}');updated=inventory()
                    log.emit('common_horizon_state_published',**updated)
                    with state_lock:state=updated
            except Exception as e:
                errors.append(e);log.emit('trace_queue_thread_failed',error_type=type(e).__name__,error=str(e))
        if arm:
            thread=threading.Thread(target=action_schedule);threads.append(thread);thread.start()
        def archive_engine():
            try:
                for offset in cfg.get('engine_archive_offsets_ns',[]):
                    wait_until(lo+offset);capture_completed_query_tasks(rest,log,out/'events.jsonl')
            except Exception as e:
                errors.append(e);log.emit('trace_queue_thread_failed',error_type=type(e).__name__,error=str(e))
        if cfg.get('engine_archive_offsets_ns'):
            require(all(0<x<mapping['horizon_ns'] for x in cfg['engine_archive_offsets_ns']),'Register within-horizon engine archive checkpoints')
            thread=threading.Thread(target=archive_engine);threads.append(thread);thread.start()
        probes=[];query_snapshot=None
        while time.monotonic_ns()<hi:
            try:r=pending.get(timeout=max(0,(hi-time.monotonic_ns())/1e9))
            except queue.Empty:break
            if time.monotonic_ns()>=hi:break
            guard();identity=r['source_query_id'];mid=identities[identity];qid=int(r['query_id']);t=cfg['telemetry']
            if cfg.get('telemetry_availability_contract')=='wait_for_real_durable_sample_v1':
                if not sampler.wait_for_available_sample(deadline_ns=hi,max_age_seconds=t['max_age_seconds'],measurement_id=mid):break
            windows=[sampler.window(seconds=w,max_interval_seconds=t['max_interval_seconds'],max_age_seconds=t['max_age_seconds']) for w in t['window_seconds']]
            with state_lock:query_state=state
            if arm and query_snapshot!=query_state['snapshot_id']:
                guard();rec.execute(query,f'REFRESH TABLE {table}',role='query_session_state_refresh');query_snapshot=query_state['snapshot_id']
                if cfg.get('telemetry_availability_contract')=='wait_for_real_durable_sample_v1':
                    if not sampler.wait_for_available_sample(deadline_ns=hi,max_age_seconds=t['max_age_seconds'],measurement_id=mid):break
                windows=[sampler.window(seconds=w,max_interval_seconds=t['max_interval_seconds'],max_age_seconds=t['max_age_seconds']) for w in t['window_seconds']]
            if time.monotonic_ns()>=hi:break
            sql=query_templates(table)[qid].replace(f'FROM {table}',f"FROM {table} VERSION AS OF {query_state['snapshot_id']}")
            if cfg.get('query_preparation_contract')=='serialized_durable_submission_v1':
                dispatched_preparation=False
                def prepare_submission():
                    nonlocal dispatched_preparation
                    if cfg.get('submission_availability_contract')=='release_and_wait_for_real_sample_v1':
                        checked=stamp();last=sampler.available_sample_end_ns()
                        if last is None or (checked['monotonic_ns']-last)/1e9>t['max_age_seconds']:
                            raise PreparationSampleUnavailable(checked,last)
                    fresh=[sampler.window(seconds=w,max_interval_seconds=t['max_interval_seconds'],max_age_seconds=t['max_age_seconds']) for w in t['window_seconds']]
                    log.emit('query_observation',measurement_id=mid,query_id=qid,role='trace_query',windows=fresh,**query_state)
                    checked=stamp()
                    if checked['monotonic_ns']>=hi:
                        require(cfg.get('boundary_preparation_contract')=='retain_queued_unsubmitted_observation_v1','Unregistered boundary preparation')
                        log.emit('query_observation_not_dispatched',source_query_id=identity,measurement_id=mid,horizon_end_monotonic_ns=hi,checked_at=checked,reason='horizon_reached_before_dispatch')
                        return False
                    guard();ledger.transition(identity,'dispatched',measurement_id=mid,session_id='query_0')
                    dispatched_preparation=True
                    return True
                try:
                    probe=None
                    while time.monotonic_ns()<hi:
                        try:
                            probe=rec.execute(query,sql,role='trace_query',query_id=qid,measurement_id=mid,prepare_submission=prepare_submission,
                                              latest_start_ns=hi if cfg.get('rpc_boundary_contract')=='guarded_rpc_start_requeue_v1' else None)
                            break
                        except PreparationSampleUnavailable as unavailable:
                            log.emit('query_preparation_deferred',measurement_id=mid,source_query_id=identity,
                                     checked_at=unavailable.checked,last_available_sample_end_ns=unavailable.last,
                                     reason='expired_durable_sample_after_lock_acquisition_no_sql_intent')
                            if not sampler.wait_for_available_sample(deadline_ns=hi,max_age_seconds=t['max_age_seconds'],measurement_id=mid):break
                    if probe is None:break
                    if probe.get('submitted') is False:
                        ledger.transition(identity,'queued',measurement_id=mid,session_id='query_0',reason='horizon_before_rpc')
                        dispatched_preparation=False
                        break
                    ledger.transition(identity,'completed',measurement_id=mid,session_id='query_0');probes.append(probe)
                except Exception:
                    if dispatched_preparation:ledger.transition(identity,'failed',measurement_id=mid,session_id='query_0')
                    raise
                continue
            log.emit('query_observation',measurement_id=mid,query_id=qid,role='trace_query',windows=windows,**query_state)
            checked=stamp()
            if checked['monotonic_ns']>=hi:
                require(cfg.get('boundary_preparation_contract')=='retain_queued_unsubmitted_observation_v1','Observation logging crossed horizon; retain failed attempt')
                log.emit('query_observation_not_dispatched',source_query_id=identity,measurement_id=mid,horizon_end_monotonic_ns=hi,checked_at=checked,reason='horizon_reached_before_dispatch')
                break  # Actual state remains queued; no SQL request or dispatch.

            ledger.transition(identity,'dispatched',measurement_id=mid,session_id='query_0');guard()
            sql=query_templates(table)[qid].replace(f'FROM {table}',f"FROM {table} VERSION AS OF {query_state['snapshot_id']}")
            try:
                probe=rec.execute(query,sql,role='trace_query',query_id=qid,measurement_id=mid);ledger.transition(identity,'completed',measurement_id=mid,session_id='query_0');probes.append(probe)
            except Exception:
                ledger.transition(identity,'failed',measurement_id=mid,session_id='query_0');raise
        for thread in threads:thread.join()
        if errors:raise errors[0]
        final_state=inventory()
        if arm:
            log.emit('common_horizon_final_state',**final_state)
            for check_state in (initial_state,final_state):
                snapshot=check_state['snapshot_id']
                result=execute(f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {table} VERSION AS OF {snapshot}) UNION ALL (SELECT * FROM {table} VERSION AS OF {snapshot} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences")
                require(result['rows'][0][0]==0,'Arm logical multiset changed')
                log.emit('common_horizon_multiset_validation',snapshot_id=snapshot,measurement_id=result['measurement_id'])
        rest.capture('jobs');rest.capture('stages')
        with log.lock:engine_rows=[json.loads(line) for line in (out/'events.jsonl').open()]
        jobs,stages=merged_engine_frames(engine_rows)
        retained=ArchivedTaskEvidence(engine_rows,live=rest)
        for probe in probes:task_intervals(jobs,stages,retained,marker=probe['marker'])
        for action in actions:task_intervals(jobs,stages,retained,rewrite_table=table,request=action)
        sampler.stop();result=audit(out);safe_to_close=True;result['code_revision']=revision;(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    except Exception as e:
        log.emit('trace_queue_failed',error_type=type(e).__name__,error=str(e));(out/'failure.json').write_text(json.dumps({'status':'failed_preserved','error':str(e)},indent=2)+'\n');raise
    finally:
        for thread in threads:thread.join()
        if hasattr(sampler,'thread'):sampler.stop()
        log.close();lock.close()
        if safe_to_close:
            for c in connections:c.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config');p.add_argument('--expected-revision');p.add_argument('--audit-directory');p.add_argument('--audit-output');a=p.parse_args()
    if a.audit_directory:
        with Path(a.audit_output).open('x') as f:json.dump(audit(a.audit_directory),f,indent=2);f.write('\n')
    else:run(a.config,a.expected_revision)
