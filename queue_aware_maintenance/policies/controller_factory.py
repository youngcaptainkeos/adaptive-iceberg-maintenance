"""Explicitly versioned controller construction; never upgrade old episodes."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import json
from pathlib import Path
from queue_aware_maintenance.core.common import checked,require,sha
from queue_aware_maintenance.policies.policy import MaintenancePolicy
from queue_aware_maintenance.policies.snapshot_policy import SnapshotMaintenancePolicy

def build_policy(cfg,costs,forecast):
 version=cfg.get('policy_model_version','fluid_v1')
 require(version in ('fluid_v1','snapshot_whole_call_v2'),'Unknown registered policy model version')
 if version=='snapshot_whole_call_v2':
  proof=json.loads(checked(cfg['snapshot_model_verification']).read_text())
  require(proof['status']=='passed_real_source_snapshot_model_reconstruction_only','Snapshot model reconstruction not passed')
  require(proof['snapshot_simulator_sha256']==sha(source_file('snapshot_simulator.py')),'Snapshot model changed after verification')
  for name,value in cfg['snapshot_policy_code_sha256'].items():
   require(name in ('policy.py','snapshot_policy.py') and sha(source_file(name))==value,'Snapshot policy source binding differs')
  require(set(cfg['snapshot_policy_code_sha256'])=={'policy.py','snapshot_policy.py'},'Incomplete snapshot policy source binding')
  cls=SnapshotMaintenancePolicy
 else:cls=MaintenancePolicy
 if cfg['policy']=='fixed_start':
  require(version=='snapshot_whole_call_v2' and cfg.get('fixed_start_contract')=='first_controller_opportunity_v1','Unregistered experimental intervention')
  require(sha(source_file('fixed_start_policy.py'))==cfg['fixed_start_code_sha256'],'Changed experimental timing source')
  from queue_aware_maintenance.policies.fixed_start_policy import FixedStartPolicy
  return FixedStartPolicy(cfg['fixed_start_seconds'],cfg['source_start_utc'],cfg['source_end_utc'])
 if cfg['policy'] in ('queue_only','forecast_planner'):
  require(version=='snapshot_whole_call_v2' and cfg.get('ablation_contract')=='information_removal_v1','Unregistered ablation')
  require(sha(source_file('ablation_policy.py'))==cfg['ablation_code_sha256'],'Changed ablation source')
  from queue_aware_maintenance.policies.ablation_policy import AblationPolicy
  cls=AblationPolicy
 return cls(cfg['policy'],costs,forecast,cfg['source_start_utc'],cfg['source_end_utc'],cfg['query_ids'],cfg['decision_interval_seconds'])
