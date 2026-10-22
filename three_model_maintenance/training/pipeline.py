"""Four detached stages: raw verification, committed freeze, fit, artifact audit."""
import argparse
import ast
import fcntl
import json
import os
import platform
import subprocess
import sys
import traceback
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter
from three_model_maintenance.contracts import require
from three_model_maintenance.training.data import read,save,sha,verify,selected_data
from three_model_maintenance.models.latency import LatencyCandidates,STATE,boolean,cell,content_sha256

REPO=Path(__file__).resolve().parents[2]
WRAPPER=REPO/'scripts/phase6-live-evaluation/run_with_failure_alert.py'


def now():return datetime.now(timezone.utc).isoformat()


def check_registration(protocol):
    cfg=read(protocol)
    require(cfg['schema_version']=='three_model_exploratory_development_fit_v2' and
            cfg['fit_scope']=='exploratory_development_only','Unknown training registration')
    require(cfg['validation_or_test_scored'] is False and cfg['candidate_selection_performed'] is False and
            cfg['runtime_adapter_accepted'] is False and cfg['calibration_accepted'] is False and
            cfg['scheduler_authorized'] is False,'Unregistered promotion')
    committed=subprocess.check_output(['git','show','HEAD:'+str(protocol.relative_to(REPO))],cwd=REPO)
    require(committed==protocol.read_bytes(),'Training registration is not committed unchanged')
    for spec in cfg['source_files']:
        path=REPO/spec['path'];require(sha(path)==spec['sha256'],'Changed frozen training code '+spec['path'])
        if path.suffix=='.py':ast.parse(path.read_text(),filename=str(path))
    require(cfg['missing_prediction_policy']=='unsupported_no_substitution' and
            cfg['split_unit']=='whole_source_overlap_family','Substitution or row splits forbidden')
    return cfg


def freeze(cfg,protocol,out):
    out.mkdir(exist_ok=False)
    verified=Path(cfg['output_directory'])/'verify/result.json';audit=read(verified)
    require(audit['status']=='verified_development_training_inputs_only' and audit['protocol_sha256']==sha(protocol),
            'Missing independent offline data admission')
    rows,evidence,_=selected_data(cfg)
    require(content_sha256(rows)==audit['training_rows_sha256'],'Training rows changed after audit')
    record={'status':'frozen_before_estimator_fit_only','schema_version':'three_model_development_fit_freeze_v1',
            'protocol_sha256':sha(protocol),'protocol_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
            'created_utc':now(),'audit_sha256':sha(verified),'feature_names':cfg['feature_names'],
            'estimator_specs':cfg['estimator_specs'],'source_roles':cfg['source_roles'],
            'training_rows_sha256':audit['training_rows_sha256'],'training_evidence_sha256':audit['training_evidence_sha256'],
            'condition_counts':audit['condition_counts'],'training_episode_ids':sorted({r['experiment_id'] for r in rows}),
            'validation_or_test_scored':False,'runtime_adapter_accepted':False,'scheduler_authorized':False,
            'rationale':'Registered existing specifications, one known family training only; freeze precedes fitting, not collection/outcome inspection.'}
    save(out/'result.json',record)
    for spec in cfg['estimator_specs']:
        auth={'schema_version':'three_model_verified_fit_authorization_v1','training_scope':'exploratory_development_only',
              'fit_authorized':True,'source_identity_verified':True,'raw_bounds_verified':True,'protocol_freeze_verified':True,
              'training_rows_sha256':record['training_rows_sha256'],'training_evidence_sha256':record['training_evidence_sha256'],
              'training_episode_ids':record['training_episode_ids'],'feature_names':cfg['feature_names'],'estimator_spec':spec,
              'offline_data_audit':{'path':str(verified),'sha256':sha(verified)},'freeze_sha256':sha(out/'result.json'),
              'protocol_sha256':sha(protocol),'validation_or_test_scored':False,'runtime_adapter_accepted':False,
              'scheduler_authorized':False}
        save(out/(spec['kind']+'_authorization.json'),auth)


def model_size(bundle):
    import numpy as np
    details={}
    for name,model in bundle.models.items():
        pipeline=model.regressor_ if bundle.spec['kind']=='log_ridge' else model
        estimator=pipeline.named_steps['estimator']
        details[name]=({'coefficient_count':int(np.size(estimator.coef_)),
                        'intercept_count':int(np.size(estimator.intercept_))} if bundle.spec['kind']=='log_ridge'
                       else {'node_count':int(estimator.tree_.node_count),'leaf_count':int(estimator.get_n_leaves())})
    return details


