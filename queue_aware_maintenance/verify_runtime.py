#!/usr/bin/env python3
"""Server preflight on actual prepared sources/models, no generated data or SQL."""
import argparse,ast,json,math,inspect
from pathlib import Path
from common import checked,require,write_json,sha,now,utc
from costs import EmpiricalCosts
from forecast import SeasonalArrivalForecast
from policy import MaintenancePolicy

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False);report={'status':'running','started_utc':now(),'new_SQL_executed':False,'checks':[]}
 try:
  preparation=json.loads(checked(cfg['core_preparation']).read_text());require(preparation['status']=='passed_real_evidence_core_preparation_and_reconstruction','Core tests not passed');model=checked(preparation['model']);costs=EmpiricalCosts.load(model)
  for p in Path(__file__).parent.rglob('*.py'):ast.parse(p.read_text())
  import run_episode,audit_episode,engine_evidence,ledger
  from pyhive import hive
  import psutil
  report['checks'].append('all_new_and_frozen_runtime_sources_parse_and_required_server_imports_available')
  origin=cfg['observation_origin_utc'];freeze=preparation['workloads'][0]['start'];forecast=SeasonalArrivalForecast(cfg['arrivals'],origin=origin,history_days=cfg['forecast_history_days'],bin_seconds=cfg['decision_interval_seconds'],freeze_source_time=freeze);policies=[]
  for workload in preparation['workloads']:
   checked(workload['mapping'])
   for name in cfg['policies']:
    policy=MaintenancePolicy(name,costs,forecast,workload['start'],workload['end'],cfg['query_ids'],cfg['decision_interval_seconds']);decision=policy.decide(elapsed_seconds=0,queued=[],last_offered_query_id=None,files=cfg['initial_file_count'])
    require(decision['policy']==name,'Wrong actual policy')
    if name=='no_maintenance':require(not decision['execute_now'],'Null control starts maintenance')
    if name=='immediate':require(decision['execute_now'],'Immediate control fails to act')
    if 'forecast' in decision:require(utc(decision['forecast']['maximum_history_timestamp'])<utc(freeze),'Future forecast leakage')
    policies.append({'window':workload['window_index'],'policy':name,'initial_decision':decision})
  report['checks'].append('all_eight_registered_policy_window_combinations_execute_on_actual_past_only_forecasts_and_measured_costs')
  # Independent policy/objective reconstruction from the saved model diagnostic.
  diagnostics=json.loads((Path(cfg['core_preparation']['path']).parent/'model_diagnostics.json').read_text())
  for d in diagnostics:
   actual=[r for r in policies if r['window']==d['window_index'] and r['policy']=='queue_aware'][0]['initial_decision'];require(actual['chosen']==d['forecast_decision']['chosen'],'Controller integration changes initial objective/ranking')
   require(len(actual['candidates'])==1+math.ceil(preparation['workloads'][d['window_index']]['horizon_seconds']/cfg['decision_interval_seconds']),'Missing model action candidate')
  require('queued' in inspect.signature(MaintenancePolicy.decide).parameters and 'mapped_arrivals' not in inspect.signature(MaintenancePolicy.decide).parameters,'Policy must not receive future physical source schedule')
  report.update(status='passed_actual_source_controller_runtime_preflight',policies=policies,model_sha256=sha(model),estimated_eight_arm_seconds=preparation['estimated_eight_arm_seconds'],limitations=['No actual SQL in preflight; all physical table/task/drain proofs remain pending.','Model-only initial decisions choose immediate on both windows; this is not observed temporal headroom.','Two windows from one source day; no power/calibration/novelty claim.'])
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:report.update(ended_utc=now(),protocol_sha256=sha(protocol),code_sha256=sha(__file__));write_json(out/'result.json',report);print(json.dumps({k:v for k,v in report.items() if k!='policies'}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
