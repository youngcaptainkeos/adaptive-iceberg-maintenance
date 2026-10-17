import csv,json,hashlib,math
from pathlib import Path
p=Path('/mnt/nfs-storage/shashank_prafullathta/implementation/results/consistent_cost_development_20261017');r=json.loads((p/'result.json').read_text());d=p.parent/'consistent_collection_20261016'/'candidates'
def rows(x):
 with x.open() as f:return list(csv.DictReader(f))
for n,h in r['artifact_sha256'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h
raw={task:{(x['experiment_id'],x['measurement_id']):float(x[target]) for x in rows(d/name)} for task,name,target in [('query','queries.csv','service_target_ms'),('rewrite','rewrites.csv','rewrite_service_target_ms')]}
e=rows(d/'episodes.csv');families=sorted({x['source_interval_start_utc'] for x in e});validation={x['experiment_id'] for x in e if x['source_interval_start_utc']==families[1]}
pr=rows(p/'validation_predictions.csv');seen=set()
for x in pr:
 k=(x['task'],x['model'],x['experiment_id'],x['measurement_id']);assert k not in seen;seen.add(k)
 assert x['experiment_id'] in validation
 assert float(x['actual_ms'])==raw[x['task']][(x['experiment_id'],x['measurement_id'])]
for task,tr in r['results'].items():
 for model,metrics in tr['metrics'].items():
  subset=[x for x in pr if x['task']==task and x['model']==model];assert len(subset)==tr['validation_rows']
  errors=[abs(float(x['actual_ms'])-float(x['predicted_ms'])) for x in subset]
  assert math.isclose(sum(errors)/len(errors),metrics['row_mae_ms'],rel_tol=1e-12)
  em=[sum(abs(float(x['actual_ms'])-float(x['predicted_ms'])) for x in subset if x['experiment_id']==ep)/sum(x['experiment_id']==ep for x in subset) for ep in tr['validation_episodes']]
  assert math.isclose(sum(em)/len(em),metrics['equal_episode_mae_ms'],rel_tol=1e-12)
report={'status':'saved_prediction_targets_and_metrics_verified','predictions':len(pr),'reserved_test_predictions':0,'fit_receipt_sha256':hashlib.sha256((p/'result.json').read_bytes()).hexdigest(),'limitations':'Does not independently reconstruct model fitting/transforms; no calibration or model acceptance.'}
(p/'saved_prediction_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
