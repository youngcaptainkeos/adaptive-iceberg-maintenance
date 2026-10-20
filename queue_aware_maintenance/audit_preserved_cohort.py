#!/usr/bin/env python3
"""Audit incomplete collection without enabling survivor policy comparisons."""
import argparse, hashlib, json, sys
from pathlib import Path
from datetime import datetime, timezone

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--cohort',required=True);p.add_argument('--runtime',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 root=Path(a.cohort).resolve();runtime=Path(a.runtime).resolve();out=Path(a.output);out.mkdir(exist_ok=False,parents=True)
 report={'status':'running','started_utc':datetime.now(timezone.utc).isoformat(),'auditor_sha256':sha(Path(__file__)),'cohort_result_sha256':sha(root/'result.json'),'policy_comparisons_permitted':False,'model_or_novelty_claim_accepted':False,'episodes':[]}
 try:
  cohort=json.loads((root/'result.json').read_text());manifest=json.loads((root/'execution_manifest.json').read_text())
  assert sha(root/'registration.json')==cohort['protocol_sha256'],'Registration changed'
  for n,h in cohort['code_sha256'].items(): assert sha(runtime/'queue_aware_maintenance'/n)==h, f'Frozen code changed: {n}'
  sys.path.insert(0,str(runtime/'queue_aware_maintenance'))
  from audit_episode import audit
  from compare_study import reconstruct_decisions
  signatures={};total=0
  for item in cohort['attempts']:
   assert item['status']=='passed_complete_physical_and_raw_audit','Unexpected non-passing attempt; preserve and inspect'
   d=root/'episodes'/item['experiment_id'];saved=json.loads((d/'result.json').read_text())
   assert sha(d/'result.json')==item['result_sha256'],'Terminal result changed'
   actual=audit(d);actual['revision']=cohort['revision'];assert actual==saved,'Raw reconstruction differs'
   decisions=reconstruct_decisions(d)
   cfg=json.loads((d/'config.json').read_text());signature={'mapping':sha(d/'mapped_arrivals.csv'),'layout':actual['initial_layout_signature'],'source':sha(d/'preparation_result.json'),'model':cfg['model'],'horizon':cfg['horizon_seconds']}
   wi=item['window_index']
   if wi in signatures: assert signatures[wi]==signature,'Within-window matching differs'
   else: signatures[wi]=signature
   row={k:v for k,v in actual.items() if k!='queries'};row.update(window_index=wi,decision_reconstruction=decisions,result_sha256=sha(d/'result.json'))
   (out/(item['experiment_id']+'.json')).write_text(json.dumps(row,indent=2)+'\n');report['episodes'].append(row);total+=actual['completed']
   print(item['experiment_id']+' reconstructed',flush=True)
  attempted={x['experiment_id'] for x in cohort['attempts']};missing=[x for x in manifest['all_episodes'] if x['experiment_id'] not in attempted]
  assert len(missing)==cohort['unattempted'] and len(cohort['attempts'])==cohort['passed'] and cohort['failed']==0,'Inventory differs'
  report.update(status='passed_preserved_incomplete_cohort_raw_audit',passed=cohort['passed'],failed=cohort['failed'],unattempted=cohort['unattempted'],completed_queries=total,missing_episodes=missing,collection_error=cohort.get('error'),limitations=['Incomplete preregistered eight-arm study; no survivor policy comparisons.','Policy replay uses the frozen implementation, not an independent mathematical implementation.','Two adjacent source windows in one day; no independent-day generalization.','Serial client, static SF1 data, four mapped SQL templates; client/observer overhead is included in waiting.'])
  files=[]
  for f in sorted(root.rglob('*')):
   if f.is_file(): files.append({'path':str(f.relative_to(root)),'bytes':f.stat().st_size,'sha256':sha(f)})
  (out/'cohort_files_sha256.json').write_text(json.dumps(files,indent=2)+'\n')
 except Exception as e:
  report.update(status='failed_preserved',error=str(e));raise
 finally:
  report['ended_utc']=datetime.now(timezone.utc).isoformat();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
