"""Causal start/wait policy; predictor data never receives future mapped arrivals."""
from datetime import timedelta
from common import require,utc
from simulator import choose

class MaintenancePolicy:
 def __init__(self,name,costs,forecast,source_start,source_end,query_ids,interval_seconds):
  require(name in ('no_maintenance','immediate','forecast_quiet','queue_aware'),'Unknown registered policy');self.name=name;self.costs=costs;self.forecast=forecast;self.start=utc(source_start);self.end=utc(source_end);self.query_ids=query_ids;self.interval=interval_seconds;self.quiet_target=None
 def decide(self,*,elapsed_seconds,queued,last_offered_query_id,files):
  end=(self.end-self.start).total_seconds();base={'policy':self.name,'elapsed_seconds':elapsed_seconds,'queued_source_ids':[r['source_query_id'] for r in queued],'file_count':files,'execute_now':False}
  if elapsed_seconds>=end:return dict(base,reason='registered_no_new_rewrite_after_arrival_horizon')
  if self.name=='no_maintenance':return dict(base,reason='registered_null_control')
  if self.name=='immediate':return dict(base,execute_now=True,reason='registered_immediate_control')
  prediction=self.forecast.forecast(decision_source_time=(self.start+timedelta(seconds=elapsed_seconds)).isoformat(),horizon_end_source_time=self.end.isoformat(),last_offered_query_id=last_offered_query_id,query_ids=self.query_ids)
  base['forecast']={k:v for k,v in prediction.items() if k!='events'}
  if self.name=='forecast_quiet':
   if self.quiet_target is None:
    b=min(prediction['bins'],key=lambda b:(b['expected_count']/(utc(b['end'])-utc(b['start'])).total_seconds(),utc(b['start'])));self.quiet_target=(utc(b['start'])-self.start).total_seconds()
   return dict(base,execute_now=elapsed_seconds>=self.quiet_target,quiet_target_seconds=self.quiet_target,reason='earliest_minimum_past_only_forecast_arrival_rate_bin')
  arrivals=[{'source_query_id':r['source_query_id'],'query_id':int(r['query_id']),'arrival_seconds':int(r['offset_ns'])/1e9} for r in queued]+[dict(r,arrival_seconds=r['arrival_seconds']+elapsed_seconds) for r in prediction['events']];arrivals.sort(key=lambda r:r['arrival_seconds'])
  # Current client is idle at each decision. Candidate future starts are actual
  # registered source-bin opportunities; no ongoing query residual is invented.
  starts=[elapsed_seconds]+[float(i) for i in range(self.interval,int(end),self.interval) if i>elapsed_seconds]
  decision=choose(arrivals,now=elapsed_seconds,files=files,costs=self.costs,candidate_starts=starts)
  return dict(base,**decision,reason='minimum_predicted_total_response_over_current_debt_and_past_only_forecast')
