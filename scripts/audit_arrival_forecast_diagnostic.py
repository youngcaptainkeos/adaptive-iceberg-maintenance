#!/usr/bin/env python3
"""Verify saved real forecast targets, baseline histories, split coverage and metrics."""
import argparse
import csv
from datetime import datetime,timedelta
import hashlib
import json
from pathlib import Path
import numpy as np


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(1024*1024):h.update(chunk)
    return h.hexdigest()


def audit(directory, result_hash, cohort_directory):
    root=Path(directory).resolve();source=Path(cohort_directory).resolve();receipt=root/'result.json'
    if digest(receipt)!=result_hash:raise ValueError('Result not pinned/changed')
    r=json.loads(receipt.read_text());cfg=r['configuration']
    if r['status']!='completed_diagnostic_only':raise ValueError('Completed diagnostic required')
    if digest(root/'forecast_code.py')!=r['code_sha256'] or json.loads((root/'forecast_config.json').read_text())!=cfg:raise ValueError('Frozen code/protocol changed')
    cohort_path=root/'cohort_record.json';cohort=json.loads(cohort_path.read_text());independent_path=root/'independent_cohort_audit.json';independent=json.loads(independent_path.read_text())
    if digest(cohort_path)!=cfg['cohort_record']['sha256'] or digest(independent_path)!=cfg['independent_audit']['sha256'] or independent['cohort_record_sha256']!=digest(cohort_path) or independent['status']!='passed_arrival_export_integrity':raise ValueError('Cohort/audit binding mismatch')
    count_path=source/'observed_bin_counts.csv'
    if digest(count_path)!=cohort['observed_bin_counts_sha256']:raise ValueError('Observed count source changed')
    with count_path.open(newline='') as stream:counts=[int(row['observed_arrivals']) for row in csv.DictReader(stream)]
    prefix=[0]
    for value in counts:
        if value<0:raise ValueError('Invalid observed count')
        prefix.append(prefix[-1]+value)
    interval=cohort['configuration']['bin_seconds'];train_end=cohort['configuration']['training_seconds']//interval;cal_end=train_end+cohort['configuration']['calibration_seconds']//interval;origin=datetime.fromisoformat(cohort['observation_origin_utc'])
    prediction_path=root/'predictions.csv'
    if digest(prediction_path)!=r['predictions_sha256']:raise ValueError('Prediction artifact changed')
    groups={};seen=set();methods={'learned_poisson','persistence','seasonal_day','seasonal_week'}
    with prediction_path.open(newline='') as stream:
        for row in csv.DictReader(stream):
            horizon=int(row['horizon_bins']);cutoff=int(row['cutoff_bin']);method=row['method'];split=row['split']
            if horizon not in cfg['horizon_bins'] or method not in methods or split not in ('calibration','test'):raise ValueError('Unknown forecast identity')
            low,high=(train_end,cal_end) if split=='calibration' else (cal_end,len(counts))
            key=(horizon,split,method,cutoff)
            if key in seen or not low<=cutoff<=high-horizon:raise ValueError('Duplicate/misassigned/cross-split forecast horizon')
            seen.add(key)
            if datetime.fromisoformat(row['cutoff_utc'])!=origin+timedelta(seconds=cutoff*interval):raise ValueError('Changed original cutoff clock')
            truth=prefix[cutoff+horizon]-prefix[cutoff]
            if int(row['observed_future_count'])!=truth:raise ValueError('Future target differs from actual raw bins')
            predicted=float(row['prediction_count'])
            if not np.isfinite(predicted) or predicted<0:raise ValueError('Invalid/nonphysical count forecast')
            if method=='persistence' and predicted!=horizon*counts[cutoff-1]:raise ValueError('Persistence uses wrong actual history')
            if method.startswith('seasonal_'):
                period=cfg['seasonal_period_bins'][method];past_start=cutoff-period
                if past_start<0 or past_start+horizon>cutoff or predicted!=prefix[past_start+horizon]-prefix[past_start]:raise ValueError('Seasonal forecast uses unavailable/incorrect history')
            groups.setdefault((horizon,split,method),[]).append((predicted,truth))
    for horizon in cfg['horizon_bins']:
        model=r['models'][str(horizon)]
        if digest(root/model['artifact'])!=model['sha256'] or model['training_samples']!=train_end-horizon-max(cfg['lag_bins']+cfg['rolling_bins'])+1:raise ValueError('Training artifact/sample horizon mismatch')
        for split,low,high in [('calibration',train_end,cal_end),('test',cal_end,len(counts))]:
            for method in methods:
                values=groups[(horizon,split,method)]
                if len(values)!=high-low-horizon+1:raise ValueError('Forecast coverage omitted/selected cutoffs')
                array=np.asarray(values,dtype=float);prediction,truth=array[:,0],array[:,1];errors=prediction-truth
                measured={'n':len(values),'mae_count':float(np.mean(np.abs(errors))),'rmse_count':float(np.sqrt(np.mean(errors**2))),'mean_observed_count':float(np.mean(truth)),'mean_prediction_count':float(np.mean(prediction))}
                if measured!=r['metrics'][str(horizon)][split][method]:raise ValueError('Metrics differ from preserved prediction rows')
    if digest(receipt)!=result_hash or digest(prediction_path)!=r['predictions_sha256'] or digest(count_path)!=cohort['observed_bin_counts_sha256']:raise ValueError('Inputs changed during audit')
    return {'schema_version':'saved_arrival_forecast_audit_v1','status':'passed_saved_prediction_integrity','result_sha256':result_hash,'predictions_sha256':r['predictions_sha256'],'audited_prediction_rows':len(seen),'audit_code_sha256':digest(Path(__file__)),'scope':'Independent integer-prefix targets/seasonal histories/cutoff/split coverage and exact CSV metric reconstruction. Hashes verify frozen code/model artifacts; no pickle loading, scheduling, physical costs, confidence interval or publication independence claim.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True);p.add_argument('--result-sha256',required=True);p.add_argument('--cohort-directory',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=audit(a.directory,a.result_sha256,a.cohort_directory)
    with Path(a.output).open('x') as stream:json.dump(r,stream,indent=2);stream.write('\n')
    print(json.dumps(r))
