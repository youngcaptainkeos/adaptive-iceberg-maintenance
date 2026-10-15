#!/usr/bin/env python3
"""Detached read-only failure diagnostics on real frozen cost evidence; no refit."""
import argparse,csv,json,shutil,traceback
from pathlib import Path
from datetime import datetime,timezone
from experiment_validation import require,sha256,load_json,verified_file
from audit_candidate_cost_fit import audit,number

def run(protocol):
    import numpy as np
    import joblib
    cfg,base=load_json(protocol)
    require(cfg['schema_version']=='cost_failure_background_audit_v1','Unknown protocol')
    out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(protocol,out/'protocol.json')
    for name in ('run_cost_failure_audit.py','audit_candidate_cost_fit.py','experiment_validation.py'):
        shutil.copyfile(Path(__file__).parent/name,out/name)
    try:
        fit_record=verified_file(cfg['fit_record'],base);export_record=verified_file(cfg['export_record'],base)
        fit=fit_record.parent;export=export_record.parent
        audit(fit,export,out/'independent_roundtrip.json')
        record=json.loads(fit_record.read_text());fitcfg=json.loads((fit/'config.json').read_text())
        manifest=json.loads(export_record.read_text());ecfg=json.loads((export/'config.json').read_text())
        def read(name):
            with (export/name).open() as f:return list(csv.DictReader(f))
        queries,rewrites=read('queries.csv'),read('rewrites.csv')
        excluded=set(record['dropped_incomplete_history_measurements']);eligible=[r for r in queries if r['measurement_id'] not in excluded]
        models=joblib.load(fit/'exploratory_models.joblib');predictions=json.loads((fit/'heldout_predictions.json').read_text())
        diagnostics={};families=record['episode_family_assignment'];state='maintenance_client_pending_at_feature_time'
        for name,model in models.items():
            rows=rewrites if name=='rewrite_duration' else eligible
            if name.startswith('latency_separate_'):rows=[r for r in rows if r[state]==name.removeprefix('latency_separate_pending_')]
            train=[r for r in rows if families[r['experiment_id']] in fitcfg['train_family_indices']]
            test=[r for r in rows if families[r['experiment_id']] in fitcfg['test_family_indices']]
            fields=record['models'][name]['predictors'];numeric=[f for f in fields if f!='query_id']
            x=np.asarray([[number(r[f]) for f in fields] for r in train]);xt=np.asarray([[number(r[f]) for f in fields] for r in test])
            processor=model.steps[0][1];estimator=model.steps[-1][1]
            scaler=processor.named_transformers_['numeric'];numeric_x=x[:,:len(numeric)]
            # Registered floating-point roundoff check, not an accuracy gate.
            np.testing.assert_allclose(scaler.mean_,np.mean(numeric_x,axis=0),rtol=cfg['numeric_rtol'],atol=cfg['numeric_atol'])
            variance=np.var(numeric_x,axis=0)
            np.testing.assert_allclose(scaler.var_,variance,rtol=cfg['numeric_rtol'],atol=cfg['numeric_atol'])
            z=processor.transform(x);zt=processor.transform(xt);singular=np.linalg.svd(z-z.mean(axis=0),compute_uv=False)
            names=list(processor.get_feature_names_out());contributions=zt*estimator.coef_
            target='rewrite_service_target_ms' if name=='rewrite_duration' else 'service_target_ms'
            y=np.asarray([number(r[target]) for r in train]);feature_report={}
            for i,f in enumerate(numeric):
                v=numeric_x[:,i];tv=xt[:,i];sd=float(np.std(v));lo,hi=float(min(v)),float(max(v))
                feature_report[f]={'train_min':lo,'train_max':hi,'train_std':sd,'constant_in_train':sd==0,
                    'train_target_correlation':float(np.corrcoef(v,y)[0,1]) if sd>0 and float(np.std(y))>0 else None,
                    'test_outside_training_range':int(np.sum((tv<lo)|(tv>hi))),
                    'test_max_absolute_standardized_value':float(np.max(np.abs(zt[:,i])))}
            errors={}
            saved=[p for p in predictions if p['model']==name]
            for eid in sorted({p['experiment_id'] for p in saved}):
                selected=[p for p in saved if p['experiment_id']==eid]
                errors[eid]={'rows':len(selected),'mae_ms':float(np.mean([abs(p['prediction_ms']-p['actual_ms']) for p in selected])),
                    'training_median_mae_ms':float(np.mean([abs(p['training_median_ms']-p['actual_ms']) for p in selected])),
                    'negative_predictions':sum(p['prediction_ms']<0 for p in selected)}
            diagnostics[name]={'train_only_scaler_reconstruction_passed':True,'train_rows':len(train),'test_rows':len(test),
                'train_episodes':sorted({r['experiment_id'] for r in train}),'test_episodes':sorted({r['experiment_id'] for r in test}),
                'transformed_columns':len(names),'centered_design_rank':int(np.linalg.matrix_rank(z-z.mean(axis=0))),
                'singular_values':singular.tolist(),'intercept_ms':float(estimator.intercept_),
                'coefficients_ms_per_transformed_feature':dict(zip(names,map(float,estimator.coef_))),
                'mean_absolute_heldout_prediction_contribution_ms':dict(zip(names,map(float,np.mean(np.abs(contributions),axis=0)))),
                'features':feature_report,'heldout_episode_errors':errors}
        pipeline=[]
        for spec in ecfg['successful_arm_results']:
            receipt=verified_file(spec,base);directory=receipt.parent;rcfg=json.loads((directory/'config.json').read_text())
            eid=rcfg['experiment_id'];require(sha256(directory/'events.jsonl')==manifest['source_evidence'][eid]['events_sha256'],'Raw source changed')
            hashes={p.name:sha256(p) for p in sorted((directory/'code').glob('*.py'))}
            pipeline.append({'experiment_id':eid,'family':families[eid],'action_arm':rcfg['action_arm'],
                'initial_file_count':rcfg.get('initial_file_count'),'query_preparation_contract':rcfg.get('query_preparation_contract'),
                'telemetry_availability_contract':rcfg.get('telemetry_availability_contract'),
                'telemetry_persistence_contract':rcfg.get('telemetry_persistence_contract'),
                'submission_availability_contract':rcfg.get('submission_availability_contract'),'telemetry':rcfg['telemetry'],
                'frozen_code_sha256':hashes,'result_sha256':sha256(receipt)})
        report={'status':'completed_read_only_failure_and_pipeline_audit_no_refit','completed_utc':datetime.now(timezone.utc).isoformat(),
            'fit_record_sha256':sha256(fit_record),'export_record_sha256':sha256(export_record),'models':diagnostics,'episode_pipeline_inventory':pipeline,
            'distinct_instrumentation_code_vectors':len({json.dumps(p['frozen_code_sha256'],sort_keys=True) for p in pipeline}),
            'scheduler_authorized':False,'calibrated_training_accepted':False,
            'limits':['Training-only preprocessing reconstruction is not model accuracy acceptance.','Held-out diagnostics cannot justify retuning this test set.',
                     'Coefficients/contributions/correlations are descriptive, not causal effects.','This read-only audit cannot validate an unexercised synchronization branch.'],
            'next_gates':['Consistent real instrumentation and independently registered matched layout/regime blocks.',
                          'Training-only model development followed by untouched future test families.',
                          'Adequate independent rewrite/exposure/calibration blocks before scheduler deployment.']}
        (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        text=['# Cost failure and pipeline audit','',report['status'],'','No fitting, SQL, maintenance or scheduler promotion was performed.','',
              f"Distinct frozen instrumentation versions: {report['distinct_instrumentation_code_vectors']}",'',
              '| Model | Training rows / episodes | Test rows / episodes | Scaling reconstructed |','| --- | --- | --- | --- |']
        for n,d in diagnostics.items():text.append(f"| {n} | {d['train_rows']} / {len(d['train_episodes'])} | {d['test_rows']} / {len(d['test_episodes'])} | passed |")
        text+=['','Detailed training coverage, constants, design rank, coefficients, held-out contributions and per-episode errors are in report.json.',
               'These identify failure patterns, not causal explanations or permission to tune on the test set.','',*['- '+v for v in report['next_gates']]]
        (out/'report.md').write_text('\n'.join(text)+'\n')
        print(json.dumps({'status':report['status'],'output_directory':str(out)}),flush=True)
    except Exception as exc:
        (out/'failure.json').write_text(json.dumps({'status':'failed_preserved','error':str(exc),'traceback':traceback.format_exc()},indent=2)+'\n')
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);a=p.parse_args();run(a.protocol.resolve())
