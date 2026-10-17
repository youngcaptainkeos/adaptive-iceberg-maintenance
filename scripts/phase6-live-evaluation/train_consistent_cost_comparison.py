#!/usr/bin/env python3
"""Development-only real cost comparison; reserved family never evaluated."""
import argparse,csv,json,math,hashlib,traceback
from pathlib import Path
from datetime import datetime,timezone

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):
 with Path(p).open() as f:return list(csv.DictReader(f))
def num(x):
 v=float(x);need(math.isfinite(v),'Nonfinite number');return v

def run(path):
 import numpy as np,joblib,sklearn
 from sklearn.compose import ColumnTransformer
 from sklearn.preprocessing import OneHotEncoder,StandardScaler
 from sklearn.pipeline import make_pipeline
 from sklearn.linear_model import Ridge
 from sklearn.tree import DecisionTreeRegressor
 cfg=json.loads(path.read_text());need(cfg['schema_version']=='consistent_cost_development_v1','Unknown protocol')
 need(cfg['ridge_alpha']==1.0 and cfg['tree_max_depth']==3 and cfg['seed']==20261015,'Registered candidate parameters differ')
 out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'running','started_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(path),'code_sha256':sha(__file__),'test_family_evaluated':False,'model_accepted':False,'scheduler_authorized':False,'results':{}}
 try:
  d=Path(cfg['export_directory']);need(sha(d/'export_record.json')==cfg['export_record_sha256'],'Export changed')
  manifest=json.loads((d/'export_record.json').read_text());v=Path(cfg['verification']['path']);need(sha(v)==cfg['verification']['sha256'],'Verification changed')
  vr=json.loads(v.read_text());need(vr['status']=='verified_candidate_csv_raw_roundtrip_only' and vr['export_record_sha256']==cfg['export_record_sha256'],'Unverified corpus')
  for n,h in manifest['artifact_sha256'].items():need(sha(d/n)==h,'Artifact changed '+n)
  episodes=read(d/'episodes.csv');intervals=sorted({(e['source_interval_start_utc'],e['source_interval_end_utc']) for e in episodes})
  need(len(intervals)==3,'Three registered families required')
  for a,b in zip(intervals,intervals[1:]):need(datetime.fromisoformat(a[1])<=datetime.fromisoformat(b[0]),'Source overlap')
  family={e['experiment_id']:intervals.index((e['source_interval_start_utc'],e['source_interval_end_utc'])) for e in episodes}
  need(cfg['train_family_index']==0 and cfg['validation_family_index']==1 and cfg['reserved_test_family_index']==2,'Chronological development split required')
  report['source_intervals']=intervals;report['sklearn_version']=sklearn.__version__;report['excluded_queries']=[]
  predictions=[];models={}
  for task,filename,target,features in [('query','queries.csv','service_target_ms',['query_id','file_count','maintenance_client_pending_at_feature_time']),('rewrite','rewrites.csv','rewrite_service_target_ms',['file_count'])]:
   rows=read(d/filename);train=[];valid=[];reserved=0
   for r in rows:
    fi=family[r['experiment_id']]
    if fi==2:reserved+=1;continue # No test targets/predictors consumed by fitting or evaluation.
    if task=='query' and any(r['offered_history_complete_'+w]!='True' for w in ('60s','300s')):
     report['excluded_queries'].append({'experiment_id':r['experiment_id'],'measurement_id':r['measurement_id'],'reason':'incomplete_real_offered_history'});continue
    need(num(r[target])>0,'Positive measured target required')
    (train if fi==0 else valid).append(r)
   need(train and valid,'Missing development labels')
   def matrix(rs):return np.asarray([[float(r[f]=='True') if f=='maintenance_client_pending_at_feature_time' else num(r[f]) for f in features] for r in rs],dtype=float)
   x,z=matrix(train),matrix(valid);y=np.asarray([num(r[target]) for r in train]);truth=np.asarray([num(r[target]) for r in valid])
   estimates={};fallbacks={}
   if task=='query':
    byq={q:float(np.median([num(r[target]) for r in train if r['query_id']==q])) for q in {r['query_id'] for r in train}}
    need(all(r['query_id'] in byq for r in valid),'Unsupported validation SQL identity')
    buckets={(r['query_id'],r['file_count']) for r in train};byql={k:float(np.median([num(r[target]) for r in train if (r['query_id'],r['file_count'])==k])) for k in buckets}
    estimates['query_median']=np.asarray([byq[r['query_id']] for r in valid]);estimates['query_layout_median']=np.asarray([byql.get((r['query_id'],r['file_count']),byq[r['query_id']]) for r in valid]);fallbacks['query_layout_median']=sum((r['query_id'],r['file_count']) not in byql for r in valid)
    pre=ColumnTransformer([('query',OneHotEncoder(handle_unknown='error',sparse_output=False),[0]),('numeric',StandardScaler(),[1,2])])
    models['query_empirical']={'query':byq,'query_layout':byql}
   else:
    estimates['training_median']=np.full(len(valid),float(np.median(y)));pre=StandardScaler();models['rewrite_empirical']=float(np.median(y))
   ridge=make_pipeline(pre,Ridge(alpha=cfg['ridge_alpha']));ridge.fit(x,np.log(y));estimates['log_ridge']=np.exp(ridge.predict(z));models[task+'_log_ridge']=ridge
   tree=DecisionTreeRegressor(max_depth=cfg['tree_max_depth'],criterion='absolute_error',random_state=cfg['seed']);tree.fit(x,y);estimates['shallow_tree']=tree.predict(z);models[task+'_shallow_tree']=tree
   result={'training_rows':len(train),'validation_rows':len(valid),'reserved_test_rows_not_evaluated':reserved,'training_episodes':sorted({r['experiment_id'] for r in train}),'validation_episodes':sorted({r['experiment_id'] for r in valid}),'features':features,'fallback_counts':fallbacks,'metrics':{}}
   for name,pred in estimates.items():
    need(np.isfinite(pred).all() and (pred>0).all(),'Nonpositive/nonfinite prediction; no clipping')
    err=np.abs(pred-truth);ep={e:float(np.mean(err[[r['experiment_id']==e for r in valid]])) for e in result['validation_episodes']}
    result['metrics'][name]={'row_mae_ms':float(np.mean(err)),'equal_episode_mae_ms':float(np.mean(list(ep.values()))),'per_episode_mae_ms':ep,'slices':{}}
    for field in (['query_id','file_count','maintenance_client_pending_at_feature_time'] if task=='query' else ['file_count']):
     result['metrics'][name]['slices'][field]={value:{'rows':sum(r[field]==value for r in valid),'mae_ms':float(np.mean(err[[r[field]==value for r in valid]])),'training_support_rows':sum(r[field]==value for r in train)} for value in sorted({r[field] for r in valid})}
    for r,t,p in zip(valid,truth,pred):predictions.append({'task':task,'model':name,'experiment_id':r['experiment_id'],'measurement_id':r['measurement_id'],'actual_ms':float(t),'predicted_ms':float(p)})
   report['results'][task]=result
  joblib.dump(models,out/'development_models.joblib')
  with (out/'validation_predictions.csv').open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(predictions[0]));w.writeheader();w.writerows(predictions)
  report['status']='completed_development_only_uncalibrated';report['limitations']=['Only one training and one validation source family; row counts are not independent replications.','Reserved third family not evaluated. No automatic winner/refit/test.','Full demand-history eligibility restricts latency comparison to later replay; pending regimes may have little or no support.','Log regression estimates geometric center; not an unbiased arithmetic mean.','Rewrite models have very few measured labels and cannot establish reliability.']
  report['artifact_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file()}
 except Exception as e:
  report.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc());raise
 finally:
  report['ended_utc']=datetime.now(timezone.utc).isoformat();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','results']}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);run(p.parse_args().protocol)
