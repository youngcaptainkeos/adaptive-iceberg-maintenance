"""Reload real exploratory artifacts; reconstruct support/baselines without refitting."""
from collections import defaultdict,Counter
from statistics import median
import json
import math
from pathlib import Path
from three_model_maintenance.contracts import require
from three_model_maintenance.models.latency import STATE,boolean,cell,feature_vector,content_sha256
from three_model_maintenance.training.data import read,save,sha,selected_data


def audit(cfg,protocol,out):
    import joblib
    out.mkdir(exist_ok=False);root=Path(cfg['output_directory']);fit=read(root/'fit/result.json')
    require(fit['status']=='fitted_exploratory_candidates_pending_artifact_audit' and
            fit['protocol_sha256']==sha(protocol) and fit['freeze_sha256']==sha(root/'freeze/result.json'), 'Fit lineage differs')
    for name,digest in fit['artifacts'].items():require(sha(root/'fit'/name)==digest,'Changed fitted artifact '+name)
    frozen=read(root/'freeze/result.json');admitted=read(root/'verify/result.json')
    rows,evidence,excluded=selected_data(cfg)
    require(content_sha256(rows)==frozen['training_rows_sha256']==admitted['training_rows_sha256'],'Changed audited rows')
    require(len(rows)==admitted['eligible_rows'] and len(excluded)==len(admitted['excluded_rows']),'Eligibility changed')
    reports=[]
    for spec in cfg['estimator_specs']:
        name=spec['kind'];bundle=joblib.load(root/'fit'/(name+'.joblib'))
        auth=read(root/'freeze'/(name+'_authorization.json'))
        require(bundle.fitted and bundle.spec==spec and list(bundle.feature_names)==cfg['feature_names'],'Bundle specification mismatch')
        require(auth['offline_data_audit']['sha256']==sha(root/'verify/result.json') and
                auth['freeze_sha256']==sha(root/'freeze/result.json'),'Offline permission lineage differs')
        groups={n:defaultdict(list) for n in ('query_median','query_layout_median','query_layout_state_median')}
        for row in rows:
            q,f,s=cell(row);target=float(row['service_target_ms'])
            for n,key in (('query_median',(q,)),('query_layout_median',(q,f)),('query_layout_state_median',(q,f,s)):
                groups[n][key].append(target)
        require(bundle.medians=={n:{key:median(v) for key,v in g.items()} for n,g in groups.items()},'Empirical baseline differs from actual labels')
        for model_name,condition in (('shared',None),('A',True),('B',False)):
            selected=[r for r in rows if condition is None or boolean(r[STATE])==condition]
            x=[feature_vector(r,cfg['feature_names']) for r in selected]
            require(bundle.support[model_name]=={cell(r) for r in selected},'Training support differs')
            require(bundle.bounds[model_name]==[(min(v[i] for v in x),max(v[i] for v in x)) for i in range(len(cfg['feature_names']))], 'Numeric support box differs')
        saved=[json.loads(line) for line in (root/'fit'/(name+'_training_diagnostic.jsonl')).open()]
        require(len(saved)==len(rows),'Missing diagnostic rows')
        supported=Counter();live_refused=0
        for row,record in zip(rows,saved):
            key=(row['experiment_id'],row['measurement_id'])
            require((record['experiment_id'],record['measurement_id'])==key and
                    record['scope']=='training_artifact_diagnostic_not_accuracy','Diagnostic identity/scope differs')
            prediction=bundle.predict_training_diagnostic(row,evidence[key],authorization=auth)
            require(prediction==record['predictions'],'Reloaded prediction differs')
            for method,value in prediction.items():
                require(value['support_status']=='supported' and math.isfinite(value['value_ms']) and value['value_ms']>0 and
                        value['uncertainty_status']=='not_calibrated','Invalid prediction on its actual training support')
                supported[method]+=1
            require(evidence[key]['runtime_adapter_accepted'] is False,'Original runtime flag changed')
            live=bundle.predict(row,evidence[key])
            require(all(v['support_status']=='unsupported' and v['value_ms'] is None and
                        'runtime_evidence_not_accepted' in v['reasons'] for v in live.values()),'Offline fit silently authorized runtime prediction')
            live_refused+=1
        reports.append({'estimator_spec':spec,'reloaded_training_diagnostics':len(rows),'supported_training_diagnostic_counts':dict(supported),
                        'runtime_predictions_refused':live_refused,'independent_medians_and_support_reconstruction':'passed'})
    save(out/'result.json',{'status':'passed_exploratory_artifact_integrity_only','protocol_sha256':sha(protocol),
        'fit_result_sha256':sha(root/'fit/result.json'),'eligible_rows':len(rows),'condition_counts':admitted['condition_counts'],
        'checks':reports,'model_refitted':False,'validation_or_test_scored':False,'accuracy_metrics_reported':False,
        'candidate_selected':False,'runtime_adapter_accepted':False,'calibration_accepted':False,'scheduler_authorized':False,
        'limitations':['Reloading and training-row checks do not measure generalization or demonstrate separate-model superiority.',
                      'One source family and one maintenance episode; no held-out independent blocks.']})
