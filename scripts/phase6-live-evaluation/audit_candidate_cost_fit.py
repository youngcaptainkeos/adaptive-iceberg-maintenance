#!/usr/bin/env python3
"""Read-only real candidate/persisted-model roundtrip; no refitting or promotion."""
import argparse,csv,json
from pathlib import Path
from experiment_validation import require,sha256

def number(value):
    return float(value=='True') if value in ('True','False') else float(value)

def audit(directory,export,output):
    import joblib,numpy as np
    record=json.loads((directory/'fit_record.json').read_text())
    cfg=json.loads((directory/'config.json').read_text())
    require(record['calibrated_training_accepted'] is False and record['scheduler_authorized'] is False,'Promoted bundle unsupported')
    for name,digest in record['artifact_sha256'].items():require(sha256(directory/name)==digest,'Fit artifact changed')
    require(sha256(export/'export_record.json')==record['export_record_sha256'],'Fit export changed')
    manifest=json.loads((export/'export_record.json').read_text())
    for name,digest in manifest['artifact_sha256'].items():require(sha256(export/name)==digest,'Candidate changed')
    def read(name):
        with (export/name).open() as f:return list(csv.DictReader(f))
    queries,rewrites=read('queries.csv'),read('rewrites.csv')
    state='maintenance_client_pending_at_feature_time'
    dropped=[r['measurement_id'] for r in queries if cfg['require_complete_demand_history'] and any(r[f'offered_history_complete_{s}s']!='True' for s in (60,300))]
    require(dropped==record['dropped_incomplete_history_measurements'],'Missing-history inventory differs')
    eligible=[r for r in queries if r['measurement_id'] not in set(dropped)]
    predictions=json.loads((directory/'heldout_predictions.json').read_text());models=joblib.load(directory/'exploratory_models.joblib')
    assignments=record['episode_family_assignment'];summaries={}
    require(set(models)=={n for n,m in record['models'].items() if m['status']=='exploratory_fit_only'},'Model inventory differs')
    seen=set()
    for name,model in models.items():
        rows=rewrites if name=='rewrite_duration' else eligible
        if name.startswith('latency_separate_'):rows=[r for r in rows if r[state]==name.removeprefix('latency_separate_pending_')]
        train=[r for r in rows if assignments[r['experiment_id']] in cfg['train_family_indices']]
        test=[r for r in rows if assignments[r['experiment_id']] in cfg['test_family_indices']]
        require({r['experiment_id'] for r in train}.isdisjoint({r['experiment_id'] for r in test}),'Episode split leakage')
        target='rewrite_service_target_ms' if name=='rewrite_duration' else 'service_target_ms'
        fields=record['models'][name]['predictors'];x=np.asarray([[number(r[k]) for k in fields] for r in test])
        actual_predictions=model.predict(x);saved=[p for p in predictions if p['model']==name]
        require(len(saved)==len(test)==record['models'][name]['test_rows'] and len(train)==record['models'][name]['train_rows'],'Prediction coverage differs')
        for r,p,estimate in zip(test,saved,actual_predictions):
            key=(name,r['experiment_id'],r['measurement_id']);require(key not in seen,'Duplicate prediction');seen.add(key)
            require((p['experiment_id'],p['measurement_id'])==(r['experiment_id'],r['measurement_id']) and p['actual_ms']==number(r[target]),'Actual target/identity differs')
            require(p['prediction_ms']==float(estimate),'Persisted estimator prediction differs')
            baseline_rows=[t for t in train if name=='rewrite_duration' or t['query_id']==r['query_id']]
            require(p['training_median_ms']==float(np.median([number(t[target]) for t in baseline_rows])),'Baseline uses different training rows')
        drift={}
        for field in fields:
            if field=='query_id':continue
            values=[number(r[field]) for r in train];lo,hi=min(values),max(values)
            drift[field]={'train_min':lo,'train_max':hi,'heldout_outside_training_range':sum(not lo<=number(r[field])<=hi for r in test)}
        summaries[name]={'train_rows':len(train),'test_rows':len(test),
                         'mae_ms':float(np.mean([abs(p['prediction_ms']-p['actual_ms']) for p in saved])),
                         'training_median_mae_ms':float(np.mean([abs(p['training_median_ms']-p['actual_ms']) for p in saved])),
                         'negative_predictions':sum(p['prediction_ms']<0 for p in saved),'feature_range_diagnostic':drift}
    require(len(seen)==len(predictions),'Unknown/orphan predictions')
    report={'status':'real_saved_fit_prediction_roundtrip_verified_only','fit_record_sha256':sha256(directory/'fit_record.json'),
            'audit_code_sha256':sha256(Path(__file__)),'models':summaries,'excluded_incomplete_history_rows':len(dropped),
            'calibrated_training_accepted':False,'scheduler_authorized':False,
            'limitations':['Integrity/roundtrip success is not accuracy acceptance.','One test source family/two episodes and one held-out rewrite; no calibration/power claim.','Feature range diagnostics do not justify tuning on held-out outcomes.']}
    with output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fit-directory',type=Path,required=True);p.add_argument('--export-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();audit(a.fit_directory,a.export_directory,a.output)
