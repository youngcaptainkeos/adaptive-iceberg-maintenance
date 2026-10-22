#!/usr/bin/env python3
"""Lower-bound audit of the actual registered serial queue; no physical forecasts."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,json
from pathlib import Path
from datetime import timedelta
from queue_aware_maintenance.core.common import checked,require,write_json,sha,now,utc
from queue_aware_maintenance.runtime.resource_admission import evaluate

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False);registration_path=checked(cfg['prior_registration']);registration=json.loads(registration_path.read_text());root=registration_path.parent;data=(root/'progress.json').read_bytes();(out/'prior_progress_snapshot.json').write_bytes(data);progress=json.loads(data);manifest=json.loads((root/'execution_manifest.json').read_text());attempted={a['experiment_id'] for a in progress['attempts']};remaining=[]
 for item in manifest['all_episodes']:
  if item['experiment_id'] in attempted:continue
  ep=json.loads(checked(item['protocol']).read_text());remaining.append({'experiment_id':item['experiment_id'],'registered_warmup_seconds':ep['telemetry']['warmup_seconds'],'registered_arrival_horizon_seconds':ep['horizon_seconds']})
 require(len(remaining)==progress['unattempted'],'Progress and manifest population differ');clock=utc(now());minimum=sum(r['registered_warmup_seconds']+r['registered_arrival_horizon_seconds'] for r in remaining);earliest=clock+timedelta(seconds=minimum);future_path=checked(cfg['corrected_registration']);future=json.loads(future_path.read_text());prepared=json.loads(checked(future['core_preparation']).read_text());admission=evaluate(future,prepared,REPOSITORY_ROOT);pid=progress['pid'];cmdline=Path(f'/proc/{pid}/cmdline');actual=cmdline.read_bytes().replace(b'\x00',b' ').decode() if cmdline.exists() else None
 report={'status':'audited_registered_schedule_constraint_only','observed_utc':clock.isoformat(),'protocol_sha256':sha(protocol),'code_sha256':sha(__file__),'prior_registration_sha256':sha(registration_path),'prior_progress_snapshot_sha256':sha(out/'prior_progress_snapshot.json'),'coordinator_pid':pid,'actual_coordinator_cmdline':actual,'coordinator_matches_expected_runtime':actual is not None and cfg['expected_prior_runtime'] in actual and 'run_study.py' in actual,'prior_status':progress['status'],'remaining_unattempted_arms':remaining,'remaining_success_path_lower_bound_seconds':minimum,'earliest_prior_successful_terminal_lower_bound_utc':earliest.isoformat(),'corrected_latest_model_feasible_launch_utc':admission['latest_model_feasible_launch_utc'],'prior_success_path_misses_registered_corrected_admission':earliest>utc(admission['latest_model_feasible_launch_utc']),'corrected_admitted_now':admission['admitted_at_check'],'new_SQL_executed':False,'limitations':['Lower bound excludes current arm remaining drain, every initialization/final audit and other overhead.','This is incompatibility with the registered model-based admission rule, not proof of an absolute physical runtime bound.','Earlier resource release could occur from an actual failure; failure is not a completion strategy and must be audited.','No process was stopped, queue changed, experiment launched, demand compressed or acceptance gate weakened.']};write_json(out/'result.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
