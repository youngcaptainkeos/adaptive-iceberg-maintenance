#!/usr/bin/env python3
"""Independent whole-call FIFO reconstruction on all real-source action candidates."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,csv,json,math
from pathlib import Path
from queue_aware_maintenance.core.common import checked,require,write_json,sha,now
from queue_aware_maintenance.models.costs import EmpiricalCosts
from queue_aware_maintenance.models.forecast import SeasonalArrivalForecast
from queue_aware_maintenance.models.snapshot_simulator import simulate,choose
from queue_aware_maintenance.models.simulator import simulate as fluid_simulate
from queue_aware_maintenance.policies.snapshot_policy import SnapshotMaintenancePolicy

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'running','started_utc':now(),'physical_validation_passed':False,'prospective_physical_outcomes_used':False,'checks':[]}
 try:
  prior=json.loads(checked(cfg['semantics_audit']).read_text());require(prior['status']=='failed_model_semantics_gate' and prior['historical_query_targets_verified']==cfg['historical_query_rows'],'Missing real-label mismatch proof')
  prepared=json.loads(checked(cfg['core_preparation']).read_text());costs=EmpiricalCosts.load(checked(prepared['model']));diagnostics=[];checked_queries=0;crossings=0
  forecast=SeasonalArrivalForecast(cfg['arrivals'],origin=cfg['observation_origin_utc'],history_days=cfg['forecast_history_days'],bin_seconds=cfg['decision_interval_seconds'],freeze_source_time=prepared['workloads'][0]['start'])
  for w in prepared['workloads']:
   rows=list(csv.DictReader(checked(w['mapping']).open()));arrivals=[{'source_query_id':r['source_query_id'],'query_id':int(r['query_id']),'arrival_seconds':int(r['offset_ns'])/1e9} for r in rows];starts=list(range(0,int(w['horizon_seconds']),cfg['decision_interval_seconds']))
   noaction=simulate(arrivals,now=0,files=cfg['initial_file_count'],costs=costs);old=fluid_simulate(arrivals,now=0,files=cfg['initial_file_count'],costs=costs)
   require(noaction['sum_response_seconds']==old['sum_response_seconds'],'No-action model changed')
   for start in [None]+starts:
    actual=simulate(arrivals,now=0,files=cfg['initial_file_count'],costs=costs,rewrite_start=start);clock=0;total=0;rewrite=None if start is None else costs.rewrite(cfg['initial_file_count']);end=None if rewrite is None else start+rewrite['median_seconds']
    require(actual['completed']==len(arrivals) and len(actual['queries'])==len(arrivals),'Source population lost')
    for source,q in zip(arrivals,actual['queries']):
     begin=max(clock,source['arrival_seconds']);post=end is not None and begin>=end;layout=rewrite['predicted_post_files'] if post else cfg['initial_file_count'];pending=end is not None and start<=begin<end;duration=costs.query_cells[(source['query_id'],layout,pending)]['median_seconds'];finish=begin+duration
     require(q['source_query_id']==source['source_query_id'] and q['start_seconds']==begin and q['finish_seconds']==finish and q['dispatch_layout_files']==layout and q['dispatch_maintenance_pending']==pending,'Pinned whole-call recurrence differs')
     require(math.isclose(finish-begin,duration,rel_tol=cfg['numeric_relative_tolerance'],abs_tol=cfg['numeric_absolute_tolerance_seconds']),'Whole-call target not preserved')
     if end is not None and (begin<end<finish or begin<start<finish):crossings+=1
     total+=finish-source['arrival_seconds'];clock=finish+costs.turnaround;checked_queries+=1
    require(total==actual['sum_response_seconds'],'Independent full-response sum differs')
   prediction=forecast.forecast(decision_source_time=w['start'],horizon_end_source_time=w['end'],last_offered_query_id=None,query_ids=cfg['query_ids'])
   controller=SnapshotMaintenancePolicy('queue_aware',costs,forecast,w['start'],w['end'],cfg['query_ids'],cfg['decision_interval_seconds']);decision=controller.decide(elapsed_seconds=0,queued=[],last_offered_query_id=None,files=cfg['initial_file_count']);expected=choose(prediction['events'],now=0,files=cfg['initial_file_count'],costs=costs,candidate_starts=starts);require(decision['chosen']==expected['chosen'] and decision['candidates']==expected['candidates'],'Snapshot controller does not use pinned model')
   diagnostics.append({'window_index':w['window_index'],'past_only_forecast_decision':choose(prediction['events'],now=0,files=cfg['initial_file_count'],costs=costs,candidate_starts=starts),'perfect_arrival_diagnostic_only':choose(arrivals,now=0,files=cfg['initial_file_count'],costs=costs,candidate_starts=starts)})
  require(crossings>0,'No real-source boundary cases checked')
  report.update(status='passed_real_source_snapshot_model_reconstruction_only',checks=['All real-source candidates preserve whole pinned-query duration and FIFO identity','No-action predictions unchanged','Past-only forecast choices recomputed without prospective labels or refit'],query_candidate_checks=checked_queries,boundary_crossing_checks=crossings,diagnostics=diagnostics,model_accepted=False,limitations=['No physical validation of the repaired model/controller. Frozen live cohort uses original fluid model and must not be silently relabelled.','Whole-call pending label is observational and does not establish causal interference.','Metadata publication delay after rewrite completion remains unmodelled; layout-transition time is an approximation.','No calibrated forecasts, performance or publication novelty claim.'])
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:report.update(ended_utc=now(),protocol_sha256=sha(protocol),code_sha256=sha(__file__),snapshot_simulator_sha256=sha(source_file('snapshot_simulator.py')));write_json(out/'result.json',report);print(json.dumps({k:v for k,v in report.items() if k!='diagnostics'}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
