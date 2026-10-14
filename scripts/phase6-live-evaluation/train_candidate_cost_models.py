#!/usr/bin/env python3
"""Exploratory measured-cost regression; never promotes a scheduler model.

Execution requires a SHA-bound export, its independent verification receipt,
and an explicitly registered chronological family split. No missing-value repair.
"""
import argparse
import csv
import json
import math
import platform
import shutil
from datetime import datetime
from pathlib import Path

from experiment_validation import require, sha256

HOST = [f'{field}_{seconds}s' for seconds in (60, 300) for field in
        ('cpu_busy_fraction', 'memory_used_fraction', 'read_bytes_per_second', 'write_bytes_per_second')]
LAYOUT = ['file_count', 'record_count', 'total_bytes']
STATE = 'maintenance_client_pending_at_feature_time'
QUERY = LAYOUT + HOST + ['queue_depth_at_feature_time', STATE]


def read_csv(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def number(value):
    if value in ('True', 'False'):
        return float(value == 'True')
    result = float(value)
    require(math.isfinite(result), 'Nonfinite predictor/target')
    return result


def run(config):
    import joblib
    import numpy as np
    import sklearn
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    cfg = json.loads(config.read_text())
    require(cfg['schema_version'] == 'candidate_cost_fit_v1', 'Unsupported fit protocol')
    require(cfg['ridge_alpha'] > 0, 'Register positive regularization')
    base = config.parent
    directory = (base / cfg['export_directory']).resolve()
    manifest_path = directory / 'export_record.json'
    require(sha256(manifest_path) == cfg['export_record_sha256'], 'Export changed')
    manifest = json.loads(manifest_path.read_text())
    require(manifest['schema_version'] == 'physical_cost_candidate_export_v1' and
            manifest['calibrated_training_accepted'] is False and
            manifest['scheduler_authorized'] is False, 'Unsupported/promoted export')
    verification = (base / cfg['verification']['path']).resolve()
    require(sha256(verification) == cfg['verification']['sha256'], 'Verification changed')
    receipt = json.loads(verification.read_text())
    require(receipt['status'] == 'verified_candidate_csv_raw_roundtrip_only' and
            receipt['export_record_sha256'] == cfg['export_record_sha256'], 'Missing raw verification')
    for name, digest in manifest['artifact_sha256'].items():
        require(sha256(directory / name) == digest, 'Candidate artifact changed')

    episodes = read_csv(directory / 'episodes.csv')
    intervals = sorted({(r['source_interval_start_utc'], r['source_interval_end_utc']) for r in episodes})
    families = []
    for start, end in intervals:
        start, end = datetime.fromisoformat(start), datetime.fromisoformat(end)
        require(start < end, 'Invalid source interval')
        if families and start < families[-1][1]:
            families[-1][1] = max(end, families[-1][1])
        else:
            families.append([start, end])
    train = cfg['train_family_indices']
    test = cfg['test_family_indices']
    require(train and test and len(set(train + test)) == len(train + test), 'Overlapping/empty split')
    require(set(train + test) == set(range(len(families))) and max(train) < min(test),
            'Require complete chronological whole-family partition')
    assignments = {}
    for row in episodes:
        start = datetime.fromisoformat(row['source_interval_start_utc'])
        end = datetime.fromisoformat(row['source_interval_end_utc'])
        matches = [i for i, (a, b) in enumerate(families) if a <= start and end <= b]
        require(len(matches) == 1 and row['experiment_id'] not in assignments, 'Ambiguous episode family')
        assignments[row['experiment_id']] = matches[0]

    queries, rewrites = read_csv(directory / 'queries.csv'), read_csv(directory / 'rewrites.csv')
    require(len(queries) == manifest['query_rows'] and len(rewrites) == manifest['rewrite_rows'], 'Row counts changed')
    require(set(QUERY + ['query_id']) <= set(manifest['query_predictor_allowlist']), 'Predictors not allowed')
    dropped = []
    if cfg['require_complete_demand_history']:
        dropped = [r for r in queries if any(r[f'offered_history_complete_{s}s'] != 'True' for s in (60, 300))]
        queries = [r for r in queries if r not in dropped]
    numeric = QUERY + (['offered_count_60s', 'offered_count_300s'] if cfg['require_complete_demand_history'] else [])
    output = (base / cfg['output_directory']).resolve()
    require(not output.exists(), 'Output occupied; preserve previous attempt')
    output.mkdir(parents=True)
    shutil.copyfile(config, output / 'config.json')
    shutil.copyfile(__file__, output / 'trainer.py')
    predictions, models, summaries = [], {}, {}

    def fit(name, rows, fields, target, categorical=False):
        training = [r for r in rows if assignments[r['experiment_id']] in train]
        testing = [r for r in rows if assignments[r['experiment_id']] in test]
        if not training or not testing:
            summaries[name] = {'status': 'not_fit_missing_train_or_test_rows', 'train_rows': len(training), 'test_rows': len(testing)}
            return
        # Predeclared regularization, all scaling/encoding/medians learned on train only.
        columns = fields + (['query_id'] if categorical else [])
        def matrix(records):
            return np.asarray([[number(r[f]) for f in columns] for r in records], dtype=float)
        x, xt = matrix(training), matrix(testing)
        y = np.asarray([number(r[target]) for r in training])
        require(all(y > 0), 'Nonpositive measured service time')
        transformers = [('numeric', StandardScaler(), list(range(len(fields))))]
        if categorical:
            known = {r['query_id'] for r in training}
            require(all(r['query_id'] in known for r in testing), 'Unseen test SQL identity; no extrapolation claim')
            transformers.append(('sql', OneHotEncoder(handle_unknown='error', sparse_output=False), [len(fields)]))
        model = make_pipeline(ColumnTransformer(transformers), Ridge(alpha=cfg['ridge_alpha']))
        model.fit(x, y)
        yp = model.predict(xt)
        models[name] = model
        for r, pred in zip(testing, yp):
            median_rows = [t for t in training if not categorical or t['query_id'] == r['query_id']]
            baseline = float(np.median([number(t[target]) for t in median_rows]))
            predictions.append({'model': name, 'experiment_id': r['experiment_id'], 'measurement_id': r['measurement_id'],
                                'query_id': r.get('query_id'), 'maintenance_pending': r.get(STATE), 'file_count': r['file_count'],
                                'source_family': assignments[r['experiment_id']], 'actual_ms': number(r[target]),
                                'prediction_ms': float(pred), 'training_median_ms': baseline})
        own = [p for p in predictions if p['model'] == name]
        groups = {}
        for dimension in ('experiment_id', 'query_id', 'maintenance_pending', 'file_count'):
            groups[dimension] = {}
            for value in sorted({str(p[dimension]) for p in own}):
                block = [p for p in own if str(p[dimension]) == value]
                groups[dimension][value] = {'rows': len(block), 'mae_ms': float(np.mean([abs(p['prediction_ms'] - p['actual_ms']) for p in block])),
                                           'median_baseline_mae_ms': float(np.mean([abs(p['training_median_ms'] - p['actual_ms']) for p in block]))}
        summaries[name] = {'status': 'exploratory_fit_only', 'train_rows': len(training), 'test_rows': len(testing),
                           'train_episodes': sorted({r['experiment_id'] for r in training}), 'test_episodes': sorted({r['experiment_id'] for r in testing}),
                           'predictors': columns, 'negative_predictions': sum(p['prediction_ms'] < 0 for p in own), 'groups': groups}

    fit('latency_shared', queries, numeric, 'service_target_ms', True)
    for pending in ('False', 'True'):
        fit('latency_separate_pending_' + pending, [r for r in queries if r[STATE] == pending],
            [f for f in numeric if f != STATE], 'service_target_ms', True)
    fit('rewrite_duration', rewrites, LAYOUT + HOST, 'rewrite_service_target_ms')
    joblib.dump(models, output / 'exploratory_models.joblib')
    (output / 'heldout_predictions.json').write_text(json.dumps(predictions, indent=2) + '\n')
    report = {'status': 'exploratory_uncalibrated_no_scheduler_authorization', 'calibrated_training_accepted': False,
              'scheduler_authorized': False, 'export_record_sha256': cfg['export_record_sha256'], 'config_sha256': sha256(config),
              'trainer_sha256': sha256(Path(__file__)), 'source_families': [[a.isoformat(), b.isoformat()] for a, b in families],
              'episode_family_assignment': assignments, 'dropped_incomplete_history_measurements': [r['measurement_id'] for r in dropped],
              'models': summaries, 'versions': {'python': platform.python_version(), 'sklearn': sklearn.__version__, 'numpy': np.__version__},
              'limitations': ['No calibration, model selection, counterfactual penalty or scheduler promotion.',
                              'Observed client maintenance pending is not exact engine-active exposure.',
                              'Rows within episodes/source families are dependent; row MAE is descriptive.',
                              'Negative regression predictions retained and reported, never clipped into an accepted policy.']}
    (output / 'fit_record.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    run(parser.parse_args().config.resolve())
