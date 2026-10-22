#!/usr/bin/env python3
"""Detached evidence-first continuation. No SQL, fitting or survivor comparisons."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,csv,json,statistics,traceback,os,socket,sys,ast
from pathlib import Path
from datetime import timedelta
from queue_aware_maintenance.core.common import checked,sha,write_json,require,now,utc,notify
from queue_aware_maintenance.models.costs import EmpiricalCosts
from queue_aware_maintenance.models.forecast import SeasonalArrivalForecast
from queue_aware_maintenance.policies.controller_factory import build_policy
from queue_aware_maintenance.models.snapshot_simulator import choose


def interval_union(intervals):
 merged=[]
 for lo,hi in sorted(intervals):
  require(hi>=lo,'Reversed recorded interval')
  if merged and lo<=merged[-1][1]:merged[-1][1]=max(hi,merged[-1][1])
  else:merged.append([lo,hi])
 return merged

def intersection_ns(a,b):
 i=j=total=0
 while i<len(a) and j<len(b):
  total+=max(0,min(a[i][1],b[j][1])-max(a[i][0],b[j][0]))
  if a[i][1]<b[j][1]:i+=1
  else:j+=1
 return total

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'running','started_utc':now(),'pid':os.getpid(),'host':socket.gethostname(),'protocol_sha256':sha(protocol),'code_sha256':sha(__file__),'new_SQL_executed':False,'fitting_executed':False,'policy_benefit_or_novelty_accepted':False,'stages':[]}
 def save():
  p=out/'progress.tmp';p.write_text(json.dumps(report,indent=2)+'\n');p.replace(out/'progress.json')
 def announce(message,name):notify('Capstone evidence-first continuation',message,out/name,cfg['notification_configuration'])
 save()
 try:
  for source in PACKAGE_ROOT.rglob('*.py'):ast.parse(source.read_text())
  for name,h in cfg['code_sha256'].items():require(sha(source_file(name))==h,'Frozen continuation code differs '+name)
  previous=json.loads(checked(cfg['preserved_audit']).read_text());require(previous['status']=='passed_preserved_incomplete_cohort_raw_audit','Raw reconstruction prerequisite absent')
  root=checked(cfg['cohort_result']).parent;cohort=json.loads((root/'result.json').read_text());require((cohort['passed'],cohort['failed'],cohort['unattempted'])==(7,0,1),'Preserved original inventory changed')
  costs=EmpiricalCosts.load(checked(cfg['model']));rows=[];busy_gaps=[];real_decisions=[]
  announce('Started detached read-only overhead accounting, real-source ablation checks and timing-headroom gate. No new physical campaign until supported.','start_notification.json')
  for item in cohort['attempts']:
   d=root/'episodes'/item['experiment_id'];saved=json.loads((d/'result.json').read_text());require(sha(d/'result.json')==item['result_sha256'],'Changed episode result');ecfg=json.loads((d/'config.json').read_text());mapping=list(csv.DictReader((d/'mapped_arrivals.csv').open()));calls=[];waits=[];rest=[];clock=None;decisions=[];offered_records=[];before_ns=0
   require(sha(d/'events.jsonl')==saved['events_sha256'],'Changed raw ledger')
   with (d/'events.jsonl').open() as f:
    for line in f:
     if not any('"kind": "'+k+'"' in line for k in ('statement_completed','query_telemetry_availability_wait','spark_rest','cohort_clock','controller_decision','cohort_queue_transition')):continue
     r=json.loads(line);kind=r['kind']
     if kind=='statement_completed' and r['role']=='trace_query':calls.append(r);before_ns+=r['instrumentation_before_execute_ns']
     elif kind=='query_telemetry_availability_wait':waits.append((r['started']['monotonic_ns'],r['ended']['monotonic_ns']))
     elif kind=='spark_rest':rest.append((r['request_start']['monotonic_ns'],r['response_end']['monotonic_ns']))
     elif kind=='cohort_clock':clock=r['start_monotonic_ns']
     elif kind=='controller_decision':decisions.append(r)
     elif kind=='cohort_queue_transition' and r['state']=='offered':offered_records.append(r)
   require(len(calls)==len(mapping)==saved['completed'] and clock is not None,'Incomplete call accounting')
   gaps=[]
   for prev,nxt,source in zip(calls,calls[1:],mapping[1:]):
    lo=max(prev['fetch_end']['monotonic_ns'],clock+int(source['offset_ns']));hi=nxt['client_execute_start']['monotonic_ns'];require(hi>=lo,'Negative busy gap');gaps.append((lo,hi));busy_gaps.append((hi-lo)/1e9)
   merged=interval_union(gaps);gaps_ns=sum(b-a for a,b in merged);wait_overlap=intersection_ns(merged,interval_union(waits));rest_overlap=intersection_ns(merged,interval_union(rest));combined=intersection_ns(merged,interval_union(waits+rest))
   errors=[abs(q['service_ns']/1e9-costs.service(q['query_id'],saved['initial_file_state']['file_count'],False)) for q in saved['queries']] if item['policy']=='no_maintenance' else []
   rows.append({'experiment_id':item['experiment_id'],'policy':item['policy'],'queries':len(calls),'total_busy_intercall_gap_seconds':gaps_ns/1e9,'mean_busy_intercall_gap_seconds':gaps_ns/max(1,len(gaps))/1e9,'telemetry_wait_overlap_seconds':wait_overlap/1e9,'REST_request_overlap_seconds':rest_overlap/1e9,'union_recorded_wait_REST_overlap_seconds':combined/1e9,'unattributed_busy_gap_seconds':(gaps_ns-combined)/1e9,'durable_intent_to_call_seconds':before_ns/1e9,'response_wait_fraction':saved['sum_wait_before_call_ns']/saved['sum_response_ns'],'noaction_service_mean_absolute_model_error_seconds':statistics.mean(errors) if errors else None,'events_sha256':saved['events_sha256'],'limitations':['Intervals are wall-clock overlap accounting, not causal overhead.','Unattributed time includes logging/locking/scheduling/metadata/policy work; no invented component attribution.','Intent-to-call time overlaps busy gaps and must not be added again.']})
   if item['policy']=='queue_aware':real_decisions=[(r,ecfg,mapping,[o for o in offered_records if o['actual_transition']['monotonic_ns']<=r['decision_started']['monotonic_ns']]) for r in decisions]
   print(item['experiment_id']+' overhead accounting complete',flush=True)
  write_json(out/'overhead_accounting.json',rows);report['stages'].append('recorded_interval_overhead_accounting_complete');save()
  # New baselines are checked on actual prior queue observations, never dummy demand.
  ablations=[];forecasts={}
  for event,ecfg,mapping,offered in real_decisions:
   key=ecfg['forecast_history_freeze_utc']
   if key not in forecasts:forecasts[key]=SeasonalArrivalForecast(ecfg['arrivals'],origin=ecfg['observation_origin_utc'],history_days=ecfg['forecast_history_days'],bin_seconds=ecfg['decision_interval_seconds'],freeze_source_time=key)
   byid={r['source_query_id']:r for r in mapping};queued=[byid[i] for i in event['decision']['queued_source_ids']];elapsed=event['decision']['elapsed_seconds'];last=int(offered[-1]['source']['query_id']) if offered else None
   for name in ('queue_only','forecast_planner'):
    options=dict(ecfg,policy=name,ablation_contract='information_removal_v1',ablation_code_sha256=sha(source_file('ablation_policy.py')))
    p=build_policy(options,costs,forecasts[key]);decision=p.decide(elapsed_seconds=elapsed,queued=queued,last_offered_query_id=last,files=ecfg['initial_file_count'])
    require(decision['policy']==name and decision['queued_source_ids']==event['decision']['queued_source_ids'],'Ablation changes observed queue identity')
    if name=='queue_only':require('forecast' not in decision,'Queue-only accesses future forecast')
    else:require(utc(decision['forecast']['maximum_history_timestamp'])<utc(key),'Forecast comparator leakage')
    require(decision['chosen'] in decision['candidates'] and decision['chosen']['sum_response_seconds']==min(c['sum_response_seconds'] for c in decision['candidates']),'Ablation objective mismatch')
    ablations.append({'elapsed_seconds':elapsed,'decision':decision,'physical_execution':False,'meaning':'Real development-source observation; information ablation, not a reproduced named published system.'})
  require(ablations,'No real-source ablation observations');write_json(out/'ablation_checks.json',ablations);report['stages'].append('ablation_runtime_checks_on_real_observed_queues_complete');save()
  diagnostics=json.loads(checked(cfg['model_diagnostics']).read_text());headroom=[];noise=statistics.median(busy_gaps)
  for diagnostic in diagnostics:
   mapping=list(csv.DictReader(checked(next(w['mapping'] for w in json.loads(checked(cfg['workloads']).read_text()) if w['window_index']==diagnostic['window_index'])).open()))
   events=[{'source_query_id':r['source_query_id'],'query_id':int(r['query_id']),'arrival_seconds':int(r['offset_ns'])/1e9} for r in mapping]
   choices=choose(events,now=0,files=cfg['initial_file_count'],costs=costs,candidate_starts=range(0,cfg['horizon_seconds'],cfg['decision_interval_seconds']))
   require(choices==diagnostic['perfect_arrival_diagnostic_only'],'Saved development headroom differs from reconstructed model')
   immediate=next(c for c in choices['candidates'] if c['rewrite_start_seconds']==0);gain=immediate['sum_response_seconds']-choices['chosen']['sum_response_seconds'];per=gain/len(events)
   headroom.append({'window_index':diagnostic['window_index'],'queries':len(events),'best_model_start_seconds':choices['chosen']['rewrite_start_seconds'],'perfect_arrival_model_gain_vs_immediate_sum_seconds':gain,'gain_per_query_seconds':per,'registered_observability_screen_seconds_per_query':noise,'passes_screen':per>noise and gain>0,'model_only_diagnostic_not_measured_oracle':True})
  write_json(out/'headroom_gate.json',{'windows':headroom,'gate_rationale':cfg['headroom_gate_rationale'],'not_a_statistical_confidence_bound':True});report['stages'].append('development_headroom_gate_reconstructed');save()
  # Inspect prospective independent-day capacity only; never use these outcomes to tune.
  cohort_source=json.loads(checked(cfg['arrival_cohort']).read_text());origin=utc(cohort_source['observation_origin_utc']);intervals=[(origin+timedelta(days=i),origin+timedelta(days=i,seconds=cfg['horizon_seconds'])) for i in cfg['candidate_independent_day_indices']];counts=[0]*len(intervals);total=0
  with checked(cfg['arrivals']).open() as f:
   for row in csv.DictReader(f):
    total+=1;t=utc(row['arrival_utc'])
    for i,(lo,hi) in enumerate(intervals):
     if lo<=t<hi:counts[i]+=1
  require(total==cohort_source['selected_total_arrivals'],'Truncated independent-day source')
  independent=[{'day_index':day,'start':lo.isoformat(),'end':hi.isoformat(),'arrivals':n,'not_yet_replayed':True,'prior_partition':'reserved arrival calibration context; not used for this diagnostic gate or model fitting'} for day,(lo,hi),n in zip(cfg['candidate_independent_day_indices'],intervals,counts)]
  write_json(out/'independent_block_capacity.json',{'blocks':independent,'selection':'First two chronological days following the original training partition, fixed before physical outcomes. No claim of statistical independence merely from day separation.','forecast_support_gate':'Existing rolling forecaster must not impute unavailable frozen predecessor bins on later days. Physical protocol must prove all predictor history before launch.','physical_authorized_by_this_file':False})
  allowed=all(x['passes_screen'] for x in headroom) and all(counts)
  report.update(status='headroom_gate_passed_protocol_design_required' if allowed else 'blocked_no_resolvable_development_timing_headroom',overhead_episodes=len(rows),ablation_checks=len(ablations),headroom=headroom,independent_blocks=independent,physical_campaign_launched=False,requires_followup=not allowed,limitations=['Retrospective development diagnostics, no calibration or policy-superiority test.','Recorded instrumentation intervals cannot identify observer-free counterfactual throughput.','Independent-block readiness requires untouched physical outcomes, verified overlap exclusion and fully supported frozen forecast history.'])
  lines=['# Autonomous continuation outcome','',report['status'],'','No new SQL, physical episode, fitting or survivor comparison was executed.','', '## Development headroom']
  for r in headroom:lines.append(f"- Window {r['window_index']}: best perfect-arrival model start={r['best_model_start_seconds']}s; gain over immediate={r['perfect_arrival_model_gain_vs_immediate_sum_seconds']:.9f}s total; observability screen={noise:.9f}s/query; pass={r['passes_screen']}.")
  lines+=['','## Consequence','A long physical benefit campaign is blocked when timing headroom is zero or below the registered observed busy-gap screen. More sophisticated regressors cannot create demonstrated action-timing headroom. The result does not prove there is no physical headroom: model misspecification and observer effects remain.','', 'Next design gate: separate observer overhead causally with a registered matched observer probe; establish real action-time headroom on development blocks; then freeze the six-policy independent-day protocol. Do not silently relax this gate or consume independent blocks for tuning.','', 'The new queue-only and forecast-planner baselines are source-implemented and exercised on actual recorded queue states; they are not physically validated.']
  (out/'report.md').write_text('\n'.join(lines)+'\n');announce(report['status']+'. Saved overhead, ablation and headroom reports. Physical campaign not launched; inspect report before changing design.','terminal_notification.json')
 except Exception as e:report.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc());raise
 finally:
  report['ended_utc']=now();save();write_json(out/'result.json',report)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
