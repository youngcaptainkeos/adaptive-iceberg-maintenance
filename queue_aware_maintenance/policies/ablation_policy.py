"""Explicit information-removal comparators; never fabricate physical arrivals."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
from datetime import timedelta
from queue_aware_maintenance.core.common import require
from queue_aware_maintenance.policies.snapshot_policy import SnapshotMaintenancePolicy
from queue_aware_maintenance.models.snapshot_simulator import choose

class AblationPolicy(SnapshotMaintenancePolicy):
 def __init__(self,name,*args):
  require(name in ('queue_only','forecast_planner'),'Unknown information ablation')
  super().__init__('queue_aware',*args);self.name=name
 def decide(self,*,elapsed_seconds,queued,last_offered_query_id,files):
  end=(self.end-self.start).total_seconds();base={'policy':self.name,'elapsed_seconds':elapsed_seconds,'queued_source_ids':[r['source_query_id'] for r in queued],'file_count':files,'execute_now':False}
  if elapsed_seconds>=end:return dict(base,reason='registered_no_new_rewrite_after_arrival_horizon')
  if self.name=='queue_only':
   arrivals=[{'source_query_id':r['source_query_id'],'query_id':int(r['query_id']),'arrival_seconds':int(r['offset_ns'])/1e9} for r in queued]
   base['information_ablation']='Current actual queue only; no future-demand estimate enters this comparator.'
  else:
   prediction=self.forecast.forecast(decision_source_time=(self.start+timedelta(seconds=elapsed_seconds)).isoformat(),horizon_end_source_time=self.end.isoformat(),last_offered_query_id=last_offered_query_id,query_ids=self.query_ids)
   arrivals=[dict(r,arrival_seconds=r['arrival_seconds']+elapsed_seconds) for r in prediction['events']]
   base.update(forecast={k:v for k,v in prediction.items() if k!='events'},information_ablation='Same horizon model and forecast; existing queue omitted from optimization only, never from physical replay/accounting.')
  starts=[elapsed_seconds]+[float(i) for i in range(self.interval,int(end),self.interval) if i>elapsed_seconds]
  return dict(base,**choose(arrivals,now=elapsed_seconds,files=files,costs=self.costs,candidate_starts=starts),reason='registered_information_removal_baseline_not_published_system_reproduction')
