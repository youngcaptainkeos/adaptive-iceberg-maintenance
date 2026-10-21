#!/usr/bin/env python3
"""Actual matched observer-submission probe; never eligible for cost/policy fitting."""
import argparse,json,time,uuid,fcntl,shutil,statistics,traceback,re
from pathlib import Path
from datetime import datetime,timezone
from common import checked,sha,require,write_json,now,utc,notify
from physical_measurements import EventLog,StatementRecorder,SparkEvidence,stamp
from sampler_factory import build_sampler
from query_observation_binding import verify_observations
from statement_timing import completed_statements
from run_correctness_pilot import canonical,query_templates
from engine_evidence import EngineArchive

class FreshSampleRequired(Exception):pass

def actual_call_ns(probe):
 # StatementRecorder returns clocks; elapsed_ns exists only in its raw event.
 start=probe['client_execute_start']['monotonic_ns'];end=probe['fetch_end']['monotonic_ns']
 require(isinstance(start,int) and isinstance(end,int) and end>start,'Invalid actual call clocks')
 return end-start

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False);report={'status':'running','started_utc':now(),'protocol_sha256':sha(protocol),'code_sha256':sha(__file__),'eligible_for_cost_training':False,'eligible_for_policy_benefit_comparison':False};locks=[];connections=[];sampler=None;log=None
 try:
  for n,h in cfg['code_sha256'].items():require(sha(Path(__file__).parent/n)==h,'Changed frozen probe source '+n)
  prior=json.loads(checked(cfg['continuation_result']).read_text());require(prior['status']=='blocked_no_resolvable_development_timing_headroom','Unexpected diagnostic prerequisite')
  deadline=utc(cfg['no_new_SQL_after_utc']);require(datetime.now(timezone.utc)<deadline,'Probe start cutoff reached')
  def guard():require(datetime.now(timezone.utc)<deadline,'No new SQL after probe cutoff; preserve partial results')
  repo=Path(cfg['canonical_repository'])
  for name in ('.physical_correctness.lock','.queue_aware_study.lock'):
   f=(repo/'results'/name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
  source=json.loads(checked(cfg['preparation_result']).read_text());require(source['status']=='accepted_correctness_source','Source not accepted')
  expected={}
  for i,spec in enumerate(cfg['expected_query_ledgers']):
   p=checked(spec);shutil.copyfile(p,out/f'expected_ledger_{i}.jsonl');rr=[r for r in completed_statements([p]).values() if r['role']=='control_before'];require(len(rr)==1,'Ambiguous expected query');expected[int(rr[0]['query_id'])]=canonical(rr[0]['rows'])
  require(set(expected)==set(cfg['query_ids']),'Missing query references')
  log=EventLog(out/'events.jsonl',cfg['experiment_id']);rec=StatementRecorder(log);log.emit('observer_probe_registration',configuration=cfg,source_sha256=sha(__file__),meaning='Diagnostic matched real SQL, not a trace replay or relaxed policy acceptance.')
  rest=SparkEvidence(cfg['spark_rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log);require(not rest._capture('jobs?status=running'),'Competing actual Spark job')
  from pyhive import hive
  connections.append(hive.Connection(**{k:cfg['engine'][k] for k in ('host','port','username')}));cursor=connections[0].cursor();markers=[]
  def call(sql,role='probe_metadata',**kwargs):
   guard();mid=kwargs.pop('measurement_id',uuid.uuid4().hex);markers.append('capstone_event_'+mid);return rec.execute(cursor,sql,role=role,measurement_id=mid,**kwargs)
  require(call('SELECT version()')['rows'][0][0].split()[0]==cfg['engine']['expected_version'],'Engine version changed');env=rest.capture('environment');require(dict(env['sparkProperties'])['spark.master']==cfg['expected_spark_master'],'Resources changed')
  table=cfg['destination_table'];require(re.fullmatch(r'local\.experiment\.queueaware_[a-z0-9_]+',table),'Unregistered isolated table');require(not any(r[1]==table.split('.')[-1] for r in call('SHOW TABLES IN local.experiment')['rows']),'Occupied table; never reuse')
  require(call(f"SELECT snapshot_id FROM {source['table']}.history ORDER BY made_current_at DESC LIMIT 1")['rows'][0][0]==source['snapshot_id'],'Immutable source current snapshot changed')
  archive=EngineArchive(rest,log,table);call(f"CREATE TABLE {table} USING iceberg AS SELECT /*+ REPARTITION({cfg['initial_file_count']}) */ * FROM {source['table']} VERSION AS OF {source['snapshot_id']}")
  snap=call(f'SELECT snapshot_id FROM {table}.history ORDER BY made_current_at DESC LIMIT 1');files=call(f'SELECT file_path, record_count, file_size_in_bytes FROM {table}.files');state={'table':table,'snapshot_id':snap['rows'][0][0],'snapshot_measurement_id':snap['measurement_id'],'file_inventory_measurement_id':files['measurement_id'],'file_state':{'file_count':len(files['rows']),'record_count':sum(r[1] for r in files['rows']),'total_bytes':sum(r[2] for r in files['rows'])}}
  require(state['file_state']['file_count']==cfg['initial_file_count'] and state['file_state']['record_count']==source['record_count'],'Initial physical source differs')
  def equality():
   r=call(f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {table} VERSION AS OF {state['snapshot_id']}) UNION ALL (SELECT * FROM {table} VERSION AS OF {state['snapshot_id']} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences")
   require(len(r['rows'])==1 and len(r['rows'][0])==1 and r['rows'][0][0]==0,'Logical source differs');return r['measurement_id']
  equality();sampler=build_sampler(cfg,log);sampler.start();notify('Capstone observer probe started','Fresh isolated table; real ABBA submission-path probe. Background sampler remains on in both modes; no model fitting or policy trial.',out/'start_notification.json',cfg['notification_configuration']);time.sleep(cfg['telemetry']['warmup_seconds']);guard()
  probes=[];observations=[];results=[];cutoff_ns=time.monotonic_ns()+int((deadline-datetime.now(timezone.utc)).total_seconds()*1e9)
  # Four real template warmup calls are explicitly excluded from comparisons,
  # retain their correctness and actual task proof alongside measured calls.
  phases=[('warmup',1)]+[(m,cfg['cycles_per_phase']) for m in cfg['phase_order']]
  for phase,(mode,cycles) in enumerate(phases):
   phase_start=stamp()
   for cycle in range(cycles):
    for qid in cfg['query_ids']:
     guard();mid=uuid.uuid4().hex;began=stamp();role='observer_probe_'+mode
     def prepare():
      if mode!='full':return
      last=sampler.available_sample_end_ns()
      if last is None or (time.monotonic_ns()-last)/1e9>cfg['telemetry']['interval_seconds']:raise FreshSampleRequired()
      windows=[sampler.window(seconds=w,max_interval_seconds=cfg['telemetry']['max_interval_seconds'],max_age_seconds=cfg['telemetry']['max_age_seconds']) for w in cfg['telemetry']['window_seconds']]
      log.emit('query_observation',measurement_id=mid,query_id=qid,role=role,windows=windows,**state)
     while True:
      if mode=='full':require(sampler.wait_for_available_sample(deadline_ns=cutoff_ns,max_age_seconds=cfg['telemetry']['interval_seconds'],measurement_id=mid),'No fresh actual telemetry before deadline')
      sql=query_templates(table)[qid].replace(f'FROM {table}',f"FROM {table} VERSION AS OF {state['snapshot_id']}")
      try:probe=call(sql,role=role,query_id=qid,measurement_id=mid,prepare_submission=prepare if mode=='full' else None);break
      except FreshSampleRequired:log.emit('observer_probe_preparation_deferred',measurement_id=mid,reason='fresh_durable_sample_required_before_SQL_intent')
     require(canonical(probe['rows'])==expected[qid],'Actual query result differs');probes.append(probe);ended=stamp();row={'measurement_id':mid,'phase':phase,'mode':mode,'cycle':cycle,'query_id':qid,'preparation_to_result_ns':probe['fetch_end']['monotonic_ns']-began['monotonic_ns'],'actual_call_ns':actual_call_ns(probe),'post_result_correctness_check_ns':ended['monotonic_ns']-probe['fetch_end']['monotonic_ns']};results.append(row);log.emit('observer_probe_query_complete',**row)
   archive.checkpoint(probes,[],markers);log.emit('observer_probe_phase_complete',phase=phase,mode=mode,started=phase_start,ended=stamp());print(f'phase {phase} {mode} complete',flush=True)
  require(call(f'SELECT snapshot_id FROM {table}.history ORDER BY made_current_at DESC LIMIT 1')['rows'][0][0]==state['snapshot_id'],'Table snapshot changed');equality();archive.checkpoint(probes,[],markers,final=True);sampler.stop();sampler=None;log.close();log=None
  events=[json.loads(line) for line in (out/'events.jsonl').open()];checks=verify_observations(events,cfg);require(len(checks)==sum(r['mode']=='full' for r in results),'Missing strict observation proof')
  require(len(results)==len(cfg['query_ids'])*(1+len(cfg['phase_order'])*cfg['cycles_per_phase']),'Incomplete registered probe')
  summaries=[]
  for qid in cfg['query_ids']:
   row={'query_id':qid}
   for mode in ('full','minimal'):
    values=[r for r in results if r['mode']==mode and r['query_id']==qid];row[mode]={'calls':len(values),'median_preparation_to_result_seconds':statistics.median(r['preparation_to_result_ns']/1e9 for r in values),'median_actual_call_seconds':statistics.median(r['actual_call_ns']/1e9 for r in values)}
   row['descriptive_full_minus_minimal_preparation_to_result_seconds']=row['full']['median_preparation_to_result_seconds']-row['minimal']['median_preparation_to_result_seconds'];summaries.append(row)
  write_json(out/'queries.json',results);report.update(status='passed_actual_matched_submission_path_probe',queries=len(results),strict_full_observations=len(checks),table=table,snapshot_id=state['snapshot_id'],events_sha256=sha(out/'events.jsonl'),summaries=summaries,limitations=['Minimal mode retains durable StatementRecorder, snapshot pinning, exact results, task ownership and shared background sampler. It omits strict per-submission telemetry wait/window preparation, not all observation cost.','Fixed ABBA ordering and query warmup mitigate but do not eliminate cache/time drift. Descriptive engineering probe, no independent-block confidence claim.','No original arrival trace, queue-benefit outcome, rewrite or counterfactual cost training label produced.','Existing full policy raw acceptance gates remain unchanged; minimal-mode calls are ineligible for those datasets.'])
  write_json(out/'result.json',dict(report,ended_utc=now()));notify('Capstone observer probe complete','Actual matched probe passed; '+str(len(results))+' real queries. See summaries; no calibrated policy-benefit claim. Laptop-independent run finished.',out/'terminal_notification.json',cfg['notification_configuration'])
 except Exception as e:
  report.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc());write_json(out/'failure_result.json',dict(report,ended_utc=now()));raise
 finally:
  if sampler is not None:sampler.stop()
  if log is not None:log.close()
  for c in connections:c.close()
  for f in locks:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
