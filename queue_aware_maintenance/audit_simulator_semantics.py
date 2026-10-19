#!/usr/bin/env python3
"""Audit query-pinned layout and whole-call target semantics on real source records."""
import argparse,csv,json,math,sys
from pathlib import Path
from common import checked,sha,require,write_json,now
from costs import EmpiricalCosts
from simulator import simulate

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'running','started_utc':now(),'new_SQL_executed':False,'new_physical_outcomes_used':False,'protocol_sha256':sha(protocol),'code_sha256':sha(__file__)}
 try:
  prepared=json.loads(checked(cfg['core_preparation']).read_text());costs=EmpiricalCosts.load(checked(prepared['model']));all_cases=[];counterexamples=[]
  for w in prepared['workloads']:
   rows=list(csv.DictReader(checked(w['mapping']).open()));arrivals=[{'source_query_id':r['source_query_id'],'query_id':int(r['query_id']),'arrival_seconds':int(r['offset_ns'])/1e9} for r in rows]
   for start in range(0,int(w['horizon_seconds']),cfg['decision_interval_seconds']):
    estimate=simulate(arrivals,now=0,files=cfg['initial_file_count'],costs=costs,rewrite_start=start);end=estimate['rewrite_end_seconds'];post=estimate['final_layout_files']
    for q in estimate['queries']:
     begin=q['start_seconds'];layout=post if begin>=end else cfg['initial_file_count'];pending=start<=begin<end;whole_call=costs.service(q['query_id'],layout,pending);actual=q['finish_seconds']-begin
     if begin<end<q['finish_seconds'] or begin<start<q['finish_seconds']:
      record={'window_index':w['window_index'],'source_query_id':q['source_query_id'],'query_id':q['query_id'],'rewrite_start_seconds':start,'rewrite_end_seconds':end,'query_start_seconds':begin,'fluid_query_finish_seconds':q['finish_seconds'],'pinned_dispatch_layout':layout,'dispatch_pending':pending,'whole_call_conditional_duration_seconds':whole_call,'fluid_duration_seconds':actual}
      all_cases.append(record)
      if not math.isclose(actual,whole_call,rel_tol=cfg['numeric_relative_tolerance'],abs_tol=cfg['numeric_absolute_tolerance_seconds']):counterexamples.append(record)
  require(all_cases,'No actual-source simulated boundary crossings to inspect')
  # Actual historical SQL and exported target rows establish the contract;
  # model boundary examples are estimates over real arrivals, not physical labels.
  export=checked(cfg['candidate_export']);manifest=json.loads(export.read_text());targets=list(csv.DictReader((export.parent/'queries.csv').open()));verified=0;seen=set()
  for row in targets:
   eid=row['experiment_id']
   if eid in seen:continue
   seen.add(eid);spec=manifest['source_evidence'][eid];result=checked(spec['registered_result_spec']);events=result.parent/'events.jsonl';require(sha(events)==spec['events_sha256'],'Historical raw evidence changed')
   requests={};completed={};observations={}
   with events.open() as f:
    for line in f:
     r=json.loads(line);mid=r.get('measurement_id')
     if r['kind']=='statement_requested' and r.get('role')=='trace_query':requests[mid]=r
     if r['kind']=='statement_completed' and r.get('role')=='trace_query':completed[mid]=r
     if r['kind']=='query_observation':observations[mid]=r
   for target in (r for r in targets if r['experiment_id']==eid):
    mid=target['measurement_id'];r=completed[mid];obs=observations[mid]
    require('VERSION AS OF '+str(obs['snapshot_id']) in requests[mid]['sql'],'Historical SQL not snapshot pinned')
    duration=r['fetch_end']['monotonic_ns']-r['client_execute_start']['monotonic_ns'];require(duration==int(target['client_elapsed_ns']) and math.isclose(duration/1e6,float(target['service_target_ms']),rel_tol=cfg['numeric_relative_tolerance'],abs_tol=cfg['numeric_absolute_tolerance_seconds']),'Target not whole-call elapsed')
    verified+=1
  report.update(status='failed_model_semantics_gate' if counterexamples else 'passed_snapshot_pinned_whole_call_semantics',historical_query_targets_verified=verified,actual_source_model_boundary_cases=len(all_cases),inconsistent_boundary_cases=len(counterexamples),examples=counterexamples[:cfg['maximum_report_examples']],fluid_model_sha256=sha(Path(__file__).parent/'simulator.py'),interpretation='Historical labels describe whole pinned-query client calls. They do not identify fractional work rates or allow a query to switch to a compacted snapshot mid-call. Boundary outputs are model estimates, not measured counterfactuals.',live_physical_runtime_changed=False)
 except Exception as e:report.update(status='failed_audit_execution_preserved',error=str(e));raise
 finally:report['ended_utc']=now();write_json(out/'result.json',report);print(json.dumps(report),flush=True)
 return 1 if report['status']=='failed_model_semantics_gate' else 0
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);sys.exit(run(p.parse_args().protocol))
