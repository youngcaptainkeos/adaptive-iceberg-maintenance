#!/usr/bin/env python3
"""One isolated original-snapshot matched measurement pilot, never training approval."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import fcntl,json,re,shutil,subprocess,time,uuid
from pathlib import Path
from experiment_validation import load_json,require,verified_file,sha256
from physical_measurements import EventLog,StatementRecorder,SparkEvidence,TelemetrySampler
from run_correctness_pilot import query_templates,canonical
from engine_overlap import task_intervals,overlap_evidence,engine_time
from query_observation_binding import verify_observations
from statement_timing import completed_statements


def run(config_path,expected_revision):
    cfg,base=load_json(config_path);repo=Path(__file__).resolve().parents[2]
    require(cfg['schema_version']=='matched_snapshot_measurement_pilot_v1' and cfg['purpose']=='physical_matching_and_feature_integrity_only','Unreviewed pilot')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==expected_revision,'Full revision mismatch')
    require(subprocess.run(['git','diff','--exit-code','HEAD','--','scripts/phase6-live-evaluation/*.py'],cwd=repo,capture_output=True).returncode==0,'Dirty experiment Python code')
    deadline=datetime.fromisoformat(cfg['no_new_operation_after_utc'])
    def before_operation():require(datetime.now(timezone.utc)<deadline,'Physical-operation cutoff; preserve state')
    require(cfg.get('decision_feature_contract')=='pre_action_windows_v1','Pre-action decision context required for new episodes')
    before_operation();source=json.loads(verified_file(cfg['preparation_result'],base).read_text());verified_file(cfg['source'],base);verified_file(cfg['generator_provenance'],base)
    require(source['status']=='accepted_correctness_source' and re.fullmatch(r'local\.experiment\.integrity_sf1_[a-z0-9_]+',source['table']),'Unaccepted benchmark source')
    table=cfg['destination_table'];require(re.fullmatch(r'local\.experiment\.integrity_matched_[a-z0-9_]+',table),'Dedicated new table required')
    require(isinstance(cfg['query_id'],int) and not isinstance(cfg['query_id'],bool) and cfg['query_id'] in range(4) and cfg['layout']=='repartition_to_verified_source_file_count','Declare query/layout')
    require(cfg['rewrite_options']=={'partial-progress.enabled':'false'},'Atomic existing binpack intervention only')
    t=cfg['telemetry'];require(t['window_seconds']==[60,300] and t['warmup_seconds']>max(t['window_seconds']),'Declared complete histories required')
    require(cfg['poll_interval_seconds']>0 and cfg['engine_start_observation_seconds']>0,'Declare bounded observation parameters')
    lock=(repo/'results'/'.physical_correctness.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    output=(base/cfg['output_directory']).resolve();output.mkdir(parents=True,exist_ok=False);shutil.copy2(config_path,output/'config.json');code=output/'code';code.mkdir()
    for name in ['run_matched_measurement_pilot.py','query_observation_binding.py','physical_measurements.py','run_correctness_pilot.py','engine_overlap.py','experiment_validation.py','telemetry_binding.py','statement_timing.py']:
        shutil.copy2(Path(__file__).parent/name,code/name)
    log=EventLog(output/'events.jsonl',cfg['experiment_id']);rec=StatementRecorder(log);rest=SparkEvidence(cfg['spark_rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log);sampler=TelemetrySampler(log,t['interval_seconds'])
    log.emit('matched_protocol',configuration=cfg,code_revision=expected_revision,code_sha256={p.name:sha256(p) for p in code.iterdir()})
    from pyhive import hive
    cursors=[];connections=[];safe_to_close=False
    def process_snapshot(identity):
        import psutil
        processes=[]
        for process in psutil.process_iter(['pid','name','cpu_times','memory_info']):
            try:
                info=process.info;cpu=info['cpu_times'];memory=info['memory_info']
                processes.append({'pid':info['pid'],'name':info['name'],'cpu_times':cpu._asdict() if cpu is not None else None,'rss_bytes':memory.rss if memory is not None else None})
            except psutil.Error as exc:processes.append({'pid':process.pid,'inaccessible':type(exc).__name__})
        log.emit('host_process_snapshot',measurement_id=identity,processes=processes)
    def execute(sql,role='metadata'):
        before_operation();return rec.execute(cursors[0],sql,role=role)
    try:
        for _ in range(2):
            connection=hive.Connection(**{k:cfg['engine'][k] for k in ['host','port','username']});connections.append(connection);cursors.append(connection.cursor())
        require(not rest._capture('jobs?status=running'),'Existing Spark work; refused')
        require(execute('SELECT version()')['rows'][0][0].split()[0]==cfg['engine']['expected_version'],'Engine mismatch')
        rest.capture('environment')
        require(execute(f"SELECT snapshot_id FROM {source['table']}.history ORDER BY made_current_at DESC LIMIT 1")['rows'][0][0]==source['snapshot_id'],'Source snapshot changed')
        require(not any(r[1]==table.split('.')[-1] for r in execute('SHOW TABLES IN local.experiment')['rows']),'Target exists; never overwrite')
        execute(f"CREATE TABLE {table} USING iceberg AS SELECT /*+ REPARTITION({source['file_count']}) */ * FROM {source['table']} VERSION AS OF {source['snapshot_id']}",'create_isolated_target')
        def inventory():
            snapshot=execute(f'SELECT snapshot_id FROM {table}.history ORDER BY made_current_at DESC LIMIT 1');files=execute(f'SELECT file_path, record_count, file_size_in_bytes FROM {table}.files')
            state={'file_count':len(files['rows']),'record_count':sum(r[1] for r in files['rows']),'total_bytes':sum(r[2] for r in files['rows'])}
            return {'table':table,'snapshot_id':snapshot['rows'][0][0],'snapshot_measurement_id':snapshot['measurement_id'],'file_inventory_measurement_id':files['measurement_id'],'file_state':state}
        original=inventory();require(original['file_state']['record_count']==source['record_count'] and original['file_state']['file_count']==source['file_count']>1,'Original layout failed')
        log.emit('matched_initial_state',**original);sampler.start();time.sleep(t['warmup_seconds'])
        def probe(role,state):
            before_operation();identity=uuid.uuid4().hex
            windows=[sampler.window(seconds=w,max_interval_seconds=t['max_interval_seconds'],max_age_seconds=t['max_age_seconds']) for w in t['window_seconds']]
            require(all(w['covered_seconds']/w['window_seconds']>=t['minimum_coverage_fraction'] for w in windows),'Coverage below unchanged gate')
            process_snapshot(identity)
            log.emit('query_observation',measurement_id=identity,query_id=cfg['query_id'],role=role,windows=windows,**state)
            sql=query_templates(table)[cfg['query_id']].replace(f'FROM {table}',f"FROM {table} VERSION AS OF {state['snapshot_id']}")
            return rec.execute(cursors[0],sql,role=role,query_id=cfg['query_id'],measurement_id=identity)
        before=probe('control_before',original);during=None
        maintenance_id=uuid.uuid4().hex
        decision_windows=[sampler.window(seconds=w,max_interval_seconds=t['max_interval_seconds'],max_age_seconds=t['max_age_seconds']) for w in t['window_seconds']]
        require(all(w['covered_seconds']/w['window_seconds']>=t['minimum_coverage_fraction'] for w in decision_windows),'Pre-action coverage below unchanged gate')
        process_snapshot(maintenance_id)
        log.emit('maintenance_decision_observation',measurement_id=maintenance_id,query_id=None,role='maintenance',windows=decision_windows,**original)
        with ThreadPoolExecutor(max_workers=1) as pool:
            before_operation()
            maintenance=pool.submit(rec.execute,cursors[1],f"CALL local.system.rewrite_data_files(table => '{table.removeprefix('local.')}', strategy => 'binpack', options => map('partial-progress.enabled','false'))",role='maintenance',measurement_id=maintenance_id)
            until=time.monotonic()+cfg['engine_start_observation_seconds']
            while time.monotonic()<until and not maintenance.done():
                stages=rest._capture('stages?status=active')
                active=[s for s in stages if str(s.get('description','')).startswith('Rewriting ') and str(s.get('description','')).endswith(' in '+table) and s.get('numActiveTasks',0)>0]
                if active:
                    log.emit('rewrite_task_observed_active',stage_ids=[s['stageId'] for s in active]);during=probe('during_rewrite',original);break
                time.sleep(cfg['poll_interval_seconds'])
            rewritten=maintenance.result()  # Always allow the physical rewrite to finish naturally.
        execute(f'REFRESH TABLE {table}','post_commit_session_refresh');after_state=inventory()
        after=probe('control_after_original_snapshot',original);layout=probe('compacted_layout',after_state)
        values=dict(zip(rewritten['columns'],rewritten['rows'][0]));require(values['rewritten_data_files_count']>0 and values['rewritten_bytes_count']>0,'No useful physical rewrite')
        require(after_state['file_state']['record_count']==original['file_state']['record_count'] and after_state['file_state']['file_count']==original['file_state']['file_count']-values['rewritten_data_files_count']+values['added_data_files_count'],'Physical metadata conservation failed')
        queries=[before,after,layout]+([during] if during else []);require(all(canonical(q['rows'])==canonical(before['rows']) for q in queries),'Matched/compacted query results differ')
        jobs=rest.capture('jobs');stages=rest.capture('stages');rewrite_tasks=task_intervals(jobs,stages,rest,rewrite_table=table,request=rewritten)
        exposures=[dict(measurement_id=q['measurement_id'],**overlap_evidence(task_intervals(jobs,stages,rest,marker=q['marker']),rewrite_tasks)) for q in queries]
        require(all(not q['verified_task_lifetime_overlap'] for q in exposures[:3]),'Control/layout task contamination')
        rows=[json.loads(line) for line in (output/'events.jsonl').open()];markers=[r['marker'] for r in rows if r['kind']=='statement_requested']
        for job in jobs:
            overlaps=any(engine_time(job['submissionTime'])<datetime.fromisoformat(q['fetch_end']['utc']).timestamp() and (not job.get('completionTime') or engine_time(job['completionTime'])>datetime.fromisoformat(q['client_execute_start']['utc']).timestamp()) for q in queries)
            if overlaps:require(any(m in str(job.get('description','')) for m in markers) or str(job.get('description','')).endswith(' in '+table),'Unrelated foreground Spark job contaminated probe')
        difference=execute(f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {table}) UNION ALL (SELECT * FROM {table} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences",'full_multiset_validation')['rows'][0][0];require(difference==0,'Exact row multiset changed')
        sampler.stop();completed_statements([output/'events.jsonl']);rows=[json.loads(line) for line in (output/'events.jsonl').open()];checks=verify_observations(rows,cfg)
        decision_checks=verify_observations(rows,cfg,kind='maintenance_decision_observation');require(len(decision_checks)==1,'One bound pre-action decision observation required')
        require(during is not None and exposures[-1]['verified_task_lifetime_overlap'],'Missed actual task overlap; no positive treatment label')
        result={'status':'accepted_matched_measurement_integrity_only','table':table,'original':original,'compacted':after_state,'rewrite_result':values,'query_observation_checks':checks,'decision_observation_checks':decision_checks,'task_exposures':exposures,'multiset_difference_count':difference,'code_revision':expected_revision,'limitations':['One query/one physical rewrite, not variance or statistical/cost/model approval','Controlled benchmark layout, not natural fragmentation or trace replay','Host background/cache/time trends recorded only through counters; matched snapshots alone are not a causal guarantee','REST/logging observation overhead differs during maintenance; no idle-host or pure CPU-execution claim','No intensity/small-file eligibility/forecast feature invented or training export']}
        safe_to_close=True
        log.emit('matched_pilot_accepted',**result);(output/'result.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps(result,default=str))
    except Exception as exc:
        log.emit('matched_pilot_failed',error_type=type(exc).__name__,error=str(exc),table=table,preservation='Preserve table, data, every failed artifact; no cancellation');raise
    finally:
        try:
            if hasattr(sampler,'thread'):sampler.stop()
        finally:log.close();lock.close()
        # Close only our completed client sessions; never cancel an operation/service.
        if safe_to_close:
            for cursor in cursors:cursor.close()
            for connection in connections:connection.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--expected-revision',required=True);a=p.parse_args();run(a.config,a.expected_revision)
