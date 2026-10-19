#!/usr/bin/env python3
"""Prepare substantial real workloads, model artifacts and independent real-data checks."""
import argparse,csv,json,math,statistics,ast,shutil
from pathlib import Path
from common import checked,sha,write_json,require,now,utc
from costs import EmpiricalCosts
from forecast import SeasonalArrivalForecast
from simulator import simulate as fluid_simulate,choose as fluid_choose
from snapshot_simulator import simulate as snapshot_simulate,choose as snapshot_choose

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());version=cfg.get('policy_model_version','fluid_v1');require(version in ('fluid_v1','snapshot_whole_call_v2'),'Unknown prepared model version');simulate,choose=(snapshot_simulate,snapshot_choose) if version=='snapshot_whole_call_v2' else (fluid_simulate,fluid_choose);out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False);report={'status':'running','started_utc':now(),'physical_queries_executed':0,'new_physical_outcomes_used_for_model':False,'tests':[]}
 try:
  audit=json.loads(checked(cfg['input_audit']).read_text());require(audit['status']=='audited_actual_cost_support_and_new_source_capacity','Input gate failed')
  for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_text());shutil.copy2(p,out/p.name)
  costs=EmpiricalCosts.from_protocol(cfg);costs.save(out/'empirical_costs.json');
  if 'frozen_cost_model' in cfg:checked(cfg['frozen_cost_model']);require(sha(out/'empirical_costs.json')==cfg['frozen_cost_model']['sha256'],'Historical cost model changed during source preparation')
  loaded=EmpiricalCosts.load(out/'empirical_costs.json');require(loaded.summary()==costs.summary(),'Saved model roundtrip differs')
  # Independently reconstruct every training cell from actual CSV labels.
  from collections import defaultdict
  values=defaultdict(list);export=checked(cfg['candidate_export'])
  with (export.parent/'queries.csv').open() as f:
   for r in csv.DictReader(f):values[(int(r['query_id']),int(r['file_count']),r['maintenance_client_pending_at_feature_time']=='True')].append(float(r['service_target_ms'])/1000)
  require(set(values)==set(costs.query_cells) and all(statistics.median(v)==costs.service(*k) for k,v in values.items()),'Empirical model reconstructed incorrectly');report['tests'].append('all_real_conditional_medians_and_serialized_model_reconstructed')
  intervals=audit['prospective_intervals'];arrivals_path=checked(cfg['arrivals']);selected=[[] for _ in intervals];identities=set();count=0
  with arrivals_path.open() as f:
   for r in csv.DictReader(f):
    t=utc(r['arrival_utc']);count+=1
    for i,interval in enumerate(intervals):
     start,end=utc(interval['start']),utc(interval['end'])
     if start<=t<end:
      require(r['queryId'] not in identities,'Repeated prospective source ID');identities.add(r['queryId']);delta=t-start;offset=(delta.days*86400+delta.seconds)*1000000000+delta.microseconds*1000
      selected[i].append({'source_query_id':r['queryId'],'warehouse_id':r['warehouseId'],'source_arrival_utc':r['arrival_utc'],'offset_ns':offset,'query_id':cfg['query_ids'][len(selected[i])%len(cfg['query_ids'])]})
  cohort=json.loads(checked(cfg['cohort']).read_text());require(count==cohort['selected_total_arrivals'],'Truncated source CSV')
  forecast=SeasonalArrivalForecast(cfg['arrivals'],origin=cohort['observation_origin_utc'],history_days=cfg['forecast_history_days'],bin_seconds=cfg['decision_interval_seconds'],freeze_source_time=intervals[0]['start'])
  model_artifacts=[];diagnostics=[]
  for i,(interval,selected_rows) in enumerate(zip(intervals,selected)):
   require(len(selected_rows)==interval['arrivals'],'Arrival missing/extra');path=out/f'mapped_arrivals_{i}.csv'
   with path.open('x',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(selected_rows[0]));w.writeheader();w.writerows(selected_rows)
   start,end=utc(interval['start']),utc(interval['end']);horizon=(end-start).total_seconds();events=[{'source_query_id':r['source_query_id'],'arrival_seconds':r['offset_ns']/1e9,'query_id':r['query_id']} for r in selected_rows]
   base=simulate(events,now=0,files=cfg['initial_file_count'],costs=costs);clock=0;independent=[]
   for event in events:
    begin=max(clock,event['arrival_seconds']);finish=begin+costs.service(event['query_id'],cfg['initial_file_count'],False);independent.append(finish-event['arrival_seconds']);clock=finish+costs.turnaround
   require(base['completed']==len(events) and [r['source_query_id'] for r in base['queries']]==[r['source_query_id'] for r in events],'Simulation drops/duplicates/reorders source queries')
   require(math.isclose(sum(independent),base['sum_response_seconds'],rel_tol=cfg['numeric_relative_tolerance'],abs_tol=cfg['numeric_absolute_tolerance_seconds']),'Independent FIFO recurrence differs');report['tests'].append(f'window_{i}_full_actual_arrivals_FIFO_conservation_and_response_recurrence')
   pred=forecast.forecast(decision_source_time=interval['start'],horizon_end_source_time=interval['end'],last_offered_query_id=None,query_ids=cfg['query_ids']);require(utc(pred['maximum_history_timestamp'])<start,'Forecast future leakage');require(all(j<(utc(intervals[0]['start'])-forecast.origin).total_seconds()/forecast.bin_seconds for b in pred['bins'] for j in b['history_bin_indices']),'Forecast uses current/future trace bin')
   # Recompute each seasonal estimate from independently grouped past arrivals.
   actual_counts={}
   with arrivals_path.open() as f:
    for r in csv.DictReader(f):
     t=utc(r['arrival_utc'])
     if t>=utc(intervals[0]['start']):break
     j=int((t-forecast.origin).total_seconds())//cfg['decision_interval_seconds'];actual_counts[j]=actual_counts.get(j,0)+1
   for b in pred['bins']:
    observed=[actual_counts.get(j,0) for j in b['history_bin_indices']];require(observed==b['actual_historical_counts'],'Historical predictor source differs');expected=statistics.mean(observed)*(utc(b['end'])-utc(b['start'])).total_seconds()/cfg['decision_interval_seconds'];require(expected==b['expected_count'] and round(expected)==b['forecast_count'],'Forecast not reconstructed')
   forecast_events=[dict(r,arrival_seconds=r['arrival_seconds']) for r in pred['events']];candidate_starts=list(range(0,int(horizon),cfg['decision_interval_seconds']));forecast_decision=choose(forecast_events,now=0,files=cfg['initial_file_count'],costs=costs,candidate_starts=candidate_starts);oracle=choose(events,now=0,files=cfg['initial_file_count'],costs=costs,candidate_starts=candidate_starts)
   require(all(simulate(events,now=0,files=cfg['initial_file_count'],costs=costs,rewrite_start=s)['completed']==len(events) for s in candidate_starts),'Maintenance simulator loses actual demands')
   if version=='snapshot_whole_call_v2':
    for action_start in candidate_starts:
     simulated=simulate(events,now=0,files=cfg['initial_file_count'],costs=costs,rewrite_start=action_start);clock=0;end=simulated['rewrite_end_seconds'];total=0
     for event,q in zip(events,simulated['queries']):
      begin=max(clock,event['arrival_seconds']);layout=simulated['final_layout_files'] if begin>=end else cfg['initial_file_count'];pending=action_start<=begin<end;finish=begin+costs.query_cells[(event['query_id'],layout,pending)]['median_seconds'];require(q['source_query_id']==event['source_query_id'] and q['start_seconds']==begin and q['finish_seconds']==finish and q['dispatch_layout_files']==layout,'Independent snapshot whole-call recurrence differs');total+=finish-event['arrival_seconds'];clock=finish+costs.turnaround
     require(total==simulated['sum_response_seconds'],'Independent snapshot response sum differs')
    report['tests'].append(f'window_{i}_all_action_pinned_whole_call_recurrences_reconstructed')
   diagnostics.append({'window_index':i,'source_interval':interval,'forecast':pred,'forecast_decision':forecast_decision,'perfect_arrival_diagnostic_only':oracle,'noaction_model_drain_seconds':base['estimated_drain_seconds'],'all_model_outputs_are_estimates_not_measured_counterfactuals':True});report['tests'].append(f'window_{i}_strict_past_forecast_reconstruction_all_action_candidates_complete')
   model_artifacts.append({'window_index':i,'mapping':{'path':str(path),'sha256':sha(path)},'start':interval['start'],'end':interval['end'],'horizon_seconds':horizon,'arrivals':len(events)})
  write_json(out/'model_diagnostics.json',diagnostics);write_json(out/'workloads.json',model_artifacts)
  report.update(status='passed_real_evidence_core_preparation_and_reconstruction',policy_model_version=version,workloads=model_artifacts,model={'path':str(out/'empirical_costs.json'),'sha256':sha(out/'empirical_costs.json')},estimated_eight_arm_seconds=sum(d['noaction_model_drain_seconds']+cfg['physical_warmup_seconds'] for d in diagnostics)*cfg['planned_policy_count'],limitations=['Only real-source-based model estimates tested; physical controller comparison pending.','Two windows same day; no independent-day calibration.','Perfect-arrival diagnostic is retrospective, not used as deployable predictor.','One rewrite allowance; model has no continuing-ingestion transition or novelty guarantee.'])
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:report.update(ended_utc=now(),protocol_sha256=sha(protocol));write_json(out/'result.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
