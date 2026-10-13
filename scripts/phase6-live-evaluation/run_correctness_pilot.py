#!/usr/bin/env python3
"""Bounded physical correctness pilot; no policy, trace replay or training approval."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import fcntl
import json
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time

from experiment_validation import load_json, require, verified_file, sha256
from physical_measurements import EventLog, StatementRecorder, SparkEvidence, TelemetrySampler
from engine_overlap import task_intervals, overlap_evidence


def query_templates(table):
    # Retained existing four benchmark query identities; dates/predicates are SQL semantics.
    return [f"SELECT count(*), sum(L_EXTENDEDPRICE * (1 - L_DISCOUNT)) FROM {table} WHERE L_SHIPDATE >= '1995-01-01' AND L_SHIPDATE <= '1995-03-31'",
            f'SELECT L_RETURNFLAG, L_LINESTATUS, count(*), sum(L_QUANTITY), avg(L_DISCOUNT) FROM {table} GROUP BY L_RETURNFLAG, L_LINESTATUS',
            f'SELECT count(*) FROM {table} WHERE L_DISCOUNT > 0.05 AND L_QUANTITY < 24',
            f"SELECT max(L_EXTENDEDPRICE), min(L_EXTENDEDPRICE) FROM {table} WHERE L_SHIPDATE >= '1996-01-01'"]


def canonical(rows):
    return sorted(json.dumps(list(row),default=str,allow_nan=False) for row in rows)


def run(config_path,expected_revision):
    cfg,base=load_json(config_path)
    require(cfg.get('schema_version')=='physical_correctness_pilot_v1' and cfg.get('purpose')=='physical_correctness_only','Not a correctness protocol')
    require(bool(cfg.get('configuration_rationale')), 'Rationale required')
    repo=Path(__file__).resolve().parents[2]
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    require(revision==expected_revision,'Revision mismatch')
    require(subprocess.run(['git','diff','--exit-code','HEAD','--','scripts/phase6-live-evaluation/*.py'],cwd=repo,capture_output=True).returncode==0,'Dirty experiment code')
    source_path=verified_file(cfg['preparation_result'],base)
    source=json.loads(source_path.read_text())
    require(source['status']=='accepted_correctness_source','Preparation failed')
    verified_file(cfg['source'],base)
    verified_file(cfg['generator_provenance'],base)
    require(re.fullmatch(r'local\.experiment\.integrity_sf1_[a-z0-9_]+',source['table']), 'Unreviewed source table')
    target=cfg['destination_table']
    require(re.fullmatch(r'local\.experiment\.integrity_pilot_[a-z0-9_]+',target),'New dedicated pilot table required')
    engine=cfg['engine']
    require(engine['host']=='127.0.0.1' and engine['username']=='ccbd','Reviewed local worker3 engine required')
    require(cfg['minimum_overlap_queries'] in range(1,5),'Declare overlap gate for four-query correctness pilot')
    options=cfg['rewrite_options']
    require(options=={'partial-progress.enabled':'false'},'Pilot uses default binpack eligibility with atomic commit')
    require(cfg.get('layout')=='repartition_to_verified_source_file_count','Declare diagnostic layout rule')
    telemetry=cfg['telemetry']
    require(telemetry['warmup_seconds']>telemetry['window_seconds']>0,'Warmup must cover the declared window')
    require(0<telemetry['minimum_coverage_fraction']<=1,'Declare coverage gate')
    lock=(repo/'results'/'.physical_correctness.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    output=(base/cfg['output_directory']).resolve();output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(config_path,output/'pilot_config.json');code=output/'code';code.mkdir()
    for name in ('run_correctness_pilot.py','physical_measurements.py','engine_overlap.py','experiment_validation.py'):
        shutil.copy2(Path(__file__).parent/name,code/name)
    log=EventLog(output/'events.jsonl',cfg['experiment_id'])
    rec=StatementRecorder(log)
    rest=SparkEvidence(cfg['spark_rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log)
    sampler=TelemetrySampler(log,telemetry['interval_seconds'])
    log.emit('pilot_protocol',configuration=cfg,code_revision=revision,code_sha256={p.name:sha256(p) for p in code.iterdir()})
    from pyhive import hive
    def features():
        w=sampler.window(seconds=telemetry['window_seconds'],max_interval_seconds=telemetry['max_interval_seconds'],max_age_seconds=telemetry['max_age_seconds'])
        require(w['covered_seconds']/w['window_seconds']>=telemetry['minimum_coverage_fraction'],'Insufficient measured telemetry coverage')
        return w
    with ExitStack() as stack:
        connections=[]
        # Open every worker connection before creating the barrier to avoid a failed
        # connection leaving other threads waiting forever.
        for _ in range(6):
            conn=hive.Connection(host=engine['host'],port=engine['port'],username=engine['username'])
            stack.callback(conn.close);cur=conn.cursor();stack.callback(cur.close);connections.append(cur)
        cur=connections[0]
        def execute(sql,role='metadata'):
            return rec.execute(cur,sql,role=role)
        try:
            jobs=rest.capture('jobs')
            require(not any(j['status']=='RUNNING' for j in jobs),'Existing Spark work; pilot refused')
            require(execute('SELECT version()')['rows'][0][0].split()[0]==engine['expected_version'],'Engine version mismatch')
            require(execute(f"SELECT snapshot_id FROM {source['table']}.history ORDER BY made_current_at DESC LIMIT 1")['rows'][0][0]==source['snapshot_id'],'Source snapshot changed')
            require(tuple(execute(f"SELECT sum(record_count),count(*) FROM {source['table']}.files")['rows'][0])==(source['record_count'],source['file_count']),'Source layout changed')
            require(not any(r[1]==target.split('.')[-1] for r in execute('SHOW TABLES IN local.experiment')['rows']),'Target exists; refuse overwrite')
            execute(f"CREATE TABLE {target} USING iceberg AS SELECT /*+ REPARTITION({source['file_count']}) */ * FROM {source['table']} VERSION AS OF {source['snapshot_id']}",'create_isolated_target')
            before=execute(f'SELECT sum(record_count),count(*),sum(file_size_in_bytes) FROM {target}.files')['rows'][0]
            require(before[0]==source['record_count'] and before[1]==source['file_count']>1,'Declared physical layout not achieved')
            before_snapshot=execute(f'SELECT snapshot_id FROM {target}.history ORDER BY made_current_at DESC LIMIT 1')['rows'][0][0]
            properties=execute(f'SHOW TBLPROPERTIES {target}')['rows']
            log.emit('pilot_initial_state',table=target,snapshot_id=before_snapshot,metadata=before,properties=properties)
            sampler.start();time.sleep(telemetry['warmup_seconds'])
            controls=[]
            for qid,sql in enumerate(query_templates(target)):
                log.emit('pre_query_features',query_id=qid,role='control',features=features())
                controls.append(rec.execute(cur,sql,role='control',query_id=qid))
            barrier=threading.Barrier(5)
            def query(qid):
                barrier.wait()
                log.emit('pre_query_features',query_id=qid,role='concurrent',features=features())
                return rec.execute(connections[qid+1],query_templates(target)[qid],role='concurrent',query_id=qid)
            def rewrite():
                barrier.wait()
                return rec.execute(connections[5],f"CALL local.system.rewrite_data_files(table => '{target.removeprefix('local.')}', strategy => 'binpack', options => map('partial-progress.enabled','false'))",role='maintenance')
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures=[pool.submit(query,qid) for qid in range(4)]
                maintenance=pool.submit(rewrite)
                concurrent=[f.result() for f in futures]
                rewritten=maintenance.result()
            rewrite_result=dict(zip(rewritten['columns'],rewritten['rows'][0]))
            require(rewrite_result.get('rewritten_data_files_count',0)>0,'No useful physical rewrite; refuse treatment labels')
            require(all(canonical(a['rows'])==canonical(b['rows']) for a,b in zip(controls,concurrent)),'Concurrent query result mismatch')
            # Another Thrift connection committed the rewrite. Invalidate this
            # connection's cached relation before reading post-commit metadata.
            execute(f'REFRESH TABLE {target}','post_commit_session_refresh')
            after=execute(f'SELECT sum(record_count),count(*),sum(file_size_in_bytes) FROM {target}.files')['rows'][0]
            require(after[0]==before[0] and after[1]==before[1]-rewrite_result['rewritten_data_files_count']+rewrite_result['added_data_files_count'],'Rewrite metadata conservation failed')
            physical=execute(f'SELECT count(*) FROM {target}','post_rewrite_physical_count')['rows'][0][0]
            require(physical==source['record_count'],'Physical rows changed')
            # Exact multiset comparison across all fields, including duplicate rows.
            difference=execute(f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {target}) UNION ALL (SELECT * FROM {target} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences",'full_multiset_validation')['rows'][0][0]
            require(difference==0,'Full row multiset changed')
            post=[rec.execute(cur,sql,role='post_rewrite',query_id=qid) for qid,sql in enumerate(query_templates(target))]
            require(all(canonical(a['rows'])==canonical(b['rows']) for a,b in zip(controls,post)),'Post-rewrite query result mismatch')
            jobs=rest.capture('jobs');stages=rest.capture('stages')
            rewrite_tasks=task_intervals(jobs,stages,rest,rewrite_table=target,request=rewritten)
            overlaps=[]
            for qid,query_result in enumerate(concurrent):
                tasks=task_intervals(jobs,stages,rest,marker=query_result['marker'])
                overlaps.append(dict(query_id=qid,measurement_id=query_result['measurement_id'],**overlap_evidence(tasks,rewrite_tasks)))
            # Controls must have no overlap with this maintenance event.
            for result in controls:
                tasks=task_intervals(jobs,stages,rest,marker=result['marker'])
                require(not overlap_evidence(tasks,rewrite_tasks)['verified_task_lifetime_overlap'],'Control contamination')
            log.emit('engine_overlap_review',queries=overlaps,rewrite_tasks=rewrite_tasks)
            overlap_count=sum(q['verified_task_lifetime_overlap'] for q in overlaps)
            require(overlap_count>=cfg['minimum_overlap_queries'],'Insufficient actual Spark task overlap')
            snapshot=execute(f'SELECT snapshot_id FROM {target}.history ORDER BY made_current_at DESC LIMIT 1')['rows'][0][0]
            result=dict(status='accepted_physical_correctness_pilot',table=target,before_snapshot=before_snapshot,after_snapshot=snapshot,before_metadata=before,after_metadata=after,rewrite_result=rewrite_result,physical_row_count=physical,multiset_difference_count=difference,overlaps=overlaps,code_revision=revision,limitations=['One SF1 correctness pilot, not performance inference or training data','Concurrent clients are a diagnostic, not observed trace arrivals','Task lifetime overlap is not simultaneous CPU-execution proof','No statistical claim or model approval'])
            log.emit('pilot_accepted',**result);(output/'result.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps(result,default=str))
        except Exception as exc:
            log.emit('pilot_failed',error_type=type(exc).__name__,error=str(exc),table=target,preservation='Keep every table/artifact; no forced cancellation')
            raise
        finally:
            try:
                if hasattr(sampler,'thread'): sampler.stop()
            finally:
                log.close();lock.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True);parser.add_argument('--expected-revision',required=True)
    args=parser.parse_args();run(args.config,args.expected_revision)
