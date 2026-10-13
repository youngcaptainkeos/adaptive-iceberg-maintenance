#!/usr/bin/env python3
"""Chronological real-count forecast diagnostic; never a scheduling/model promotion."""
import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import shutil
import sys
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
import sklearn
from threadpoolctl import threadpool_limits
import joblib


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()


def artifact(spec, base):
    path=(base/spec['path']).resolve()
    if digest(path)!=spec['sha256']:raise ValueError('Registered artifact changed: '+str(path))
    return path


def features(history, when, lag_bins, rolling_bins):
    # Only the caller's observed prefix is exposed to feature construction.
    if len(history)<max(lag_bins+rolling_bins):raise ValueError('Insufficient past history')
    values=[history[-lag] for lag in lag_bins]
    values += [np.mean(history[-width:]) for width in rolling_bins]
    minute=when.hour*60+when.minute+when.second/60
    weekday=when.weekday()+minute/(24*60)
    values += [np.sin(2*np.pi*minute/(24*60)),np.cos(2*np.pi*minute/(24*60)),
               np.sin(2*np.pi*weekday/7),np.cos(2*np.pi*weekday/7)]
    return np.asarray(values,dtype=float)


def evaluate(config_path):
    path=Path(config_path).resolve();cfg=json.loads(path.read_text());base=path.parent
    if cfg['schema_version']!='observed_arrival_forecast_diagnostic_v1':raise ValueError('Unsupported forecast protocol')
    receipt=artifact(cfg['cohort_record'],base);audit_path=artifact(cfg['independent_audit'],base)
    r=json.loads(receipt.read_text());audit=json.loads(audit_path.read_text())
    if r['status']!='extracted_arrival_cohort_only' or audit['status']!='passed_arrival_export_integrity' or audit['cohort_record_sha256']!=digest(receipt):raise ValueError('Independent completed-cohort audit required')
    counts_path=receipt.parent/'observed_bin_counts.csv'
    if digest(counts_path)!=r['observed_bin_counts_sha256'] or audit['observed_bin_counts_sha256']!=r['observed_bin_counts_sha256']:raise ValueError('Count source changed')
    with counts_path.open(newline='') as f:
        reader=csv.DictReader(f);rows=list(reader)
    interval=r['configuration']['bin_seconds']
    counts=np.asarray([int(row['observed_arrivals']) for row in rows],dtype=np.int64)
    if len(counts)!=r['complete_bins'] or np.any(counts<0) or any(int(row['bin_id'])!=i or int(row['elapsed_seconds'])!=i*interval for i,row in enumerate(rows)) or int(counts.sum())!=r['complete_bin_arrivals']:raise ValueError('Invalid original count timeline')
    origin=datetime.fromisoformat(r['observation_origin_utc']);train_end=r['configuration']['training_seconds']//interval;cal_end=train_end+r['configuration']['calibration_seconds']//interval
    lags=cfg['lag_bins'];rolling=cfg['rolling_bins'];horizons=cfg['horizon_bins'];periods=cfg['seasonal_period_bins']
    for group in [lags,rolling,horizons,list(periods.values())]:
        if not group or any(not isinstance(v,int) or isinstance(v,bool) or v<=0 for v in group):raise ValueError('Explicit positive bin counts required')
    if set(periods)!= {'seasonal_day','seasonal_week'} or periods['seasonal_day']*interval!=24*3600 or periods['seasonal_week']*interval!=7*24*3600 or min(periods.values())<max(horizons):raise ValueError('Seasonal units/available history invalid')
    if max(periods.values())>train_end:raise ValueError('No weekly history at calibration boundary')
    parameters=cfg['model_parameters']
    if parameters.get('loss')!='poisson' or parameters.get('early_stopping') is not False:raise ValueError('Nonnegative count model and no internal random validation required')
    output=(base/cfg['output_directory']).resolve();output.mkdir(parents=True,exist_ok=False)
    for src,name in [(path,'forecast_config.json'),(Path(__file__),'forecast_code.py'),(receipt,'cohort_record.json'),(audit_path,'independent_cohort_audit.json')]:shutil.copy2(src,output/name)
    result={'schema_version':'arrival_forecast_diagnostic_result_v1','status':'in_progress','configuration':cfg,'sklearn_version':sklearn.__version__,'numpy_version':np.__version__,'python_version':sys.version,'code_sha256':digest(Path(__file__)),'metrics':{},'models':{},'scope':'One training-selected observed warehouse, chronological point forecasts only. Overlapping horizons are dependent; three reserved days cannot support finite 90% daily-block conformal calibration. No uncertainty claim, policy decision, physical replay/cost model or accepted Model C promotion.'}
    def save():
        temp=output/'result.tmp';temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(output/'result.json')
    save()
    try:
        with threadpool_limits(limits=cfg['cpu_threads']):
            with (output/'predictions.csv').open('x',newline='') as f:
                writer=csv.writer(f);writer.writerow(['split','cutoff_bin','cutoff_utc','horizon_bins','method','prediction_count','observed_future_count'])
                for horizon in horizons:
                    # Training labels and their entire future horizon stay in training.
                    start=max(lags+rolling)
                    indices=range(start,train_end-horizon+1)
                    X=np.asarray([features(counts[:i],origin+timedelta(seconds=i*interval),lags,rolling) for i in indices])
                    y=np.asarray([counts[i:i+horizon].sum() for i in indices],dtype=float)
                    if not len(y) or not np.isfinite(X).all() or y.sum()<=0:raise ValueError('Unusable actual training count targets')
                    model=HistGradientBoostingRegressor(**parameters);model.fit(X,y)
                    target=output/f'count_forecaster_h{horizon}.joblib';joblib.dump(model,target)
                    result['models'][str(horizon)]={'artifact':target.name,'sha256':digest(target),'training_samples':len(y),'effective_parameters':model.get_params()}
                    result['metrics'][str(horizon)]={}
                    for split,low,high in [('calibration',train_end,cal_end),('test',cal_end,len(counts))]:
                        cutoffs=list(range(low,high-horizon+1))
                        if not cutoffs:raise ValueError('Empty chronological evaluation segment')
                        # Each forecast receives only counts strictly before cutoff.
                        matrix=np.asarray([features(counts[:i],origin+timedelta(seconds=i*interval),lags,rolling) for i in cutoffs])
                        learned=model.predict(matrix)
                        methods={'learned_poisson':learned,'persistence':np.asarray([horizon*counts[i-1] for i in cutoffs],dtype=float)}
                        for name,period in periods.items():
                            methods[name]=np.asarray([counts[:i][i-period:i-period+horizon].sum() for i in cutoffs],dtype=float)
                        truth=np.asarray([counts[i:i+horizon].sum() for i in cutoffs],dtype=float)
                        detail={}
                        for name,predictions in methods.items():
                            if not np.isfinite(predictions).all() or np.any(predictions<0):raise ValueError('Invalid count forecast; no clipping/substitute prediction')
                            error=predictions-truth
                            detail[name]={'n':len(truth),'mae_count':float(np.mean(np.abs(error))),'rmse_count':float(np.sqrt(np.mean(error**2))),'mean_observed_count':float(np.mean(truth)),'mean_prediction_count':float(np.mean(predictions))}
                            for i,predicted,observed in zip(cutoffs,predictions,truth):writer.writerow([split,i,(origin+timedelta(seconds=i*interval)).isoformat(),horizon,name,float(predicted),int(observed)])
                        result['metrics'][str(horizon)][split]=detail
                    save()
        for spec in [cfg['cohort_record'],cfg['independent_audit']]:artifact(spec,base)
        if digest(counts_path)!=r['observed_bin_counts_sha256']:raise ValueError('Actual input changed during fitting')
        result.update(status='completed_diagnostic_only',predictions_sha256=digest(output/'predictions.csv'))
        save();print(json.dumps({'status':result['status'],'metrics':result['metrics']}))
    except Exception as exc:
        result.update(status='failed_preserved_artifacts',error=str(exc));save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True);args=parser.parse_args();evaluate(args.config)
