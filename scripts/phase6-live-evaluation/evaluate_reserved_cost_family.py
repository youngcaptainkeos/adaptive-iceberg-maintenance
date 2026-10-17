#!/usr/bin/env python3
"""One-time frozen-model family evaluation; no fitting or model selection."""
import argparse,csv,json,math,hashlib,traceback,shutil
from pathlib import Path
from datetime import datetime,timezone

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,msg):
 if not ok:raise ValueError(msg)
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
def run(protocol):
 import numpy as np,joblib
 cfg=json.loads(protocol.read_text());need(cfg['schema_version']=='reserved_cost_family_evaluation_v1','Unknown protocol')
 out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'running','started_utc':datetime.now(timezone.utc).isoformat(),'test_family_evaluated':False,'refit_performed':False,'model_accepted':False,'scheduler_authorized':False,'primary_methods':cfg['primary_methods'],'results':{},'excluded_test_queries':[]}
 try:
  for spec in cfg['inputs']:need(sha(spec['path'])==spec['sha256'],'Frozen input changed '+spec['path'])
  need(sha(__file__)==cfg['evaluation_code_sha256'],'Evaluation code changed')
  audit=json.loads(Path(cfg['audit_receipt']).read_text());need(audit['status']=='passed_independent_development_reconstruction' and audit['reserved_test_evaluated'] is False,'Development audit gate failed')
  d=Path(cfg['export_directory']);fitdir=Path(cfg['fit_directory']);fit=json.loads((fitdir/'result.json').read_text());manifest=json.loads((d/'export_record.json').read_text())
  for name,h in manifest['artifact_sha256'].items():need(sha(d/name)==h,'Corpus changed '+name)
  for name,h in fit['artifact_sha256'].items():need(sha(fitdir/name)==h,'Frozen models/predictions changed '+name)
  need(fit['status']=='completed_development_only_uncalibrated' and fit['test_family_evaluated'] is False,'Fit gate differs')
  need(cfg['primary_methods']=={'query':'query_layout_median','rewrite':'training_median'} and cfg['test_family_index']==2,'Frozen primary/test assignment differs')
  shutil.copyfile(protocol,out/'registration.json');shutil.copyfile(__file__,out/'evaluation_code.py')
  models=joblib.load(fitdir/'development_models.joblib');episodes=rows(d/'episodes.csv');intervals=sorted({(r['source_interval_start_utc'],r['source_interval_end_utc']) for r in episodes});need(len(intervals)==3 and all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:])),'Family partition differs')
  family={r['experiment_id']:intervals.index((r['source_interval_start_utc'],r['source_interval_end_utc'])) for r in episodes};allpred=[]
  for task,filename,target,features in [('query','queries.csv','service_target_ms',['query_id','file_count','maintenance_client_pending_at_feature_time']),('rewrite','rewrites.csv','rewrite_service_target_ms',['file_count'])]:
   raw=rows(d/filename);train=[];test=[];offered_test=0
   for r in raw:
    fi=family[r['experiment_id']]
    if fi==1:continue
    if fi==2:offered_test+=1
    if task=='query' and any(r['offered_history_complete_'+w]!='True' for w in ('60s','300s')):
     if fi==2:report['excluded_test_queries'].append({'experiment_id':r['experiment_id'],'measurement_id':r['measurement_id'],'reason':'incomplete_real_offered_history'})
     continue
    (train if fi==0 else test).append(r)
   need(train and test,'Missing eligible rows')
   x=np.array([[float(r[f]=='True') if 'pending' in f else float(r[f]) for f in features] for r in test]);need(np.isfinite(x).all(),'Nonfinite test predictors')
   truth=np.array([float(r[target]) for r in test]);need(np.isfinite(truth).all() and (truth>0).all(),'Invalid measured test target')
   estimates={};fallbacks={}
   if task=='query':
    q=models['query_empirical']['query'];ql=models['query_empirical']['query_layout'];need(all(r['query_id'] in q for r in test),'Unseen SQL; no invented fallback')
    estimates['query_median']=np.array([q[r['query_id']] for r in test]);estimates['query_layout_median']=np.array([ql.get((r['query_id'],r['file_count']),q[r['query_id']]) for r in test]);fallbacks['query_layout_median']=sum((r['query_id'],r['file_count']) not in ql for r in test)
   else:estimates['training_median']=np.full(len(test),models['rewrite_empirical'])
   estimates['log_ridge']=np.exp(models[task+'_log_ridge'].predict(x));estimates['shallow_tree']=models[task+'_shallow_tree'].predict(x)
   metrics={};episode_ids=sorted({r['experiment_id'] for r in test})
   for name,pred in estimates.items():
    need(np.isfinite(pred).all() and (pred>0).all(),'Invalid prediction; no clipping')
    err=np.abs(pred-truth);per={e:float(np.mean(err[[r['experiment_id']==e for r in test]])) for e in episode_ids};metrics[name]={'row_mae_ms':float(np.mean(err)),'equal_episode_mae_ms':float(np.mean(list(per.values()))),'per_episode_mae_ms':per,'slices':{}}
    for f in features:
     metrics[name]['slices'][f]={v:{'rows':sum(r[f]==v for r in test),'training_support_rows':sum(r[f]==v for r in train),'mae_ms':float(np.mean(err[[r[f]==v for r in test]]))} for v in sorted({r[f] for r in test})}
    for r,t,v in zip(test,truth,pred):allpred.append({'task':task,'model':name,'experiment_id':r['experiment_id'],'measurement_id':r['measurement_id'],'actual_ms':float(t),'predicted_ms':float(v)})
   report['results'][task]={'all_test_rows':offered_test,'eligible_test_rows':len(test),'excluded_test_rows':offered_test-len(test),'test_episodes':episode_ids,'features':features,'fallback_counts':fallbacks,'metrics':metrics}
  with (out/'test_predictions.csv').open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(allpred[0]));w.writeheader();w.writerows(allpred)
  report.update(status='completed_single_reserved_family_evaluation_uncalibrated',test_family_evaluated=True,source_test_interval=intervals[2],limitations=['One reserved source family, dependent repeated layouts/actions, no independent calibration.','Full demand-history filter excludes early queries; cannot claim full-episode scheduler accuracy.','Only four test rewrites; no established compaction-model reliability.','No tuning, refit, automatic winner or scheduler deployment after this test.'])
  report['artifact_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file()}
 except Exception as e:report.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc());raise
 finally:
  report['ended_utc']=datetime.now(timezone.utc).isoformat();report['protocol_sha256']=sha(protocol);report['evaluation_code_sha256']=sha(__file__);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'test_family_evaluated':report['test_family_evaluated']}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);run(p.parse_args().protocol)