def fit(cfg,protocol,out):
    import joblib,sklearn,numpy
    out.mkdir(exist_ok=False);root=Path(cfg['output_directory'])
    frozen=read(root/'freeze/result.json')
    require(frozen['status']=='frozen_before_estimator_fit_only' and frozen['protocol_sha256']==sha(protocol), 'Missing fit freeze')
    require(frozen['estimator_specs']==cfg['estimator_specs'],'Different parameter budget')
    rows,evidence,_=selected_data(cfg);artifacts={};cards=[]
    for spec in cfg['estimator_specs']:
        name=spec['kind'];auth_path=root/'freeze'/(name+'_authorization.json');auth=read(auth_path)
        require(auth['freeze_sha256']==sha(root/'freeze/result.json') and
                auth['protocol_sha256']==sha(protocol),'Authorization differs from registered freeze')
        bundle=LatencyCandidates(feature_names=cfg['feature_names'],estimator_spec=spec,support_policy=cfg['support_policy'])
        bundle.fit(rows,evidence,authorization=auth)
        path=out/(name+'.joblib');joblib.dump(bundle,path)
        diagnostics=out/(name+'_training_diagnostic.jsonl')
        with diagnostics.open('x') as stream:
            for row in rows:
                key=(row['experiment_id'],row['measurement_id'])
                result=bundle.predict_training_diagnostic(row,evidence[key],authorization=auth)
                stream.write(json.dumps({'experiment_id':key[0],'measurement_id':key[1],
                    'scope':'training_artifact_diagnostic_not_accuracy','predictions':result},allow_nan=False)+'\n')
        artifacts[path.name]=sha(path);artifacts[diagnostics.name]=sha(diagnostics)
        cards.append({'estimator_spec':spec,'artifact':path.name,'sha256':sha(path),'authorization_sha256':sha(auth_path),
                      'feature_names':list(bundle.feature_names),'target':'measured_client_service_ms','model_size':model_size(bundle),
                      'support_cells':{name:[list(c) for c in sorted(values)] for name,values in bundle.support.items()},
                      'numeric_bounds':bundle.bounds,'condition_counts':frozen['condition_counts']})
    card={'scope':'exploratory_development_only','models':cards,'training_rows':len(rows),
          'source_roles':cfg['source_roles'],'validation_or_test_scored':False,'candidate_selection_performed':False,
          'runtime_adapter_accepted':False,'calibration_accepted':False,'scheduler_authorized':False,
          'python':platform.python_version(),'sklearn':sklearn.__version__,'numpy':numpy.__version__,'joblib':joblib.__version__,
          'limitations':['16 A observations from one maintenance episode are not independent A episodes.',
                        'All examples are training; saved predictions have no accuracy/validation interpretation.',
                        'Separate estimators use the same fixed specification as shared, not equal total parameter count.',
                        'A is client-pending condition, not measured causal harm or counterfactual cost.',
                        'C demand forecasting and rewrite-cost training are outside this job.']}
    save(out/'model_card.json',card);artifacts['model_card.json']=sha(out/'model_card.json')
    save(out/'result.json',{'status':'fitted_exploratory_candidates_pending_artifact_audit','protocol_sha256':sha(protocol),
                           'freeze_sha256':sha(root/'freeze/result.json'),'artifacts':artifacts,'ended_utc':now(),
                           'validation_or_test_scored':False,'runtime_adapter_accepted':False,'scheduler_authorized':False})


def run_stage(protocol,stage):
    cfg=check_registration(protocol);root=Path(cfg['output_directory']);out=root/stage
    if stage=='verify':verify(cfg,protocol,out)
    elif stage=='freeze':freeze(cfg,protocol,out)
    elif stage=='fit':fit(cfg,protocol,out)
    else:
        from three_model_maintenance.audits.trained_bundle import audit
        audit(cfg,protocol,out)


def run(protocol):
    cfg=check_registration(protocol);root=Path(cfg['output_directory']);root.mkdir(parents=True,exist_ok=False)
    save(root/'registration.json',cfg)
    locks=[]
    report={'status':'running','pid':os.getpid(),'started_utc':now(),'protocol_sha256':sha(protocol),'stages':[],
            'model_fit_performed':False,'model_fit_attempted':False,'validation_or_test_scored':False,'runtime_adapter_accepted':False,'scheduler_authorized':False}
    def progress():
        temp=root/'progress.next.json';temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(root/'progress.json')
    try:
        for name in ('.three_model_collection.lock','.queue_aware_study.lock','.common_horizon_cohort.lock','.physical_correctness.lock'):
            handle=(REPO/'results'/name).open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(handle)
        progress()
        for stage in ('verify','freeze','fit','audit'):
            check_registration(protocol)
            record={'stage':stage,'started_utc':now()};report['stages'].append(record)
            if stage=='fit':
                report['model_fit_attempted']=True
                report['model_fit_performed']=None  # Unknown until child reports completion; never hide partial fits.
            progress()
            command=[sys.executable,'-B','-m','three_model_maintenance.training.pipeline','--protocol',str(protocol),'--stage',stage]
            with (root/(stage+'.log')).open('x') as log:
                completed=subprocess.run([sys.executable,'-B',str(WRAPPER),'--label',cfg['label']+'_'+stage,
                    '--receipt',str(root/(stage+'_failure_alert.json')),'--',*command],cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
            record.update(returncode=completed.returncode,ended_utc=now());progress()
            require(completed.returncode==0,'Failed '+stage+'; no retry or dependent stage')
            if stage=='fit':report['model_fit_performed']=True
            report[stage+'_result_sha256']=sha(root/stage/'result.json')
        report['status']='completed_exploratory_fit_and_artifact_audit_only'
        report['condition_counts']=read(root/'verify/result.json')['condition_counts']
    except Exception as exc:
        report.update(status='failed_preserved_no_retry',error=str(exc),traceback=traceback.format_exc());raise
    finally:
        report['ended_utc']=now();progress();save(root/'result.json',report)
        for handle in locks:handle.close()
    notice={'delivered':False,'experiment_status':report['status']}
    try:
        request=urllib.request.Request(cfg['notification_topic'],data=(cfg['label']+': all four stages passed. Exploratory A/B/shared and median artifacts saved; '+str(report['condition_counts'])+'. No held-out accuracy/calibration/scheduler claim.').encode(),headers={'Title':'Capstone exploratory training completed'},method='POST')
        with urllib.request.urlopen(request,timeout=10) as response:notice.update(delivered=True,http_status=response.status)
    except Exception as exc:notice['error']=str(exc)
    save(root/'completion_notification.json',notice)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--stage',choices=('verify','freeze','fit','audit'))
    args=parser.parse_args();protocol=args.protocol.resolve()
    if args.stage:run_stage(protocol,args.stage)
    else:run(protocol)
