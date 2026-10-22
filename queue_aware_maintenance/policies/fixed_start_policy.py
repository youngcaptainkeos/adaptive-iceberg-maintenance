"""Registered experimental start-time intervention, not a learned prediction."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
from queue_aware_maintenance.core.common import require,utc

class FixedStartPolicy:
 def __init__(self,delay,source_start,source_end):
  self.delay=delay;self.horizon=(utc(source_end)-utc(source_start)).total_seconds()
  require(isinstance(delay,(int,float)) and not isinstance(delay,bool) and 0<=delay<self.horizon,'Invalid registered intervention time')
 def decide(self,*,elapsed_seconds,queued,last_offered_query_id,files):
  return {'policy':'fixed_start','elapsed_seconds':elapsed_seconds,'queued_source_ids':[r['source_query_id'] for r in queued],'file_count':files,'execute_now':self.delay<=elapsed_seconds<self.horizon,'registered_start_seconds':self.delay,'reason':'first_observed_controller_opportunity_at_or_after_registered_time_not_a_prediction'}
