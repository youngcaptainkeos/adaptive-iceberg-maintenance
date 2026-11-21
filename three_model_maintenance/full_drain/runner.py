"""Real fixed-start SF10 experiment with full foreground and rewrite completion.

Local construction only until worker3 gates pass. No model, simulator or implicit
parameter defaults. Frozen legacy collectors are imported, never patched.
"""
import argparse
import csv
import fcntl
import json
import queue
import shutil
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/phase6-live-evaluation'))
from physical_measurements import SparkEvidence
from experiment_validation import require
from three_model_maintenance.research.common import read, sha, utc, write_new,now
from three_model_maintenance.runtime.collector_bridge import build_classes
from three_model_maintenance.runtime.sf10_contract import pin_query, references, canonical_result
from three_model_maintenance.runtime.process_sampler import ProcessTelemetrySampler, validate_acquisition
from three_model_maintenance.runtime.terminal_archive import TerminalArchive
from three_model_maintenance.runtime.direct_task_retention import DirectTaskRetention
from .contract import ROOT, WORKER, checked, validate, verify_inputs,verify_committed
from .ledger import FullDrainLedger
from .accounting import reconstruct
from .action_submission import execute_action


def run(protocol,expected_head):
    require(ROOT==WORKER,'Physical execution only in registered worker3 checkout')
    cfg=validate(read(protocol));verify_inputs(cfg)
    verify_committed(protocol,cfg,expected_head)
    deadline=utc(cfg['no_new_operation_after_utc'])
    require(datetime.now(timezone.utc)<utc(cfg['no_new_episode_after_utc']),'Episode admission expired')
    def guard():
        require(not errors,'Earlier asynchronous failure stops dependent SQL')
        require(datetime.now(timezone.utc)<deadline,'No new SQL after operational cutoff; preserve incomplete cohort')
    out=Path(cfg['output_directory']).resolve()
    require(out.is_relative_to(ROOT/'results') and not out.exists(),'Exclusive repository result directory required')
    out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(protocol,out/'config.json')
    (out/'inputs').mkdir()
    for name,spec in cfg['inputs'].items():shutil.copyfile(checked(spec),out/'inputs'/name)
    shutil.copyfile(checked(cfg['typed_reference']),out/'inputs'/'typed_reference')
    shutil.copyfile(checked(cfg['study_registration']),out/'inputs'/'study_registration')
    for name in cfg['code_sha256']:
        target=out/'code'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    locks=[];threads=[];connections=[];errors=[];done=threading.Event();log=None;sampler=None
    probes=[];actions=[];safe=False;ledger=None
    try:
        for name in ('.three_model_collection.lock','.queue_aware_study.lock','.physical_correctness.lock'):
            stream=(ROOT/'results'/name).open('a');locks.append(stream);fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(shutil.disk_usage(out).free>=cfg['minimum_free_bytes'],'Insufficient registered disk capacity')
        guard()
        source=read(checked(cfg['inputs']['source_preparation']))
        require(source['status']=='accepted_sf10_trace_source_with_typed_capability','SF10 source not accepted')
        source_cfg=read(checked(cfg['inputs']['source_config']))
        require(cfg['query_suite']==source_cfg['query_suite'] and cfg['sf10_tables']==source_cfg['sf10_tables']
                and cfg['typed_reference']==source_cfg['typed_reference'],'Unverified source/query vocabulary')
        mapping=read(checked(cfg['inputs']['mapping_record']))
        mapping_path=checked(cfg['inputs']['mapping']);shutil.copyfile(mapping_path,out/'mapped_arrivals.csv')
        require(mapping['mapped_arrivals_sha256']==sha(mapping_path) and mapping['arrival_count']==cfg['arrival_count']
                and mapping['horizon_ns']==cfg['horizon_ns'],'Mapping registration differs')
        require(mapping['source_interval_start_utc']==cfg['source_start_utc']
                and mapping['source_interval_end_utc']==cfg['source_end_utc'],'Source window identity differs')
        mapped=list(csv.DictReader(mapping_path.open()))
        require(len(mapped)==cfg['arrival_count'] and len({r['source_query_id'] for r in mapped})==len(mapped),'Wrong offered population')
        require(all(0<=int(r['offset_ns'])<cfg['horizon_ns'] and int(r['query_id']) in range(6) for r in mapped),'Invalid mapped arrival')
        require(all(int(a['offset_ns'])<=int(b['offset_ns']) for a,b in zip(mapped,mapped[1:])),'Unsorted arrivals')
        expected=references(cfg)
        execution_cfg=dict(cfg,_protocol_sha256=sha(protocol))
        Log,Recorder=build_classes(execution_cfg)
        log=Log(out/'events.jsonl',cfg['experiment_id']);rec=Recorder(log)
        rest=SparkEvidence(cfg['spark_rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log)
        require(validate_acquisition(cfg),'Independent acquisition contract required')
        sampler=ProcessTelemetrySampler(log,cfg['telemetry']['interval_seconds'],journal=out/'telemetry_acquisition.jsonl',until=cfg['no_new_operation_after_utc'])
        log.emit('full_drain_protocol',configuration=cfg,code_revision=expected_head,protocol_sha256=sha(protocol))
        from pyhive import hive
        baseline_jobs=rest.capture('jobs')
        require(not any(j['status']=='RUNNING' for j in baseline_jobs),'Other Spark work active before episode')
        log.emit('full_drain_engine_baseline',job_ids=sorted(j['jobId'] for j in baseline_jobs))
        for _ in range(3):connections.append(hive.Connection(**{k:cfg['engine'][k] for k in ('host','port','username')}))
        class CutoffCursor:
            def __init__(self,cursor):self.cursor=cursor
            def execute(self,sql):
                guard()  # Check again at every actual cursor call, including metadata.
                return self.cursor.execute(sql)
            def __getattr__(self,name):return getattr(self.cursor,name)
        meta,query_cursor,action_cursor=[CutoffCursor(c.cursor()) for c in connections]
        def call(cursor,sql,role='metadata',**kwargs):
            guard();return rec.execute(cursor,sql,role=role,**kwargs)
        require(call(meta,'SELECT version()')['rows'][0][0].split()[0]==cfg['engine']['expected_version'],'Engine version differs')
        env=rest.capture('environment');actual_properties=dict(env['sparkProperties'])
        require(all(actual_properties.get(k)==v for k,v in cfg['expected_spark_properties'].items()),
                'Registered engine parallelism/memory/properties differ')
        table=cfg['destination_table']
        require(not any(r[1]==table.split('.')[-1] for r in call(meta,'SHOW TABLES IN local.experiment')['rows']),'Occupied table; no reuse')
        require(call(meta,f"SELECT snapshot_id FROM {source['table']}.history ORDER BY made_current_at DESC LIMIT 1")['rows']==[[source['snapshot_id']]],'Source snapshot changed')
        call(meta,f"CREATE TABLE {table} USING iceberg AS SELECT /*+ REPARTITION({cfg['initial_file_count']}) */ * FROM {source['table']} VERSION AS OF {source['snapshot_id']}")
        def inventory(cursor):
            snap=call(cursor,f'SELECT snapshot_id FROM {table}.history ORDER BY made_current_at DESC LIMIT 1')
            files=call(cursor,f'SELECT file_path, record_count, file_size_in_bytes FROM {table}.files')
            require(len(snap['rows'])==1 and files['rows'],'Missing snapshot/file state')
            return dict(table=table,snapshot_id=snap['rows'][0][0],snapshot_measurement_id=snap['measurement_id'],
                file_inventory_measurement_id=files['measurement_id'],inventory_end_ns=files['fetch_end']['monotonic_ns'],
                layout_signature=sorted([r[1:] for r in files['rows']]),
                file_state=dict(file_count=len(files['rows']),record_count=sum(r[1] for r in files['rows']),total_bytes=sum(r[2] for r in files['rows'])))
        def multiset(state):
            snapshot=state['snapshot_id']
            sql=f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {table} VERSION AS OF {snapshot}) UNION ALL (SELECT * FROM {table} VERSION AS OF {snapshot} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences"
            result=call(meta,sql);require(result['rows']==[[0]],'Full logical multiset differs')
            log.emit('full_drain_multiset',snapshot_id=snapshot,measurement_id=result['measurement_id'])
        state=inventory(meta);initial=dict(state)
        require(state['file_state']['record_count']==source['record_count'] and state['file_state']['file_count']==cfg['initial_file_count'],'Initial layout/population differs')
        multiset(initial);log.emit('full_drain_initial_state',**initial)
        sampler.start();time.sleep(cfg['telemetry']['warmup_seconds']);guard()
        lo=time.monotonic_ns();hi=lo+cfg['horizon_ns'];cutoff=lo+int((deadline-datetime.now(timezone.utc)).total_seconds()*1e9)
        require(cutoff-hi>=cfg['minimum_drain_admission_ns'] and lo+cfg['latest_action_offset_ns']<cutoff,'Insufficient registered drain/action budget')
        log.emit('full_drain_clock',start_monotonic_ns=lo,arrival_end_monotonic_ns=hi,dispatch_end_monotonic_ns=cutoff)
        ledger=FullDrainLedger(log,mapped,lo,hi,cutoff);pending=queue.Queue();offered_done=threading.Event();action_done=threading.Event();state_lock=threading.Lock()
        identities={r['source_query_id']:uuid.uuid4().hex for r in mapped}
        def failure(name,exc):
            errors.append(exc);log.emit('full_drain_thread_failed',thread=name,error=str(exc))
        def offer():
            try:
                for row in mapped:
                    time.sleep(max(0,(lo+int(row['offset_ns'])-time.monotonic_ns())/1e9))
                    mid=identities[row['source_query_id']];ledger.transition(row,'offered',mid);ledger.transition(row,'queued',mid);pending.put(row)
            except Exception as exc:failure('offer',exc)
            finally:offered_done.set()
        def fresh(mid):
            require(sampler.wait_for_available_sample(deadline_ns=cutoff,
                max_age_seconds=cfg['three_model_capture']['admission_max_sample_age_seconds'],measurement_id=mid),'No fresh actual sample before cutoff')
        def windows():
            t=cfg['telemetry'];return [sampler.window(seconds=w,max_interval_seconds=t['max_interval_seconds'],max_age_seconds=t['max_age_seconds']) for w in t['window_seconds']]
        def action():
            nonlocal state
            try:
                if done.wait(max(0,(lo+cfg['action_offset_ns']-time.monotonic_ns())/1e9)):return
                require(not errors,'Earlier failure stops dependent rewrite')
                guard();log.emit('full_drain_action_due',registered_offset_ns=cfg['action_offset_ns'])
                refresh=call(action_cursor,f'REFRESH TABLE {table}');current=inventory(action_cursor);mid=uuid.uuid4().hex;fresh(mid)
                observed_windows=[]
                def prepare():
                    guard();require(time.monotonic_ns()<=lo+cfg['latest_action_offset_ns'],'Missed action start window')
                    require(time.monotonic_ns()-current['inventory_end_ns']<=cfg['metadata_max_age_seconds']*1e9,'Action metadata stale')
                    observed_windows[:]=windows()
                    log.emit('maintenance_decision_observation',measurement_id=mid,query_id=None,role='maintenance',
                        windows=observed_windows,decision_refresh_measurement_id=refresh['measurement_id'],**current)
                sql=f"CALL local.system.rewrite_data_files(table => '{table.removeprefix('local.')}', strategy => 'binpack', options => map('partial-progress.enabled','false'))"
                guard()
                result=execute_action(rec,action_cursor,sql,mid,prepare,
                    min(cutoff,lo+cfg['latest_action_offset_ns']),
                    lambda:[w['last_available_sample_end_monotonic_ns'] for w in observed_windows],
                    cfg['three_model_capture']['max_feature_age_ns'],current['inventory_end_ns'],
                    int(cfg['metadata_max_age_seconds']*1e9))
                require(result is not None and result.get('submitted') is not False,'Rewrite not submitted; obligation unmet')
                require(len(result['rows'])==1 and len(result['rows'][0])>=3
                        and all(type(v) is int and v>0 for v in result['rows'][0][:3]),
                        'Rewrite must actually rewrite files, add files and rewrite bytes')
                actions.append(result);call(action_cursor,f'REFRESH TABLE {table}');updated=inventory(action_cursor)
                with state_lock:state=updated
                log.emit('full_drain_layout_published',**updated)
            except Exception as exc:failure('maintenance',exc)
            finally:action_done.set()
        archive=TerminalArchive(rest,log,out/'events.jsonl',table)
        direct=DirectTaskRetention(out/'direct_archive',base_url=cfg['spark_rest_url'],app_id=cfg['spark_app_id'],
            page_length=cfg['direct_archive']['page_length'],max_pages=cfg['direct_archive']['max_pages'],
            max_requests_per_checkpoint=cfg['direct_archive']['max_requests_per_checkpoint'],
            timeout_seconds=cfg['direct_archive']['timeout_seconds'],latest_request_utc=cfg['no_new_operation_after_utc'])
        def capture(terminal=False):
            archive.capture(terminal=terminal)
            requested=[r for r in archive.requests.values() if r['role']=='trace_query']
            completed=[r for r in archive.completed.values() if r['role']=='trace_query']
            if completed:
                direct.capture(requested,completed,terminal=terminal)
            elif terminal:
                raise ValueError('No completed query population at terminal capture')
        def observe():
            try:
                while not done.wait(cfg['archive_interval_seconds']):
                    capture()
            except Exception as exc:failure('archive',exc)
        for fn in (offer,action,observe):
            t=threading.Thread(target=fn);threads.append(t);t.start()
        query_snapshot=None
        while not (offered_done.is_set() and pending.empty()):
            guard()
            if errors:raise errors[0]
            try:row=pending.get(timeout=cfg['idle_poll_seconds'])
            except queue.Empty:continue
            mid=identities[row['source_query_id']];qid=int(row['query_id']);fresh(mid)
            with state_lock:current=dict(state)
            if query_snapshot!=current['snapshot_id']:
                call(query_cursor,f'REFRESH TABLE {table}',role='query_session_state_refresh');query_snapshot=current['snapshot_id'];fresh(mid)
            def prepare():
                guard();log.emit('query_observation',measurement_id=mid,query_id=qid,role='trace_query',windows=windows(),**current)
                ledger.transition(row,'dispatched',mid)
                return True
            try:
                probe=call(query_cursor,pin_query(cfg,table,qid,current['snapshot_id']),role='trace_query',query_id=qid,
                           measurement_id=mid,prepare_submission=prepare,latest_start_ns=cutoff)
                require(probe is not None and probe.get('submitted') is not False,'No submitted query; preserve incomplete cohort')
                require(canonical_result(probe['rows'],qid,cfg)==expected[str(qid)],'Typed query result differs')
                ledger.transition(row,'completed',mid);probes.append(probe)
            except Exception:
                if ledger.active==row['source_query_id']:ledger.transition(row,'failed',mid)
                raise
        # Foreground drain does not terminate a late required maintenance arm.
        while not action_done.wait(cfg['idle_poll_seconds']):
            guard()
            if errors:raise errors[0]
        if errors:raise errors[0]
        require(len(actions)==1,'Required rewrite did not complete')
        log.emit('full_drain_work_complete',offered=len(mapped),completed=len(probes),completed_rewrites=len(actions))
        done.set()
        for t in threads:t.join()
        if errors:raise errors[0]
        capture(terminal=True)
        sampler.stop();log.emit('telemetry_acquisition_phase_complete',contract=cfg['telemetry_lifecycle_contract'])
        final=inventory(meta);log.emit('full_drain_final_state',**final);multiset(final);ledger.census('full_drain_final_census')
        result=reconstruct(out);result.update(status='collected_full_drain_pending_independent_engine_audit',
            code_revision=expected_head,physical_episode_accepted=False,training_eligible=False,
            limitations=['No acceptance before independent raw engineering gates complete.',
                         'Validation SQL follows observer shutdown and is outside the measured workload/maintenance boundary; its resource cost is unmeasured.'])
        verify_inputs(cfg);require(sha(protocol)==sha(out/'config.json'),'Protocol changed during episode')
        write_new(out/'result.json',result)
        # Separate immutable acceptance sidecar: collection is not silently
        # upgraded, and a failed independent audit keeps its original result.
        audit_files=[p for p in (out/'direct_archive').rglob('*') if p.is_file()]
        audit_files += [out/'events.jsonl',out/'result.json']
        audit_cfg=dict(schema='saved_raw_full_drain_trace_work_audit_v1',
            call_population='all_trace_queries_in_full_drain_ledger',episode=str(out.relative_to(ROOT)),
            expected_completed_calls=cfg['arrival_count'],application_url=cfg['spark_rest_url'].rstrip('/')+
                '/api/v1/applications/'+cfg['spark_app_id'],
            inputs={str(p.relative_to(ROOT)):sha(p) for p in audit_files},
            SQL_allowed=False,REST_allowed=False,physical_acceptance_allowed=False)
        write_new(out/'engine_audit_inputs.json',audit_cfg)
        from .audit import audit_saved
        proofs=audit_saved(out)
        write_new(out/'acceptance.json',dict(status='passed_full_drain_engineering_checks_only',
            completed_utc=now(),
            result_sha256=sha(out/'result.json'),**{k:v for k,v in proofs.items() if k!='response_accounting'},
            engine_audit_inputs_sha256=sha(out/'engine_audit_inputs.json'),code_revision=expected_head,
            physical_episode_accepted=False,training_eligible=False,calibration_accepted=False,
            publication_or_policy_benefit_claimed=False))
        safe=True
        print(json.dumps({k:v for k,v in result.items() if k!='queries'}),flush=True)
    except Exception as exc:
        done.set()
        if log is not None:
            try:log.emit('full_drain_failed',error=str(exc),traceback=traceback.format_exc())
            except Exception:pass
        for t in threads:t.join()  # No active RPC is interrupted or cancelled.
        debt={} if ledger is None else dict(ledger.states)
        write_new(out/'failure.json',dict(status='failed_preserved_incomplete_or_unaudited',error=str(exc),
            traceback=traceback.format_exc(),completed_queries=len(probes),completed_rewrites=len(actions),
            planned_queries=cfg['arrival_count'],actually_offered_queries=len(debt),
            not_yet_offered_queries=cfg['arrival_count']-len(debt),
            unfinished_queries=cfg['arrival_count']-len(probes),required_rewrites=1,
            observed_queue_states=debt,physical_episode_accepted=False))
        raise
    finally:
        done.set()
        for t in threads:t.join()
        if sampler is not None and hasattr(sampler,'thread'):
            try:sampler.stop()
            except Exception:
                if safe:raise
        if log is not None:log.close()
        for stream in locks:stream.close()
        if safe:
            for connection in connections:connection.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--expected-head',required=True)
    args=p.parse_args();run(args.protocol,args.expected_head)
