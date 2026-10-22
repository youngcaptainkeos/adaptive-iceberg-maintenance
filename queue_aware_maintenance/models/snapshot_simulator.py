"""Dispatch-conditioned whole-call model: a query keeps its selected snapshot.

The maintenance duration estimates when later dispatches may see the new layout.
It does not imply measured sub-query progress rates or causal interference.
"""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import math
from queue_aware_maintenance.core.common import require

def simulate(arrivals,*,now,files,costs,rewrite_start=None):
 require(all(a['arrival_seconds']<=b['arrival_seconds'] for a,b in zip(arrivals,arrivals[1:])),'Unsorted model arrivals')
 require(rewrite_start is None or rewrite_start>=now,'Rewrite in simulated past')
 rewrite=None if rewrite_start is None else costs.rewrite(files)
 end=None if rewrite is None else rewrite_start+rewrite['median_seconds']
 post=files if rewrite is None else rewrite['predicted_post_files'];clock=now;queries=[]
 for arrival in arrivals:
  begin=max(clock,arrival['arrival_seconds']);layout=post if end is not None and begin>=end else files
  pending=end is not None and rewrite_start<=begin<end
  duration=costs.service(arrival['query_id'],layout,pending)
  require(math.isfinite(duration) and duration>0,'Invalid whole-call empirical duration')
  finish=begin+duration
  queries.append({'source_query_id':arrival.get('source_query_id'),'query_id':arrival['query_id'],'arrival_seconds':arrival['arrival_seconds'],'start_seconds':begin,'finish_seconds':finish,'response_seconds':finish-arrival['arrival_seconds'],'dispatch_layout_files':layout,'dispatch_maintenance_pending':pending})
  clock=finish+costs.turnaround
 return {'status':'snapshot_pinned_model_estimate_not_physical_evidence','sum_response_seconds':sum(q['response_seconds'] for q in queries),'completed':len(queries),'estimated_drain_seconds':0 if not queries else queries[-1]['finish_seconds']-now,'rewrite_start_seconds':rewrite_start,'rewrite_end_seconds':end,'final_layout_files':post,'queries':queries}

def choose(arrivals,*,now,files,costs,candidate_starts):
 candidates=[]
 for start in [None]+list(candidate_starts):
  estimate=simulate(arrivals,now=now,files=files,costs=costs,rewrite_start=start)
  candidates.append({k:estimate[k] for k in ['sum_response_seconds','rewrite_start_seconds','rewrite_end_seconds','estimated_drain_seconds','final_layout_files']})
 best=min(candidates,key=lambda x:(x['sum_response_seconds'],x['rewrite_start_seconds'] is not None,float('inf') if x['rewrite_start_seconds'] is None else x['rewrite_start_seconds']))
 return {'chosen':best,'candidates':candidates,'objective':'sum_predicted_response_seconds_one_rewrite_allowance_no_scalar_maintenance_penalty','execute_now':best['rewrite_start_seconds']==now}
