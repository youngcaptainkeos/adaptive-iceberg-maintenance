"""Registered shared/separate Ridge and boosted trees vs medians; family splits.

No row split, train/test refit, imputation or unsupported-prediction fallback.
Model selection is validation-only; test scored once from frozen training fits.
"""
import json,math
from collections import defaultdict
from pathlib import Path
from statistics import median
from three_model_maintenance.contracts import require,QUERY_FEATURES
from three_model_maintenance.training.data import read,save,sha

PLAN_FEATURES=tuple('plan_'+n+'_count' for n in ('operator','scan','join','aggregate','exchange','sort','filter','window'))
STATE='maintenance_client_pending_at_feature_time'


def matrix(rows,names):
    output=[]
    for row in rows:
        require(set(row['features'])==set(names),'Unknown/missing model features')
        values=[float(row['features'][n]) for n in names]
        require(all(math.isfinite(x) for x in values) and row['offered_history_complete'] and row['target_ms']>0,'Incomplete/nonfinite training evidence')
        output.append(values)
    return output


def estimator(kind,names,spec):
    from sklearn.compose import ColumnTransformer,TransformedTargetRegressor
    from sklearn.preprocessing import OneHotEncoder,StandardScaler
    from sklearn.pipeline import Pipeline
    import numpy as np
    query=names.index('query_id');numeric=[i for i in range(len(names)) if i!=query]
    transform=ColumnTransformer([('query',OneHotEncoder(handle_unknown='error',sparse_output=False),[query]),('numeric',StandardScaler(),numeric)])
    if kind=='ridge':
        from sklearn.linear_model import Ridge
        model=Ridge(**spec)
    else:
        require(kind=='boosted_tree','Unregistered estimator kind')
        from sklearn.ensemble import HistGradientBoostingRegressor
        model=HistGradientBoostingRegressor(**spec)
    return TransformedTargetRegressor(regressor=Pipeline([('features',transform),('estimator',model)]),func=np.log,inverse_func=np.exp)


def key(row,kind='state'):
    f=row['features'];q=int(f['query_id']);layout=int(f['file_count']);state=bool(f[STATE])
    return (q,) if kind=='query' else (q,layout) if kind=='layout' else (q,layout,state)


def run(cfg,collections,out):
    import joblib,sklearn,numpy as np
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    names=cfg['feature_names'];require(set(names)==QUERY_FEATURES|set(PLAN_FEATURES),'Registered actual predictor contract differs')
    rows=[]
    for item in collections:
        receipt=read(Path(item['directory'])/'result.json')
        require(receipt['status']=='audited_sf10_plan_candidates_only' and sha(Path(item['directory'])/'rows.json')==receipt['rows_sha256'],'Unaudited candidate package')
        actual=read(Path(item['directory'])/'rows.json');require(all(r['family']==item['family'] and r['role']==item['role'] for r in actual),'Family role changed')
        rows.extend(actual)
    roles={role:[r for r in rows if r['role']==role and r['offered_history_complete']] for role in ('train','validation','test')}
    families={role:{r['family'] for r in roles[role]} for role in roles}
    require(all(families.values()) and not any(families[a]&families[b] for a,b in (('train','validation'),('train','test'),('validation','test'))),'Whole-family split missing/overlapping')
    require(len({(r['experiment_id'],r['measurement_id']) for r in rows})==len(rows),'Repeated observation identity')
    train=roles['train'];require(all(sum(bool(r['features'][STATE])==s for r in train)>=cfg['minimum_state_rows'] for s in (False,True)),'Insufficient actual training A/B support; no fit')
    models={};supports={};bounds={}
    for kind,spec in cfg['estimators'].items():
        for architecture in ('shared','separate'):
            name=kind+'_'+architecture;models[name]={};supports[name]={};bounds[name]={}
            for condition in ([None] if architecture=='shared' else [False,True]):
                data=[r for r in train if condition is None or bool(r['features'][STATE])==condition]
                x=matrix(data,names);y=[r['target_ms'] for r in data]
                model=estimator(kind,names,spec);model.fit(x,y);models[name][condition]=model
                supports[name][condition]={key(r) for r in data};bounds[name][condition]=[(min(v[i] for v in x),max(v[i] for v in x)) for i in range(len(names))]
    joblib.dump(models,out/'training_only_models.joblib')
    groups={kind:defaultdict(list) for kind in ('query','layout','state')}
    for row in train:
        for kind in groups:groups[kind][key(row,kind)].append(row['target_ms'])
    medians={kind:{k:median(v) for k,v in group.items()} for kind,group in groups.items()}
    methods=list(models)+['median_'+k for k in medians]
    reports={};predictions={}
    for role in ('validation','test'):
        data=roles[role];x=matrix(data,names);preds={name:[] for name in methods}
        for row,values in zip(data,x):
            for name in models:
                condition=None if name.endswith('_shared') else bool(row['features'][STATE]);limits=bounds[name][condition]
                supported=key(row) in supports[name][condition] and all(lo<=v<=hi for v,(lo,hi) in zip(values,limits))
                value=float(models[name][condition].predict([values])[0]) if supported else None
                require(value is None or math.isfinite(value) and value>0,'Invalid learned prediction')
                preds[name].append(value)
            for kind,values_by_key in medians.items():preds['median_'+kind].append(values_by_key.get(key(row,kind)))
        common=[i for i in range(len(data)) if all(preds[m][i] is not None for m in methods)]
        scores={}
        for name in methods:
            errors=defaultdict(list)
            for i in common:errors[data[i]['experiment_id']].append(abs(preds[name][i]-data[i]['target_ms']))
            per_episode={eid:sum(v)/len(v) for eid,v in errors.items()}
            scores[name]=dict(supported=sum(v is not None for v in preds[name]),equal_episode_MAE_ms=sum(per_episode.values())/len(per_episode) if per_episode else None,per_episode_MAE_ms=per_episode)
        reports[role]=dict(rows=len(data),families=sorted(families[role]),common_supported_rows=len(common),methods=scores)
        predictions[role]=[dict(identity=[r['experiment_id'],r['measurement_id']],target_ms=r['target_ms'],predictions={m:preds[m][i] for m in methods}) for i,r in enumerate(data)]
        # Selection is frozen before any test predictions or test metrics.
        if role=='validation':
            eligible=[m for m in methods if scores[m]['equal_episode_MAE_ms'] is not None]
            save(out/'validation_selection.json',dict(selected=min(eligible,key=lambda m:(scores[m]['equal_episode_MAE_ms'],m)) if eligible else None,report=reports[role],refit=False))
    save(out/'predictions.json',predictions)
    save(out/'result.json',dict(status='completed_exploratory_whole_family_comparison_only',reports=reports,
        training_families=sorted(families['train']),training_rows=len(train),selected_by_validation=read(out/'validation_selection.json')['selected'],
        model_sha256=sha(out/'training_only_models.joblib'),sklearn_version=sklearn.__version__,calibration_accepted=False,scheduler_authorized=False,
        limitations=['One family per split is exploratory, not replicated scientific generalization.','Unsupported rows have no prediction; common-support coverage must accompany error.','Separate models have greater aggregate capacity under identical per-estimator settings.','No causal maintenance penalty, calibrated uncertainty or scheduling-benefit claim.']))
