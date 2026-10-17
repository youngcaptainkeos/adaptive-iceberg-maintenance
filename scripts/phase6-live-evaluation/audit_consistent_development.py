#!/usr/bin/env python3
"""Independent reconstruction of actual development fit; never evaluates reserved family."""
import argparse,csv,json,math,hashlib,traceback
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))

def run(protocol):
 import numpy as np,joblib
 from sklearn.tree import DecisionTreeRegressor
 cfg=json.loads(protocol.read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 result={'status':'running','reserved_test_evaluated':False,'checks':[],'coverage':{}}
 try:
  for spec in cfg['inputs']:require(digest(spec['path'])==spec['sha256'],'Registered input changed '+spec['path'])
  fitdir=Path(cfg['fit_directory']);fit=json.loads((fitdir/'result.json').read_text());registration=json.loads(Path(cfg['fit_protocol']).read_text());data=Path(registration['export_directory']);manifest=json.loads((data/'export_record.json').read_text())
  require(digest(data/'export_record.json')==registration['export_record_sha256'],'Corpus manifest changed')
  for name,h in manifest['artifact_sha256'].items():require(digest(data/name)==h,'Corpus artifact changed '+name)
  for name,h in fit['artifact_sha256'].items():require(digest(fitdir/name)==h,'Fit artifact changed '+name)
  model=joblib.load(fitdir/'development_models.joblib');episodes=rows(data/'episodes.csv');intervals=sorted({(e['source_interval_start_utc'],e['source_interval_end_utc']) for e in episodes});require(len(intervals)==3,'Family count')
  require(all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:])),'Source overlap')
  family={e['experiment_id']:intervals.index((e['source_interval_start_utc'],e['source_interval_end_utc'])) for e in episodes}
  saved=rows(fitdir/'validation_predictions.csv');require(len({(p['task'],p['model'],p['measurement_id']) for p in saved})==len(saved),'Duplicate predictions')
  excluded=[]
  for task,name,target in [('query','queries.csv','service_target_ms'),('rewrite','rewrites.csv','rewrite_service_target_ms')]:
   raw=rows(data/name);splits=[[],[]];coverage={}
   for i in (0,1):
    allrows=[r for r in raw if family[r['experiment_id']]==i];eligible=[]
    for r in allrows:
     require((r['source_interval_start_utc'],r['source_interval_end_utc'])==intervals[i],'Row family binding differs')
     if task=='query' and any(r['offered_history_complete_'+w]!='True' for w in ('60s','300s')):
      excluded.append((r['experiment_id'],r['measurement_id']));continue
     eligible.append(r)
    splits[i]=eligible
    coverage[str(i)]={'all_rows':len(allrows),'eligible_rows':len(eligible),'excluded_rows':len(allrows)-len(eligible),'slices':{}}
    fields=['query_id','file_count','maintenance_client_pending_at_feature_time'] if task=='query' else ['file_count']
    for f in fields:
     values=sorted({r[f] for r in allrows}|({'True','False'} if 'pending' in f else set()))
     coverage[str(i)]['slices'][f]={v:{'all_rows':sum(r[f]==v for r in allrows),'eligible_rows':sum(r[f]==v for r in eligible)} for v in values}
   train,valid=splits;require(len(train)==fit['results'][task]['training_rows'] and len(valid)==fit['results'][task]['validation_rows'],'Eligibility differs')
   features=['query_id','file_count','maintenance_client_pending_at_feature_time'] if task=='query' else ['file_count']
   def matrix(rs):return np.array([[float(r[f]=='True') if 'pending' in f else float(r[f]) for f in features] for r in rs])
   x,z=matrix(train),matrix(valid);y=np.array([float(r[target]) for r in train]);truth=np.array([float(r[target]) for r in valid]);ridge=model[task+'_log_ridge'];transform=ridge.steps[0][1]
   if task=='query':
    categories=np.unique(x[:,0]);onehot=(x[:,0,None]==categories).astype(float);onehot_valid=(z[:,0,None]==categories).astype(float)
    require(all(q in categories for q in z[:,0]),'Unsupported SQL')
    numeric=x[:,1:];numeric_valid=z[:,1:];scaler=transform.named_transformers_['numeric'];encoder=transform.named_transformers_['query'];require(np.array_equal(encoder.categories_[0],categories),'Encoding not training-only')
   else:numeric=x;numeric_valid=z;scaler=transform
   mean=numeric.mean(axis=0);variance=numeric.var(axis=0);scale=np.sqrt(variance);scale[scale==0]=1
   require(np.allclose(scaler.mean_,mean,rtol=1e-12,atol=1e-12) and np.allclose(scaler.var_,variance,rtol=1e-12,atol=1e-12),'Training-only scaler differs')
   a=(numeric-mean)/scale;b=(numeric_valid-mean)/scale
   if task=='query':a=np.column_stack((onehot,a));b=np.column_stack((onehot_valid,b))
   require(np.allclose(transform.transform(x),a),'Saved transform differs from independent design')
   center=a.mean(axis=0);ac=a-center;ly=np.log(y);coef=np.linalg.solve(ac.T@ac+registration['ridge_alpha']*np.eye(a.shape[1]),ac.T@(ly-ly.mean()));intercept=ly.mean()-center@coef
   require(np.allclose(ridge.steps[-1][1].coef_,coef,rtol=1e-8,atol=1e-8),'Ridge not reconstructed from training log targets')
   predicted={'log_ridge':np.exp(b@coef+intercept)}
   t=DecisionTreeRegressor(max_depth=3,criterion='absolute_error',random_state=20261015).fit(x,y);stored=model[task+'_shallow_tree'];require(stored.max_depth==3 and stored.criterion=='absolute_error' and stored.random_state==20261015,'Tree parameters differ');require(np.allclose(t.predict(z),stored.predict(z)),'Tree training reconstruction differs');predicted['shallow_tree']=t.predict(z)
   if task=='query':
    byq={q:float(np.median([float(r[target]) for r in train if r['query_id']==q])) for q in {r['query_id'] for r in train}};buckets={(r['query_id'],r['file_count']) for r in train};byql={k:float(np.median([float(r[target]) for r in train if (r['query_id'],r['file_count'])==k])) for k in buckets};require(model['query_empirical']=={'query':byq,'query_layout':byql},'Empirical model differs')
    predicted['query_median']=np.array([byq[r['query_id']] for r in valid]);predicted['query_layout_median']=np.array([byql.get((r['query_id'],r['file_count']),byq[r['query_id']]) for r in valid]);require(sum((r['query_id'],r['file_count']) not in byql for r in valid)==fit['results'][task]['fallback_counts']['query_layout_median'],'Fallback counts differ')
   else:require(model['rewrite_empirical']==float(np.median(y)),'Rewrite median differs');predicted['training_median']=np.full(len(valid),np.median(y))
   for name,values in predicted.items():
    ss=[r for r in saved if r['task']==task and r['model']==name];require(len(ss)==len(valid),'Prediction coverage differs')
    for s,r,v,target_value in zip(ss,valid,values,truth):require(s['experiment_id']==r['experiment_id'] and s['measurement_id']==r['measurement_id'] and float(s['actual_ms'])==target_value and math.isclose(float(s['predicted_ms']),v,rel_tol=1e-8,abs_tol=1e-8),'Raw target/model prediction differs')
    errors=np.abs(values-truth);per=[float(np.mean(errors[[r['experiment_id']==e for r in valid]])) for e in sorted({r['experiment_id'] for r in valid})];m=fit['results'][task]['metrics'][name];require(math.isclose(float(errors.mean()),m['row_mae_ms'],rel_tol=1e-8) and math.isclose(float(np.mean(per)),m['equal_episode_mae_ms'],rel_tol=1e-8),'Metric reconstruction differs')
   result['coverage'][task]=coverage;result['checks'].append(task+'_training_transforms_models_targets_predictions_metrics_reconstructed')
  require(set(excluded)=={(r['experiment_id'],r['measurement_id']) for r in fit['excluded_queries']} and len(excluded)==len(fit['excluded_queries']),'Excluded eligibility inventory differs')
  require(all(family[r['experiment_id']]==1 for r in saved),'Reserved family prediction leakage')
  result.update(status='passed_independent_development_reconstruction',prediction_rows=len(saved),excluded_development_queries=len(excluded),limitations=['One train and one validation family; no calibration or causal/scheduler acceptance.','Tree reconstruction uses same sklearn implementation with independently rebuilt training rows.','Zero complete-history pending support prevents assessing that regime with these eligible rows.'])
 except Exception as e:result.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc());raise
 finally:
  result['protocol_sha256']=digest(protocol);result['audit_code_sha256']=digest(__file__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);run(p.parse_args().protocol)
