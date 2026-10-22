#!/usr/bin/env python3
"""Post-hoc forecast/decomposition diagnostic; never trains or changes a policy."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,csv,json
from pathlib import Path
from queue_aware_maintenance.core.common import checked,require,sha,write_json,now,utc

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'running','started_utc':now(),'protocol_sha256':sha(protocol),'code_sha256':sha(__file__),'post_hoc_diagnostic':True,'policy_changed':False,'model_fitted':False}
 try:
  result_path=checked(cfg['episode_result']);result=json.loads(result_path.read_text());require(result['status']=='audited_complete_real_full_drain_episode_only' and result['completed']==result['arrival_count'] and result['failed']==result['unfinished']==0,'Complete audited arm required')
  d=result_path.parent;ecfg=json.loads((d/'config.json').read_text());mapping=d/'mapped_arrivals.csv';require(sha(mapping)==ecfg['mapping']['sha256'],'Changed actual arrivals');arrivals=list(csv.DictReader(mapping.open()));require(len(arrivals)==result['arrival_count'],'Changed population')
  require(sha(d/'events.jsonl')==result['events_sha256'],'Changed terminal event ledger')
  first=None
  # Stream the actual ledger; parse only the first decision, no all-event memory copy.
  with (d/'events.jsonl').open('rb') as stream:
   for line in stream:
    if b'"kind": "controller_decision"' in line:
     event=json.loads(line)
     if event.get('kind')=='controller_decision':first=event;break
  require(first is not None and 'forecast' in first['decision'],'No initial forecast decision')
  forecast=first['decision']['forecast'];require(forecast['source_sha256']==ecfg['arrivals']['sha256'],'Forecast source changed');require(utc(forecast['maximum_history_timestamp'])<utc(ecfg['forecast_history_freeze_utc'])<=utc(forecast['decision_source_time']),'Forecast used future history')
  rows=[]
  for b in forecast['bins']:
   lo,hi=utc(b['start']),utc(b['end']);actual=sum(lo<=utc(a['source_arrival_utc'])<hi for a in arrivals);predicted=b['forecast_count'];rows.append({'start':b['start'],'end':b['end'],'forecast_count':predicted,'actual_count':actual,'signed_error_forecast_minus_actual':predicted-actual,'absolute_error':abs(predicted-actual)})
  require(rows,'No forecast bins');actual_total=sum(r['actual_count'] for r in rows);predicted_total=sum(r['forecast_count'] for r in rows);error=sum(r['absolute_error'] for r in rows);n=result['completed'];scale=n*1e9
  report.update(status='completed_posthoc_single_arm_forecast_and_queue_diagnostic',episode_result_sha256=sha(result_path),mapping_sha256=sha(mapping),first_decision_recorded_utc=first['recorded']['utc'],forecast_source_sha256=forecast['source_sha256'],forecast_bins=rows,forecast_bin_mean_absolute_error=error/len(rows),forecast_total=predicted_total,actual_total_in_exact_forecast_intervals=actual_total,weighted_absolute_percentage_error=None if actual_total==0 else error/actual_total,completed=n,mean_response_seconds=result['sum_response_ns']/scale,mean_wait_before_call_seconds=result['sum_wait_before_call_ns']/scale,mean_query_call_seconds=result['sum_service_ns']/scale,wait_fraction_of_total_response=result['sum_wait_before_call_ns']/result['sum_response_ns'],limitations=['Post-hoc descriptive diagnostic on one already observed arm/window, not preregistered forecast calibration or independent-day evidence.','Actual counts use exact recorded forecast intervals; arrivals before decision or outside those intervals are excluded from forecast error only, never from physical response accounting.','Queue waiting includes client scheduling/observation overhead; it is not solely Spark service or a causal compaction cost.','No counterfactual policy benefit can be inferred without the complete registered comparison; no fitting, tuning, objective change or running-code change.'])
  return report
 except Exception as error:
  report.update(status='failed_preserved',error=str(error));raise
 finally:
  report['ended_utc']=now();write_json(out/'result.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
