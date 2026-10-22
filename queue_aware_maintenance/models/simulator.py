"""FIFO expected-response model; outputs estimates, never physical outcomes."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import math
from queue_aware_maintenance.core.common import require

def simulate(arrivals,*,now,files,costs,rewrite_start=None):
 require(all(a['arrival_seconds']<=b['arrival_seconds'] for a,b in zip(arrivals,arrivals[1:])),'Unsorted simulated arrivals')
 rewrite=costs.rewrite(files) if rewrite_start is not None else None
 require(rewrite_start is None or rewrite_start>=now,'Cannot start rewrite in simulated past')
 rewrite_end=None if rewrite is None else rewrite_start+rewrite['median_seconds'];post=files if rewrite is None else rewrite['predicted_post_files'];clock=now;out=[]
 def regime(t):
  if rewrite is None or t<rewrite_start:return files,False,rewrite_start
  if t<rewrite_end:return files,True,rewrite_end
  return post,False,None
 for arrival in arrivals:
  begin=max(clock,arrival['arrival_seconds']);t=begin;work=1.0
  while work>0:
   layout,pending,boundary=regime(t);duration=costs.service(arrival['query_id'],layout,pending)
   require(math.isfinite(duration) and duration>0,'Invalid empirical duration')
   finish=t+work*duration
   if boundary is None or finish<=boundary:t=finish;work=0
   else:
    require(boundary>t,'Nonprogressing regime boundary');work-=(boundary-t)/duration;t=boundary
  out.append({'source_query_id':arrival.get('source_query_id'),'query_id':arrival['query_id'],'arrival_seconds':arrival['arrival_seconds'],'start_seconds':begin,'finish_seconds':t,'response_seconds':t-arrival['arrival_seconds']})
  clock=t+costs.turnaround
 total=sum(r['response_seconds'] for r in out)
 return {'status':'model_estimate_not_physical_evidence','sum_response_seconds':total,'completed':len(out),'estimated_drain_seconds':0 if not out else out[-1]['finish_seconds']-now,'rewrite_start_seconds':rewrite_start,'rewrite_end_seconds':rewrite_end,'final_layout_files':post,'queries':out}

def choose(arrivals,*,now,files,costs,candidate_starts):
 candidates=[]
 for start in [None]+list(candidate_starts):
  estimate=simulate(arrivals,now=now,files=files,costs=costs,rewrite_start=start)
  candidates.append({k:estimate[k] for k in ['sum_response_seconds','rewrite_start_seconds','rewrite_end_seconds','estimated_drain_seconds','final_layout_files']})
 # Equal expected response conserves maintenance, then earliest start. This is
 # a registered deterministic tie rule, never a fabricated model prediction.
 best=min(candidates,key=lambda x:(x['sum_response_seconds'],x['rewrite_start_seconds'] is not None,float('inf') if x['rewrite_start_seconds'] is None else x['rewrite_start_seconds']))
 return {'chosen':best,'candidates':candidates,'objective':'sum_predicted_response_seconds_one_rewrite_allowance_no_scalar_maintenance_penalty','execute_now':best['rewrite_start_seconds']==now}
