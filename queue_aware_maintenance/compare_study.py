#!/usr/bin/env python3
"""Post-collection raw reconstruction; never refits costs or changes policy choices."""
import argparse,csv,json
from pathlib import Path
from common import checked,require,sha,write_json,now
from audit_episode import audit
from costs import EmpiricalCosts
from forecast import SeasonalArrivalForecast
from controller_factory import build_policy

def reconstruct_decisions(directory):
 d=Path(directory);cfg=json.loads((d/'config.json').read_text())
 events=[json.loads(x) for x in (d/'events.jsonl').open()]
 mapping=list(csv.DictReader((d/'mapped_arrivals.csv').open()))
 byid={r['source_query_id']:r for r in mapping}
 costs=EmpiricalCosts.load(checked(cfg['model']))
 forecast=SeasonalArrivalForecast(cfg['arrivals'],origin=cfg['observation_origin_utc'],history_days=cfg['forecast_history_days'],bin_seconds=cfg['decision_interval_seconds'],freeze_source_time=cfg['forecast_history_freeze_utc'])
 policy=build_policy(cfg,costs,forecast)
 transitions=iter(r for r in events if r['kind']=='cohort_queue_transition')
 pending=next(transitions,None);states={};last=None;count=0
 for r in (r for r in events if r['kind']=='controller_decision'):
  frontier=r['decision_started']['monotonic_ns']
  while pending is not None and pending['actual_transition']['monotonic_ns']<=frontier:
   identity=pending['source']['source_query_id'];states[identity]=pending['state']
   if pending['state']=='offered':last=int(byid[identity]['query_id'])
   pending=next(transitions,None)
  queued=[row for row in mapping if states.get(row['source_query_id'])=='queued']
  require([row['source_query_id'] for row in queued]==r['decision']['queued_source_ids'],'Recorded controller backlog differs from actual past ledger')
  require(not any(s=='dispatched' for s in states.values()),'Controller called while serial query busy')
  reconstructed=policy.decide(elapsed_seconds=r['decision']['elapsed_seconds'],queued=queued,last_offered_query_id=last,files=cfg['initial_file_count'])
  require(reconstructed==r['decision'],'Past-only decision replay differs; no result-dependent repair permitted')
  count+=1
 return {'reconstructed_decisions':count,'raw_backlog_and_last_offered_reconstructed':True,'forecast_and_cost_model_replayed_without_refitting':True,'limitation':'Policy calculations replay their recorded implementation; core preparation separately reconstructs model/FIFO identities. This is not an independently invented cost model.'}

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'running','started_utc':now(),'protocol_sha256':sha(protocol),'code_sha256':sha(__file__),'model_accepted':False,'publication_novelty_established':False}
 try:
  semantics=json.loads(checked(cfg['model_semantics_audit']).read_text());require(semantics['status'] in ('failed_model_semantics_gate','passed_snapshot_pinned_whole_call_semantics','passed_real_source_snapshot_model_reconstruction_only'),'Unresolved model audit execution')
  cohort_path=checked(cfg['cohort_result']);cohort=json.loads(cohort_path.read_text())
  require(cohort['status']=='completed_full_physical_feasibility_pending_independent_comparison','Collection incomplete; do not infer comparisons from survivors')
  require(sha(cohort_path.parent/'registration.json')==cfg['physical_registration_sha256']==cohort['protocol_sha256'],'Physical registration hash differs')
  require(cohort['passed']==8 and cohort['failed']==0 and cohort['unattempted']==0,'Incomplete eight-arm cohort')
  manifest=json.loads((cohort_path.parent/'execution_manifest.json').read_text());require(len(manifest['all_episodes'])==8 and manifest['revision']==cohort['revision'],'Missing registered population/revision')
  physical_registration=json.loads((cohort_path.parent/'registration.json').read_text());version=physical_registration['episode_template'].get('policy_model_version','fluid_v1')
  if version=='fluid_v1':require(semantics.get('fluid_model_sha256')==manifest['code_sha256']['simulator.py'],'Legacy model audit not bound to frozen source')
  else:require(version=='snapshot_whole_call_v2' and semantics['status']=='passed_real_source_snapshot_model_reconstruction_only' and semantics['snapshot_simulator_sha256']==manifest['code_sha256']['snapshot_simulator.py'],'Snapshot audit not bound to frozen source')
  rows=[];matched={}
  for item in manifest['all_episodes']:
   checked(item['protocol']);d=cohort_path.parent/'episodes'/item['experiment_id'];saved=json.loads((d/'result.json').read_text());attempt=next(a for a in cohort['attempts'] if a['experiment_id']==item['experiment_id'])
   require(sha(d/'result.json')==attempt['result_sha256'],'Changed terminal result')
   actual=audit(d);actual['revision']=cohort['revision'];require(actual==saved,'Independent raw reconstruction differs from saved outcome')
   decision=reconstruct_decisions(d);ecfg=json.loads((d/'config.json').read_text());key=item['window_index']
   signature={'mapping_sha256':sha(d/'mapped_arrivals.csv'),'initial_layout_signature':actual['initial_layout_signature'],'source_receipt_sha256':sha(d/'preparation_result.json'),'model':ecfg['model'],'horizon_seconds':ecfg['horizon_seconds'],'arrivals':actual['arrival_count']}
   if key in matched:require(signature==matched[key],'Policies do not have matched arrivals/layout/data/model')
   else:matched[key]=signature
   row={k:v for k,v in actual.items() if k!='queries'};row.update(window_index=key,decision_reconstruction=decision,result_sha256=sha(d/'result.json'));rows.append(row)
   write_json(out/(item['experiment_id']+'.reconstruction.json'),row)
  comparisons=[]
  for window in sorted(matched):
   group={r['policy']:r for r in rows if r['window_index']==window};require(set(group)=={'queue_aware','forecast_quiet','immediate','no_maintenance'},'Missing comparator')
   for baseline in ['no_maintenance','immediate','forecast_quiet']:
    a=group['queue_aware'];b=group[baseline];comparisons.append({'window_index':window,'baseline':baseline,'queue_aware_sum_response_ns':a['sum_response_ns'],'baseline_sum_response_ns':b['sum_response_ns'],'difference_ns_queue_aware_minus_baseline':a['sum_response_ns']-b['sum_response_ns'],'fraction_reduction':1-a['sum_response_ns']/b['sum_response_ns'],'interpretation':'Observed matched-run contrast, not a causal estimate or independent-day significance test.'})
  report.update(status='audited_physical_candidate_model_semantics_failed' if semantics['status']=='failed_model_semantics_gate' else 'passed_complete_physical_and_raw_reconstruction_feasibility',model_semantics_status=semantics['status'],repaired_model_physically_validated=version=='snapshot_whole_call_v2',goal_completion_proven=False,episodes=rows,comparisons=comparisons,limitations=['Two contiguous windows from one source day; no independent-day calibration, confidence intervals or publication-level generalization.','Four benchmark SQL templates mapped to real Snowset arrival times; no original Snowflake SQL.','Single-client SF1 static16-file table, no ingestion; rewrite allowance at most one.','Service costs conditional on observed client backlog are observational, not causal interference labels.','Shared server and fixed rotated order cannot eliminate timing drift.','No policy performance or novelty conclusion follows merely from completing this audit.'])
  lines=['# Queue-aware physical feasibility results','','All eight registered arms completed and were reconstructed from raw evidence. Costs and decisions were not refitted from these outcomes. Model semantics status: '+semantics['status']+'. Physical implementation version: '+version+'. Calibration and general superiority remain unproven.','','| Window | Policy | Queries | Mean response (s) | Drain (s) | Rewrites |','|---|---|---:|---:|---:|---:|']
  for r in rows:lines.append(f"| {r['window_index']} | {r['policy']} | {r['completed']} | {r['mean_response_seconds']:.3f} | {r['drain_end_after_start_seconds']:.3f} | {r['maintenance_count']} |")
  lines+=['','Observed queue-aware contrasts (positive reduction means lower total response time):']
  for r in comparisons:lines.append(f"- Window {r['window_index']} versus {r['baseline']}: {100*r['fraction_reduction']:.3f}% reduction.")
  lines+=['','These are feasibility observations. They do not establish calibration, general superiority, causal effects or publication novelty.','']+['- '+x for x in report['limitations']]
  (out/'feasibility_report.md').write_text('\n'.join(lines)+'\n')
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:report['ended_utc']=now();write_json(out/'result.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('episodes','comparisons')}),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
