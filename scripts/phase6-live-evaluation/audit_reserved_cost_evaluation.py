#!/usr/bin/env python3
"""Read-only independent checks of frozen test predictions and raw target binding."""
import argparse,csv,json,hashlib,math
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
def check(b,m):
 if not b:raise ValueError(m)
def run(protocol):
 import numpy as np,joblib
 cfg=json.loads(protocol.read_text());d=Path(cfg['evaluation_directory']);out=Path(cfg['output']);check(not out.exists(),'Audit output already exists')
 for s in cfg['inputs']:check(sha(s['path'])==s['sha256'],'Changed audit input')
 r=json.loads((d/'result.json').read_text());reg=json.loads((d/'registration.json').read_text());check(sha(d/'registration.json')==r['protocol_sha256'],'Evaluation registration differs')
 for s in reg['inputs']:check(sha(s['path'])==s['sha256'],'Frozen evaluation input changed')
 for n,h in r['artifact_sha256'].items():check(sha(d/n)==h,'Evaluation artifact changed '+n)
 data=Path(reg['export_directory']);models=joblib.load(Path(reg['fit_directory'])/'development_models.joblib');manifest=json.loads((data/'export_record.json').read_text())
 for n,h in manifest['artifact_sha256'].items():check(sha(data/n)==h,'Corpus artifact changed')
 ep=rows(data/'episodes.csv');intervals=sorted({(e['source_interval_start_utc'],e['source_interval_end_utc']) for e in ep});family={e['experiment_id']:intervals.index((e['source_interval_start_utc'],e['source_interval_end_utc'])) for e in ep}
 predictions=rows(d/'test_predictions.csv');check(len({(x['task'],x['model'],x['measurement_id']) for x in predictions})==len(predictions),'Duplicate predictions');check(all(family[x['experiment_id']]==2 for x in predictions),'Wrong test family')
 exclusions=[]
 for task,name,target,features in [('query','queries.csv','service_target_ms',['query_id','file_count','maintenance_client_pending_at_feature_time']),('rewrite','rewrites.csv','rewrite_service_target_ms',['file_count'])]:
  raw=rows(data/name);eligible=lambda x:task!='query' or all(x['offered_history_complete_'+w]=='True' for w in ('60s','300s'))
  train=[x for x in raw if family[x['experiment_id']]==0 and eligible(x)];test=[x for x in raw if family[x['experiment_id']]==2 and eligible(x)];exclusions.extend((x['experiment_id'],x['measurement_id']) for x in raw if task=='query' and family[x['experiment_id']]==2 and not eligible(x))
  x=np.array([[float(v[f]=='True') if 'pending' in f else float(v[f]) for f in features] for v in test]);truth=np.array([float(v[target]) for v in test]);expected={}
  if task=='query':
   med={q:float(np.median([float(v[target]) for v in train if v['query_id']==q])) for q in {v['query_id'] for v in train}};keys={(v['query_id'],v['file_count']) for v in train};ql={k:float(np.median([float(v[target]) for v in train if (v['query_id'],v['file_count'])==k])) for k in keys};expected['query_median']=np.array([med[v['query_id']] for v in test]);expected['query_layout_median']=np.array([ql.get((v['query_id'],v['file_count']),med[v['query_id']]) for v in test]);check(r['results'][task]['fallback_counts']['query_layout_median']==sum((v['query_id'],v['file_count']) not in ql for v in test),'Fallback count')
  else:expected['training_median']=np.full(len(test),np.median([float(v[target]) for v in train]))
  ridge=models[task+'_log_ridge'];transformed=ridge.steps[0][1].transform(x);expected['log_ridge']=np.exp(transformed@ridge.steps[-1][1].coef_+ridge.steps[-1][1].intercept_);expected['shallow_tree']=models[task+'_shallow_tree'].predict(x)
  for model,values in expected.items():
   subset=[v for v in predictions if v['task']==task and v['model']==model];check(len(subset)==len(test)==r['results'][task]['eligible_test_rows'],'Test coverage differs')
   for s,v,t,p in zip(subset,test,truth,values):check((s['experiment_id'],s['measurement_id'])==(v['experiment_id'],v['measurement_id']) and float(s['actual_ms'])==t and math.isclose(float(s['predicted_ms']),p,rel_tol=1e-10,abs_tol=1e-10),'Frozen prediction/raw target differs')
   err=np.abs(values-truth);metrics=r['results'][task]['metrics'][model];per={e:float(np.mean(err[[v['experiment_id']==e for v in test]])) for e in {v['experiment_id'] for v in test}}
   check(math.isclose(float(err.mean()),metrics['row_mae_ms'],rel_tol=1e-10) and math.isclose(float(np.mean(list(per.values()))),metrics['equal_episode_mae_ms'],rel_tol=1e-10),'Metric differs')
   for field,sl in metrics['slices'].items():
    for value,metric in sl.items():check(metric['rows']==sum(v[field]==value for v in test) and metric['training_support_rows']==sum(v[field]==value for v in train) and math.isclose(metric['mae_ms'],float(np.mean(err[[v[field]==value for v in test]])),rel_tol=1e-10),'Slice differs')
 check(set(exclusions)=={(x['experiment_id'],x['measurement_id']) for x in r['excluded_test_queries']} and len(exclusions)==len(r['excluded_test_queries']),'Exclusion inventory differs')
 report={'status':'passed_raw_targets_frozen_predictions_and_metrics_audit','prediction_rows':len(predictions),'excluded_test_queries':len(exclusions),'test_refit':False,'evaluation_receipt_sha256':sha(d/'result.json'),'audit_code_sha256':sha(__file__),'protocol_sha256':sha(protocol),'limitations':['Read-only frozen-model reconstruction, no new fitting or independent calibration.']};out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);run(p.parse_args().protocol)
