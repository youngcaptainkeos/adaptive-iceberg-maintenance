#!/usr/bin/env python3
"""Require all registered repeats, reconstruct raw evidence, report all contrasts."""
import argparse,json,hashlib
from pathlib import Path
from common import require,sha,write_json,now
from audit_episode import audit
from compare_study import reconstruct_decisions
from run_timing_study import timing_details

def run(study,output):
 root=Path(study);out=Path(output);out.mkdir(exist_ok=False,parents=True);report={'status':'running','started_utc':now(),'code_sha256':sha(__file__),'calibration_accepted':False,'novelty_accepted':False,'general_superiority_accepted':False}
 try:
  registration=json.loads((root/'registration.json').read_text());manifest=json.loads((root/'manifest.json').read_text());progress_bytes=(root/'progress.json').read_bytes();progress=json.loads(progress_bytes);(out/'source_progress.json').write_bytes(progress_bytes);report['source_progress_sha256']=hashlib.sha256(progress_bytes).hexdigest()
  require(sha(root/'registration.json')==manifest['protocol_sha256']==progress['protocol_sha256'],'Changed study registration')
  require(progress['passed']==len(manifest['episodes'])==8 and progress['failed']==progress['unattempted']==0,'Incomplete study; no survivor comparison')
  require(len({x['experiment_id'] for x in manifest['episodes']})==8,'Duplicate physical episode')
  rows=[];signature=None
  for item in manifest['episodes']:
   p=Path(item['protocol']['path']);require(sha(p)==item['protocol']['sha256'],'Changed episode protocol');d=root/'episodes'/item['experiment_id'];attempt=next(a for a in progress['attempts'] if a['experiment_id']==item['experiment_id']);require(attempt['status']=='passed' and sha(d/'result.json')==attempt['result_sha256'],'Changed physical result')
   saved=json.loads((d/'result.json').read_text());actual=audit(d);actual['revision']=manifest['runtime_revision'];require(actual==saved,'Full raw reconstruction differs');replay=reconstruct_decisions(d)
   ecfg=json.loads((d/'config.json').read_text());declared=next(a for a in registration['actions'] if a['name']==item['action']);require(ecfg['policy']==declared['policy'],'Wrong registered intervention');
   if declared['policy']=='fixed_start':require(ecfg['fixed_start_seconds']==declared['seconds'],'Wrong registered delay')
   details=timing_details(d);require(details['actual_rewrite_start_after_arrival_clock_seconds']==attempt['actual_rewrite_start_after_arrival_clock_seconds'],'Actual rewrite timing metadata differs')
   current={'mapping_sha256':sha(d/'mapped_arrivals.csv'),'source_sha256':sha(d/'preparation_result.json'),'layout':actual['initial_layout_signature'],'model':ecfg['model'],'horizon':ecfg['horizon_seconds']}
   if signature is None:signature=current
   else:require(signature==current,'Matched source/layout/model conditions differ')
   row={k:v for k,v in actual.items() if k!='queries'};row.update(action=item['action'],repeat=item['repeat'],decision_reconstruction=replay,actual_rewrite_start_after_arrival_clock_seconds=attempt['actual_rewrite_start_after_arrival_clock_seconds']);rows.append(row);write_json(out/(item['experiment_id']+'.json'),row)
  contrasts=[]
  for repeat in range(2):
   group={r['action']:r for r in rows if r['repeat']==repeat};require(set(group)=={a['name'] for a in registration['actions']},'Missing registered action in repeat');base=group['start_0']
   for name in ('start_60','start_600','no_action'):
    other=group[name];contrasts.append({'repeat':repeat,'action':name,'sum_response_difference_ns_vs_immediate':other['sum_response_ns']-base['sum_response_ns'],'fraction_lower_response':1-other['sum_response_ns']/base['sum_response_ns'],'meaning':'Observed repeated-development contrast, not an independent-day confidence/causal estimate.'})
  consistent=[name for name in ('start_60','start_600') if all(c['sum_response_difference_ns_vs_immediate']<0 for c in contrasts if c['action']==name)]
  report.update(status='passed_complete_repeated_development_raw_comparison',episodes=rows,contrasts=contrasts,delayed_actions_lower_both_repeats=consistent,limitations=['Only two repeats of one known development arrival window. No untouched-family performance test.','Forward/reverse ordering balances early/late placement but cannot eliminate cache/time drift or supply statistical power.','Fixed start means first controller opportunity at/after requested seconds; actual SQL start lag is reported.','Null control finishes with different layout; conclusions apply to this offered cohort through drain, not unobserved future work.','Single-client static SF1/four-template setup; instrumentation remains part of observed response time.','No fitting, selection of best retry, causal interference calibration, generalization or novelty accepted.'])
  lines=['# Repeated physical timing experiment','','All8registered arms passed full raw reconstruction. This is development headroom evidence only.','','| Repeat | Intervention | Queries | Mean response(s) | Drain(s) | Actual rewrite start(s) |','|---|---|---:|---:|---:|---:|']
  for r in rows:lines.append(f"| {r['repeat']} | {r['action']} | {r['completed']} | {r['mean_response_seconds']:.3f} | {r['drain_end_after_start_seconds']:.3f} | {r['actual_rewrite_start_after_arrival_clock_seconds']} |")
  lines+=['','## All observed contrasts (positive percent means lower response than immediate)']
  for c in contrasts:lines.append(f"- Repeat{c['repeat']} {c['action']}: {100*c['fraction_lower_response']:.4f}% lower response.")
  lines+=['','Delayed interventions with lower summed response in both repeats: '+str(consistent)+'. This is a descriptive consistency flag, not statistical significance.','','## Interpretation and next gate','If no delayed action consistently lowers response, this setup has not established a delayed-maintenance benefit. If one does, repeat on untouched source-day blocks with stronger baselines before claiming general benefit. Do not tune on these outcomes and keep calling this a test set.','','## Implementation explained','See queue_aware_maintenance/IMPLEMENTATION_WALKTHROUGH_2026-10-21.md for the files, functions, data flow and why each gate exists. The experiment controlled start time; no new prediction model was trained.','']+['- '+x for x in report['limitations']]
  (out/'report.md').write_text('\n'.join(lines)+'\n')
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:report['ended_utc']=now();write_json(out/'result.json',report)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--study',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.study,a.output)
