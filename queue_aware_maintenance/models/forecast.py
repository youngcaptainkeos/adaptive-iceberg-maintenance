"""Past-only seasonal empirical count forecast; no synthetic replay demand."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
from datetime import datetime,timedelta
import csv,statistics,math
from queue_aware_maintenance.core.common import require,sha,checked,utc

class SeasonalArrivalForecast:
 def __init__(self,spec,*,origin,history_days,bin_seconds,freeze_source_time):
  self.path=checked(spec);self.source_sha256=sha(self.path);self.origin=utc(origin);self.history_days=history_days;self.bin_seconds=bin_seconds;self.freeze=utc(freeze_source_time);self.counts={};self.maximum_used=None
  with self.path.open() as f:
   for r in csv.DictReader(f):
    t=utc(r['arrival_utc'])
    if t>=self.freeze:break
    i=int((t-self.origin).total_seconds())//bin_seconds;self.counts[i]=self.counts.get(i,0)+1;self.maximum_used=t
  require(self.maximum_used is not None,'No actual predecision history')
 def forecast(self,*,decision_source_time,horizon_end_source_time,last_offered_query_id,query_ids):
  start=utc(decision_source_time);end=utc(horizon_end_source_time);require(self.freeze<=start and self.maximum_used<start,'Future source leakage')
  require(86400%self.bin_seconds==0,'Register day-dividing forecast bins');perday=86400//self.bin_seconds;begin=int((start-self.origin).total_seconds())//self.bin_seconds;stop=math.ceil((end-self.origin).total_seconds()/self.bin_seconds);bins=[];events=[];ordinal=query_ids.index(last_offered_query_id)+1 if last_offered_query_id is not None else 0
  for i in range(begin,stop):
   left=max(start,self.origin+timedelta(seconds=i*self.bin_seconds));right=min(end,self.origin+timedelta(seconds=(i+1)*self.bin_seconds))
   if right<=left:continue
   predecessors=[i-d*perday for d in range(1,self.history_days+1)];require(min(predecessors)>=0,'Insufficient registered history days')
   # Missing sparse count keys are observed zero arrivals in the verified
   # complete cohort bins, not missing dataset or a mathematical fallback.
   history=[self.counts.get(j,0) for j in predecessors];expected=statistics.mean(history)*(right-left).total_seconds()/self.bin_seconds;n=round(expected);bins.append({'bin_index':i,'history_bin_indices':predecessors,'actual_historical_counts':history,'expected_count':expected,'forecast_count':n,'start':left.isoformat(),'end':right.isoformat()})
   for j in range(n):
    events.append({'arrival_seconds':(left-start).total_seconds()+(j+0.5)*(right-left).total_seconds()/n,'query_id':query_ids[ordinal%len(query_ids)],'source_query_id':None,'meaning':'model_forecast_only_not_offered_physical_arrival'});ordinal+=1
  return {'bins':bins,'events':events,'maximum_history_timestamp':self.maximum_used.isoformat(),'history_frozen_before_source_time':self.freeze.isoformat(),'decision_source_time':start.isoformat(),'source_sha256':self.source_sha256,'sql_mix_meaning':'registered_benchmark_round_robin_not_original_snowflake_SQL'}
