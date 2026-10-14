#!/usr/bin/env python3
"""Real SF1 null controls; observed treatment cadence, no rewrite and no training labels."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from experiment_validation import load_json, require, verified_file, sha256
from physical_measurements import EventLog, StatementRecorder, SparkEvidence, TelemetrySampler
from query_observation_binding import verify_observations
from statement_timing import completed_statements
from run_correctness_pilot import query_templates, canonical
from engine_overlap import task_intervals, engine_time

ROLES = ('control_before', 'placebo_middle', 'control_after')
REFERENCE_ROLES = ('control_before', 'during_rewrite', 'control_after_original_snapshot')


def reference(spec, base):
    path = verified_file(spec, base)
    records = list(completed_statements([path]).values())
    selected = [[r for r in records if r['role'] == role] for role in REFERENCE_ROLES]
    require(all(len(group) == 1 for group in selected), 'Ambiguous reference roles')
    selected = [group[0] for group in selected]
    require(all(r['query_id'] == 1 for r in selected), 'Reference query changed')
    gaps = [(selected[i+1]['client_execute_start']['monotonic_ns'] - selected[i]['fetch_end']['monotonic_ns']) / 1e9 for i in range(2)]
    require(all(g >= 0 for g in gaps), 'Overlapping reference query cadence')
    return gaps


def audit(directory, *, completed_blocks=None):
    directory = Path(directory)
    cfg = json.loads((directory/'config.json').read_text())
    require(cfg['schema_version'] == 'no_maintenance_controls_v1', 'Unknown null protocol')
    rows = [json.loads(line) for line in (directory/'events.jsonl').open()]
    protocols=[r for r in rows if r['kind']=='null_protocol']
    require(len(protocols)==1 and protocols[0]['configuration']==cfg, 'Raw configuration differs')
    for name,digest in protocols[0]['code_sha256'].items(): require(sha256(directory/'code'/name)==digest, 'Frozen code changed')
    require(sha256(directory/'preparation_result.json')==cfg['preparation_result']['sha256'], 'Source receipt changed')
    require(not any(r['kind'] == 'statement_failed' for r in rows), 'Failed statement retained; control rejected')
    requests = {r['measurement_id']: r for r in rows if r['kind'] == 'statement_requested'}
    require(not any('rewrite_data_files' in r['sql'].lower() for r in requests.values()), 'Maintenance in null control')
    complete = completed_statements([directory/'events.jsonl'])
    require(len(complete) == len(requests), 'Unfinished statements')
    checks = verify_observations(rows, cfg)
    blocks = [r for r in rows if r['kind'] == 'null_block_complete']
    expected=len(cfg['blocks']) if completed_blocks is None else completed_blocks
    require(0 < expected <= len(cfg['blocks']) and len(blocks) == expected, 'Missing registered block')
    observations = [r for r in rows if r['kind'] == 'query_observation']
    require(len(observations) == len(blocks)*len(ROLES), 'Unregistered/missing observations')
    summary = []
    for block, registered in zip(blocks, cfg['blocks']):
        require(block['table'] == registered['destination_table'], 'Block table differs')
        probes = [complete[(cfg['experiment_id'], mid)] for mid in block['query_measurement_ids']]
        require([r['role'] for r in probes] == list(ROLES), 'Null role order differs')
        require(all(canonical(r['rows']) == canonical(probes[0]['rows']) for r in probes), 'Query results changed')
        own = [r for r in observations if r['table'] == block['table']]
        require(len(own) == 3 and all(r['snapshot_id'] == block['initial']['snapshot_id'] and r['file_state'] == block['initial']['file_state'] for r in own), 'Null state differs')
        require(block['initial'] == block['final'], 'Snapshot or exact files changed in null block')
        multiset = complete[(cfg['experiment_id'], block['multiset_measurement_id'])]
        source = json.loads((directory/'preparation_result.json').read_text())
        expected_sql = f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {block['table']}) UNION ALL (SELECT * FROM {block['table']} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences"
        require(requests[block['multiset_measurement_id']]['sql'] == expected_sql and multiset['rows'] == [[0]], 'Raw exact multiset check failed')
        gaps = reference({'path': str(directory / block['reference_file']), 'sha256': registered['reference_events']['sha256']}, directory)
        actual_gaps = [(probes[i+1]['client_execute_start']['monotonic_ns']-probes[i]['fetch_end']['monotonic_ns'])/1e9 for i in range(2)]
        require(all(actual >= planned for actual, planned in zip(actual_gaps, gaps)), 'Observed cadence shortened')
        prior=[r for r in rows if r['recorded']['monotonic_ns'] < block['recorded']['monotonic_ns'] and r['kind']=='spark_rest']
        jobs=[r['payload'] for r in prior if r['resource']=='jobs'][-1]
        stages=[r['payload'] for r in prior if r['resource']=='stages'][-1]
        class RecordedREST:
            def capture_tasks(self, stage, attempt, count):
                resource=f'stages/{stage}/{attempt}/taskList?length={count}'
                found=[r['payload'] for r in prior if r['resource']==resource]
                require(found and len(found[-1])==count, 'Missing raw completed tasks')
                return found[-1]
        rebuilt=[task_intervals(jobs,stages,RecordedREST(),marker=r['marker']) for r in probes]
        require(rebuilt==block['task_intervals'], 'Task intervals differ from raw REST')
        for probe in probes:
            start=datetime.fromisoformat(probe['client_execute_start']['utc']).timestamp(); end=datetime.fromisoformat(probe['fetch_end']['utc']).timestamp()
            overlapping=[j for j in jobs if engine_time(j['submissionTime'])<end and (not j.get('completionTime') or engine_time(j['completionTime'])>start)]
            require(overlapping and all(probe['marker'] in str(j.get('description','')) for j in overlapping), 'Raw unrelated Spark contamination')
        latency = [r['client_elapsed_ns']/1e6 for r in probes]
        summary.append({'table':block['table'], 'latencies_ms':dict(zip(ROLES,latency)), 'signed_placebo_contrast_ms':latency[1]-(latency[0]+latency[2])/2, 'after_minus_before_ms':latency[2]-latency[0], 'registered_reference_gaps_seconds':gaps, 'actual_gaps_seconds':actual_gaps})
    return {'status':'audited_null_diagnostic_only', 'blocks':summary, 'observation_checks':checks, 'events_sha256':sha256(directory/'events.jsonl'), 'cost_training_accepted':False, 'limitations':cfg['limitations']}


def run(config_path, revision):
    cfg, base = load_json(config_path)
    repo = Path(__file__).resolve().parents[2]
    require(cfg['schema_version'] == 'no_maintenance_controls_v1' and cfg['query_id'] == 1, 'Unregistered control protocol')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip() == revision, 'HEAD mismatch')
    require(subprocess.run(['git','diff','--exit-code','HEAD','--','scripts/phase6-live-evaluation/*.py'],cwd=repo,capture_output=True).returncode == 0, 'Dirty measurement code')
    require(len({b['destination_table'] for b in cfg['blocks']}) == len(cfg['blocks']) > 0, 'Duplicate/empty blocks')
    source_path = verified_file(cfg['preparation_result'],base)
    source = json.loads(source_path.read_text())
    require(source['status'] == 'accepted_correctness_source', 'Unaccepted source')
    verified_file(cfg['source'],base); verified_file(cfg['generator_provenance'],base)
    gaps = [reference(b['reference_events'],base) for b in cfg['blocks']]
    deadline = datetime.fromisoformat(cfg['no_new_operation_after_utc'])
    def guard():
        require(datetime.now(timezone.utc) < deadline, 'No new physical operation after registered cutoff')
    guard()
    lock = (repo/'results'/'.physical_correctness.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    out = (base/cfg['output_directory']).resolve(); out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(config_path,out/'config.json'); shutil.copy2(source_path,out/'preparation_result.json')
    code = out/'code'; code.mkdir()
    for name in ('run_no_maintenance_controls.py','physical_measurements.py','experiment_validation.py','query_observation_binding.py','statement_timing.py','telemetry_binding.py','run_correctness_pilot.py','engine_overlap.py'):
        shutil.copy2(Path(__file__).parent/name,code/name)
    for i,b in enumerate(cfg['blocks']): shutil.copy2(verified_file(b['reference_events'],base),out/f'reference_{i+1:02d}.jsonl')
    log = EventLog(out/'events.jsonl',cfg['experiment_id']); rec = StatementRecorder(log)
    rest = SparkEvidence(cfg['spark_rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log)
    sampler = TelemetrySampler(log,cfg['telemetry']['interval_seconds']); connections=[]
    log.emit('null_protocol',configuration=cfg,code_revision=revision,code_sha256={p.name:sha256(p) for p in code.iterdir()})
    from pyhive import hive
    try:
        for _ in range(2): connections.append(hive.Connection(**{k:cfg['engine'][k] for k in ('host','port','username')}))
        metadata, query = [c.cursor() for c in connections]
        def execute(sql,role='metadata'):
            guard(); return rec.execute(metadata,sql,role=role)
        require(not rest._capture('jobs?status=running'), 'Active Spark work; refuse')
        require(execute('SELECT version()')['rows'][0][0].split()[0] == cfg['engine']['expected_version'], 'Engine mismatch')
        rest.capture('environment')
        require(execute(f"SELECT snapshot_id FROM {source['table']}.history ORDER BY made_current_at DESC LIMIT 1")['rows'][0][0] == source['snapshot_id'], 'Source snapshot changed')
        sampler.start()
        for i, block in enumerate(cfg['blocks']):
            import re
            table=block['destination_table']; require(re.fullmatch(r'local\.experiment\.integrity_null_[a-z0-9_]+',table), 'Dedicated target required')
            require(not rest._capture('jobs?status=running'), 'Active work before block')
            require(not any(r[1] == table.split('.')[-1] for r in execute('SHOW TABLES IN local.experiment')['rows']), 'Target exists; never overwrite')
            execute(f"CREATE TABLE {table} USING iceberg AS SELECT /*+ REPARTITION({source['file_count']}) */ * FROM {source['table']} VERSION AS OF {source['snapshot_id']}", 'create_isolated_target')
            def inventory():
                snap=execute(f'SELECT snapshot_id FROM {table}.history ORDER BY made_current_at DESC LIMIT 1')
                files=execute(f'SELECT file_path, record_count, file_size_in_bytes FROM {table}.files')
                return {'table':table,'snapshot_id':snap['rows'][0][0], 'snapshot_measurement_id':snap['measurement_id'], 'file_inventory_measurement_id':files['measurement_id'], 'file_state':{'file_count':len(files['rows']),'record_count':sum(r[1] for r in files['rows']),'total_bytes':sum(r[2] for r in files['rows'])}}, sorted(files['rows'])
            state, files=inventory(); initial={'snapshot_id':state['snapshot_id'],'files':files}
            require(state['file_state']['record_count'] == source['record_count'] and state['file_state']['file_count'] == source['file_count'], 'Initial layout mismatch')
            time.sleep(cfg['telemetry']['warmup_seconds']); probes=[]
            for j,role in enumerate(ROLES):
                if j: time.sleep(gaps[i][j-1])
                guard(); identity=uuid.uuid4().hex; t=cfg['telemetry']
                windows=[sampler.window(seconds=w,max_interval_seconds=t['max_interval_seconds'],max_age_seconds=t['max_age_seconds']) for w in t['window_seconds']]
                log.emit('query_observation',measurement_id=identity,query_id=cfg['query_id'],role=role,windows=windows,**state)
                sql=query_templates(table)[cfg['query_id']].replace(f'FROM {table}',f"FROM {table} VERSION AS OF {state['snapshot_id']}")
                guard(); probes.append(rec.execute(query,sql,role=role,query_id=cfg['query_id'],measurement_id=identity))
            end, end_files=inventory(); require(initial == {'snapshot_id':end['snapshot_id'],'files':end_files}, 'Null layout changed')
            require(all(canonical(p['rows']) == canonical(probes[0]['rows']) for p in probes), 'Null query results differ')
            jobs=rest.capture('jobs'); stages=rest.capture('stages')
            tasks=[task_intervals(jobs,stages,rest,marker=p['marker']) for p in probes]
            for p in probes:
                start=datetime.fromisoformat(p['client_execute_start']['utc']).timestamp(); finish=datetime.fromisoformat(p['fetch_end']['utc']).timestamp()
                overlapping=[job for job in jobs if engine_time(job['submissionTime']) < finish and (not job.get('completionTime') or engine_time(job['completionTime']) > start)]
                require(overlapping and all(p['marker'] in str(job.get('description','')) for job in overlapping), 'Other Spark jobs contaminated null query')
            difference=execute(f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {table}) UNION ALL (SELECT * FROM {table} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences",'full_multiset_validation')
            require(len(difference['rows']) == 1 and difference['rows'][0][0] == 0, 'Exact multiset mismatch')
            log.emit('null_block_complete',index=i+1,table=table,initial=initial,final={'snapshot_id':end['snapshot_id'],'files':end_files},query_measurement_ids=[p['measurement_id'] for p in probes],task_intervals=tasks,multiset_measurement_id=difference['measurement_id'],reference_file=f'reference_{i+1:02d}.jsonl')
            audit(out, completed_blocks=i+1)
            (out/'progress.json').write_text(json.dumps({'status':'running','completed_blocks':i+1,'planned_blocks':len(cfg['blocks'])},indent=2)+'\n')
        sampler.stop()
        result=audit(out); result['code_revision']=revision
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result),flush=True)
    except Exception as exc:
        log.emit('null_control_failed',error_type=type(exc).__name__,error=str(exc),preservation='All tables/raw evidence retained; no cancellation')
        (out/'failure.json').write_text(json.dumps({'status':'failed_preserved','error':str(exc)},indent=2)+'\n'); raise
    finally:
        if hasattr(sampler,'thread'):sampler.stop()
        log.close(); lock.close()
        for c in connections:c.close()


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--config');p.add_argument('--expected-revision');p.add_argument('--audit-directory');p.add_argument('--audit-output')
    a=p.parse_args()
    if a.audit_directory:
        result=audit(a.audit_directory)
        with Path(a.audit_output).open('x') as stream: json.dump(result,stream,indent=2);stream.write('\n')
    else: run(a.config,a.expected_revision)
