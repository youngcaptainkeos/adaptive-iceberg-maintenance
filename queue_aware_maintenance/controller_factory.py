"""Explicitly versioned controller construction; never upgrade old episodes."""
import json
from pathlib import Path
from common import checked,require,sha
from policy import MaintenancePolicy
from snapshot_policy import SnapshotMaintenancePolicy

def build_policy(cfg,costs,forecast):
 version=cfg.get('policy_model_version','fluid_v1')
 require(version in ('fluid_v1','snapshot_whole_call_v2'),'Unknown registered policy model version')
 if version=='snapshot_whole_call_v2':
  proof=json.loads(checked(cfg['snapshot_model_verification']).read_text())
  require(proof['status']=='passed_real_source_snapshot_model_reconstruction_only','Snapshot model reconstruction not passed')
  require(proof['snapshot_simulator_sha256']==sha(Path(__file__).parent/'snapshot_simulator.py'),'Snapshot model changed after verification')
  for name,value in cfg['snapshot_policy_code_sha256'].items():
   require(name in ('policy.py','snapshot_policy.py') and sha(Path(__file__).parent/name)==value,'Snapshot policy source binding differs')
  require(set(cfg['snapshot_policy_code_sha256'])=={'policy.py','snapshot_policy.py'},'Incomplete snapshot policy source binding')
  cls=SnapshotMaintenancePolicy
 else:cls=MaintenancePolicy
 return cls(cfg['policy'],costs,forecast,cfg['source_start_utc'],cfg['source_end_utc'],cfg['query_ids'],cfg['decision_interval_seconds'])
