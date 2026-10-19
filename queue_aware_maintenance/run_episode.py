#!/usr/bin/env python3
"""Real Spark/Iceberg fixed-arrival cohort with full queue drain and causal policy."""
import argparse,csv,fcntl,json,queue,re,shutil,subprocess,threading,time,uuid,traceback
from pathlib import Path
from datetime import datetime,timezone,timedelta
from common import checked,sha,write_json,require,now,utc
from physical_measurements import EventLog,StatementRecorder,SparkEvidence,TelemetrySampler,stamp
from statement_timing import completed_statements
from run_correctness_pilot import query_templates,canonical
from ledger import CohortLedger
from costs import EmpiricalCosts
from forecast import SeasonalArrivalForecast
from policy import MaintenancePolicy
from engine_evidence import EngineArchive

class FreshSampleRequired(Exception):pass

def run(protocol,revision):
 cfg=json.loads(Path(protocol).read_text());root=Path(__file__).resolve().parent;repo=root.parent
 require(cfg['schema_version']=='queue_aware_full_drain_episode_v1','Unknown episode protocol');require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==revision,'Frozen runtime HEAD differs')
 require(subprocess.run(['git','diff','--exit-code','HEAD','--','queue_aware_maintenance'],cwd=repo,capture_output=True).returncode==0,'Dirty experiment source')
 deadline=utc(cfg['no_new_operation_after_utc'])
 def guard():require(datetime.now(timezone.utc)<deadline,'Operational cutoff reached; retain censoring, no new SQL')
 guard();out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False);code=out/'code';shutil.copytree(root,code,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copyfile(protocol,out/'config.json')
 lock=(repo/'results'/'.physical_correctness.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 mapping=checked(cfg['mapping']);source_path=checked(cfg['preparation_result']);source=json.loads(source_path.read_text());require(source['status']=='accepted_correctness_source','Invalid source receipt');arrivals=list(csv.DictReader(mapping.open()));require(len(arrivals)==cfg['arrival_count'] and len({r['source_query_id'] for r in arrivals})==len(arrivals),'Mapping cohort identity mismatch');shutil.copyfile(mapping,out/'mapped_arrivals.csv');shutil.copyfile(source_path,out/'preparation_result.json')
 expected={}
 for i,spec in enumerate(cfg['expected_query_ledgers']):
  path=checked(spec);shutil.copyfile(path,out/f'expected_ledger_{i}.jsonl');references=[r for r in completed_statements([path]).values() if r['role']=='control_before'];require(len(references)==1,'Ambiguous expected result');r=references[0];expected[int(r['query_id'])]=canonical(r['rows'])
 require(set(expected)==set(cfg['query_ids']),'Incomplete SQL references')
 costs=EmpiricalCosts.load(checked(cfg['model']));forecast=SeasonalArrivalForecast(cfg['arrivals'],origin=cfg['observation_origin_utc'],history_days=cfg['forecast_history_days'],bin_seconds=cfg['decision_interval_seconds'],freeze_source_time=cfg['forecast_history_freeze_utc']);policy=MaintenancePolicy(cfg['policy'],costs,forecast,cfg['source_start_utc'],cfg['source_end_utc'],cfg['query_ids'],cfg['decision_interval_seconds'])
 table=cfg['destination_table'];require(re.fullmatch(r'local\.experiment\.queueaware_[a-z0-9_]+',table),'Fresh isolated table identity required')
 log=EventLog(out/'events.jsonl',cfg['experiment_id']);rec=StatementRecorder(log);rest=SparkEvidence(cfg['spark_rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log);sampler=TelemetrySampler(log,cfg['telemetry']['interval_seconds'],asynchronous_persistence=True);connections=[];threads=[];errors=[];probes=[];actions=[];known_markers=[];state_lock=threading.RLock();action_started=False;safe=False;ledger=None;lo=None
 code_hashes={str(p.relative_to(code)):sha(p) for p in code.rglob('*') if p.is_file()};log.emit('queue_aware_protocol',configuration=cfg,revision=revision,code_sha256=code_hashes)
 def call(cursor,sql,role='metadata',**kwargs):
  guard();mid=kwargs.pop('measurement_id',uuid.uuid4().hex);known_markers.append('capstone_event_'+mid);return rec.execute(cursor,sql,role=role,measurement_id=mid,**kwargs)
 from pyhive import hive
 try:
  require(not rest._capture('jobs?status=running'),'Competing active Spark job')
  for _ in range(cfg['connection_count']):connections.append(hive.Connection(**{k:cfg['engine'][k] for k in ('host','port','username')}))
  meta,query_cursor,action_cursor=[c.cursor() for c in connections];require(call(meta,'SELECT version()')['rows'][0][0].split()[0]==cfg['engine']['expected_version'],'Engine version changed');environment=rest.capture('environment');require(dict(environment['sparkProperties']).get('spark.master')==cfg['expected_spark_master'],'Engine resources changed')
  archive=EngineArchive(rest,log,table)
  require(not any(r[1]==table.split('.')[-1] for r in call(meta,'SHOW TABLES IN local.experiment')['rows']),'Never reuse occupied table')
  require(call(meta,f"SELECT snapshot_id FROM {source['table']}.history ORDER BY made_current_at DESC LIMIT 1")['rows'][0][0]==source['snapshot_id'],'Source current snapshot changed')
  call(meta,f"CREATE TABLE {table} USING iceberg AS SELECT /*+ REPARTITION({cfg['initial_file_count']}) */ * FROM {source['table']} VERSION AS OF {source['snapshot_id']}")
  def inventory(cursor):
   snap=call(cursor,f'SELECT snapshot_id FROM {table}.history ORDER BY made_current_at DESC LIMIT 1');files=call(cursor,f'SELECT file_path, record_count, file_size_in_bytes FROM {table}.files');return {'table':table,'snapshot_id':snap['rows'][0][0],'snapshot_measurement_id':snap['measurement_id'],'file_inventory_measurement_id':files['measurement_id'],'inventory_available_monotonic_ns':files['fetch_end']['monotonic_ns'],'layout_signature':sorted([[r[1],r[2]] for r in files['rows']]),'file_state':{'file_count':len(files['rows']),'record_count':sum(r[1] for r in files['rows']),'total_bytes':sum(r[2] for r in files['rows'])}}
  state=inventory(meta);initial_state=state;require(state['file_state']['file_count']==cfg['initial_file_count'] and state['file_state']['record_count']==source['record_count'],'Initial table state differs');log.emit('cohort_initial_state',**state)
  def multiset(cursor,check_state):
   snapshot=check_state['snapshot_id'];r=call(cursor,f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {table} VERSION AS OF {snapshot}) UNION ALL (SELECT * FROM {table} VERSION AS OF {snapshot} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences");require(r['rows']==[[0]],'Logical multiset changed');log.emit('cohort_multiset_validation',snapshot_id=snapshot,measurement_id=r['measurement_id'])
  multiset(meta,initial_state);sampler.start();time.sleep(cfg['telemetry']['warmup_seconds']);guard();lo=time.monotonic_ns();hi=lo+int(cfg['horizon_seconds']*1e9);cutoff_ns=lo+int((deadline-datetime.now(timezone.utc)).total_seconds()*1e9);log.emit('cohort_clock',start_monotonic_ns=lo,arrival_end_monotonic_ns=hi,operational_end_monotonic_ns=cutoff_ns,source_start_utc=cfg['source_start_utc'],source_end_utc=cfg['source_end_utc']);ledger=CohortLedger(log,arrivals,lo);pending=queue.Queue();offering_done=threading.Event();identities={r['source_query_id']:uuid.uuid4().hex for r in arrivals}
  def offer():
   try:
    for row in arrivals:
     due=lo+int(row['offset_ns']);time.sleep(max(0,(due-time.monotonic_ns())/1e9));mid=identities[row['source_query_id']];ledger.transition(row,'offered',mid);ledger.transition(row,'queued',mid);pending.put(row)
   except Exception as e:errors.append(e);log.emit('cohort_thread_failed',thread='offer',error=str(e))
   finally:offering_done.set()
  def boundary():
   time.sleep(max(0,(hi-time.monotonic_ns())/1e9));ledger.census('cohort_arrival_boundary')
  for fn in [offer,boundary]:
   t=threading.Thread(target=fn);threads.append(t);t.start()
  def windows():return [sampler.window(seconds=w,max_interval_seconds=cfg['telemetry']['max_interval_seconds'],max_age_seconds=cfg['telemetry']['max_age_seconds']) for w in cfg['telemetry']['window_seconds']]
  def fresh():
   if not sampler.wait_for_available_sample(deadline_ns=cutoff_ns,max_age_seconds=cfg['telemetry']['interval_seconds'],measurement_id=uuid.uuid4().hex):guard()
  def action():
   nonlocal state
   try:
    refreshed=call(action_cursor,f'REFRESH TABLE {table}');current=inventory(action_cursor);mid=uuid.uuid4().hex;fresh()
    def prepare():
     guard();last=sampler.available_sample_end_ns()
     if last is None or (time.monotonic_ns()-last)/1e9>cfg['telemetry']['interval_seconds']:raise FreshSampleRequired()
     require((time.monotonic_ns()-current['inventory_available_monotonic_ns'])/1e9<=cfg['metadata_max_age_seconds'],'Action metadata stale; preserve failed attempt');log.emit('maintenance_decision_observation',measurement_id=mid,query_id=None,role='maintenance',windows=windows(),decision_refresh_measurement_id=refreshed['measurement_id'],**current)
    while True:
     try:
      result=call(action_cursor,f"CALL local.system.rewrite_data_files(table => '{table.removeprefix('local.')}', strategy => 'binpack', options => map('partial-progress.enabled','false'))",role='maintenance',measurement_id=mid,prepare_submission=prepare);break
     except FreshSampleRequired:
      log.emit('cohort_preparation_deferred',measurement_id=mid,role='maintenance',reason='fresh_sample_required_before_any_SQL_intent');fresh();refreshed=call(action_cursor,f'REFRESH TABLE {table}');current=inventory(action_cursor)
    actions.append(result);call(action_cursor,f'REFRESH TABLE {table}');updated=inventory(action_cursor)
    with state_lock:state=updated
    log.emit('cohort_maintenance_completed',measurement_id=mid,**updated)
   except Exception as e:errors.append(e);log.emit('cohort_thread_failed',thread='maintenance',error=str(e))
  next_decision=0.0;next_archive=cfg['archive_interval_seconds'];query_snapshot=None
  while not(offering_done.is_set() and pending.empty()):
   guard()
   if errors:raise errors[0]
   elapsed=(time.monotonic_ns()-lo)/1e9
   if elapsed>=next_decision and not action_started:
    with state_lock:current=dict(state)
    
    with ledger.lock:queued_observation=ledger.queued();last_offered=ledger.last_offered_query_id;began=stamp()
    decision_elapsed=(began['monotonic_ns']-lo)/1e9;decision=policy.decide(elapsed_seconds=decision_elapsed,queued=queued_observation,last_offered_query_id=last_offered,files=current['file_state']['file_count']);log.emit('controller_decision',decision_started=began,decision_finished=stamp(),decision=decision,model_sha256=cfg['model']['sha256'],current_snapshot_id=current['snapshot_id']);next_decision=(int(elapsed//cfg['decision_interval_seconds'])+1)*cfg['decision_interval_seconds']
    if decision['execute_now']:
     require(elapsed<cfg['horizon_seconds'],'No maintenance start after registered arrival horizon');action_started=True;t=threading.Thread(target=action);threads.append(t);t.start()
   if elapsed>=next_archive:archive.checkpoint(list(probes),list(actions),list(known_markers));next_archive=elapsed+cfg['archive_interval_seconds']
   try:row=pending.get(timeout=cfg['idle_poll_seconds'])
   except queue.Empty:continue
   mid=identities[row['source_query_id']];qid=int(row['query_id'])
   with state_lock:current=dict(state)
   if query_snapshot!=current['snapshot_id']:call(query_cursor,f'REFRESH TABLE {table}',role='query_session_state_refresh');query_snapshot=current['snapshot_id']
   while True:
    fresh()
    def prepare():
     guard();last=sampler.available_sample_end_ns()
     if last is None or (time.monotonic_ns()-last)/1e9>cfg['telemetry']['interval_seconds']:raise FreshSampleRequired()
     log.emit('query_observation',measurement_id=mid,query_id=qid,role='trace_query',windows=windows(),**current);ledger.transition(row,'dispatched',mid)
    try:
     sql=query_templates(table)[qid].replace(f'FROM {table}',f"FROM {table} VERSION AS OF {current['snapshot_id']}");probe=call(query_cursor,sql,role='trace_query',query_id=qid,measurement_id=mid,prepare_submission=prepare,latest_start_ns=cutoff_ns);break
    except FreshSampleRequired:log.emit('cohort_preparation_deferred',measurement_id=mid,source_query_id=row['source_query_id'],reason='fresh_sample_required_before_any_SQL_intent')
   require(probe is not None and probe.get('submitted') is not False,'Administrative cutoff before actual SQL; cohort censored');require(canonical(probe['rows'])==expected[qid],'Physical benchmark result differs');ledger.transition(row,'completed',mid);probes.append(probe)
  for t in threads:t.join()
  if errors:raise errors[0]
  final=inventory(meta);log.emit('cohort_final_state',**final);multiset(meta,final);archive.checkpoint(probes,actions,known_markers,final=True);ledger.census('cohort_final_census');sampler.stop();log.emit('cohort_physical_finished',offered=len(arrivals),completed=len(probes),maintenance_count=len(actions),all_queries_drained=True);log.close();safe=True
  from audit_episode import audit
  result=audit(out);result['revision']=revision;write_json(out/'result.json',result);print(json.dumps({k:v for k,v in result.items() if k!='queries'}),flush=True)
 except Exception as e:
  try:log.emit('cohort_failed_preserved',error=str(e),traceback=traceback.format_exc())
  except Exception:pass
  for t in threads:t.join()
  write_json(out/'failure.json',{'status':'failed_preserved_not_complete_cohort','error':str(e),'traceback':traceback.format_exc(),'offered_source_rows':len(arrivals),'completed':len(probes),'utc':now()});raise
 finally:
  if hasattr(sampler,'thread'):
   try:sampler.stop()
   except Exception:pass
  if not log.stream.closed:log.close()
  lock.close()
  if safe:
   for c in connections:c.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--expected-revision',required=True);a=p.parse_args();run(a.protocol,a.expected_revision)
