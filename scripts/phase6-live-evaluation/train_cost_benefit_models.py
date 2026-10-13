#!/usr/bin/env python3
"""Train only from verified physical query/event data under a declared protocol.

No filename modes, imputation, synthetic augmentation or calibration fallback.
No bundle is published unless both models pass all configured acceptance gates.
"""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import subprocess
import re

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error

from experiment_validation import (ValidationError, require, load_json, verified_file,
                                   finite_number, sha256)

from statement_timing import TIMING_FIELDS, DURATION_FIELDS, bind_training_rows

FEATURE_LIST = [
    'cpu_util_avg_1min', 'cpu_util_avg_5min', 'cpu_trend', 'mem_used_pct',
    'frag_file_count', 'candidate_small_files', 'table_size_mb', 'avg_file_size_kb',
    'intensity', 'q_0', 'q_1', 'q_2', 'q_3',
]
QUERY_IDS = (0, 1, 2, 3)  # Vocabulary of the four existing workload SQL templates.
SPLITS = ('train', 'calibration', 'test')


def validate_protocol(protocol):
    require(protocol.get('schema_version') == 'physical_training_protocol_v1', 'Unsupported training protocol.')
    require(isinstance(protocol.get('rationale'), str) and protocol['rationale'].strip(),
            'Declare protocol/sample-size/acceptance rationale before evaluation.')
    alpha = finite_number(protocol.get('alpha'), 'alpha')
    require(0 < alpha < 1, 'alpha must be in (0,1).')
    for name in ('min_queries_per_split_per_query', 'min_compaction_events_per_split'):
        value = protocol.get(name)
        require(isinstance(value, int) and not isinstance(value, bool) and value > 0, f'Declare positive {name}.')
    window = finite_number(protocol.get('feature_window_seconds'), 'feature_window_seconds', positive=True)
    purge = finite_number(protocol.get('purge_seconds'), 'purge_seconds')
    require(purge >= window, 'Purge gap must cover the largest telemetry feature window.')
    for name in ('minimum_test_coverage', 'minimum_relative_mae_improvement'):
        value = finite_number(protocol.get(name), name)
        require(0 <= value <= 1, f'{name} must be a fraction in [0,1].')
    require(protocol['minimum_test_coverage'] >= 1 - alpha,
            'Acceptance coverage must not weaken the declared nominal target.')
    limits = protocol.get('maximum_test_mae_ms_by_query', {})
    require(set(limits) == {str(q) for q in QUERY_IDS}, 'Declare an MAE limit for every supported query.')
    for q, value in limits.items():
        finite_number(value, f'MAE limit for query {q}', positive=True)
    params = protocol.get('model_parameters', {})
    require({'n_estimators', 'max_depth', 'learning_rate', 'loss', 'random_state'} <= set(params),
            'Declare model hyperparameters and reproducibility seed.')
    require(isinstance(params['random_state'], int) and not isinstance(params['random_state'], bool),
            'Use an explicit integer model seed.')


def prepare_training_dataframe(df_input):
    required = set(FEATURE_LIST[:9]) | {
        'measurement_id', 'experiment_id', 'split', 'query_id', 'compaction_active',
        'feature_timestamp', 'query_start_time', 'query_end_time', 'compaction_event_id',
        'query_latency_ms', 'query_latency_during_compaction_ms',
    }
    required |= {'timing_contract'} | {name + '_monotonic_ns' for name in TIMING_FIELDS} | set(DURATION_FIELDS)
    missing = sorted(required - set(df_input))
    require(not missing, f'Missing physical query/event columns: {missing}')
    require(len(df_input) > 0, 'No physical query observations.')
    df = df_input.copy()
    require(df['measurement_id'].notna().all() and df['measurement_id'].is_unique,
            'Every query observation needs a unique measurement_id.')
    require(df['experiment_id'].notna().all() and df['split'].isin(SPLITS).all(), 'Invalid experiment/split identity.')
    require(df['query_id'].isin(QUERY_IDS).all(), 'Unknown or missing query identity.')
    mapping = {True: True, False: False, 'True': True, 'False': False}
    require(df['compaction_active'].map(lambda x: isinstance(x, (bool, np.bool_)) or x in ('True', 'False')).all(),
            'Unknown compaction regime label.')
    df['compaction_active'] = df['compaction_active'].map(mapping)
    for col in ('feature_timestamp', 'query_start_time', 'query_end_time'):
        # New event contract requires ISO timestamps with explicit timezone.
        require(df[col].map(lambda x: isinstance(x, str) and re.search(r'(?:Z|[+-]\d{2}:\d{2})$', x) is not None).all(),
                f'{col} must contain timezone-qualified ISO timestamps.')
        df[col] = pd.to_datetime(df[col], utc=True, errors='raise', format='ISO8601')
    require((df['query_end_time'] > df['query_start_time']).all(), 'Invalid query intervals.')
    require((df['feature_timestamp'] <= df['query_start_time']).all(), 'Post-decision feature leakage.')
    for col in FEATURE_LIST[:9]:
        df[col] = pd.to_numeric(df[col], errors='raise')
        require(np.isfinite(df[col]).all(), f'Nonfinite measured feature {col}; imputation is prohibited.')
    for col in ('cpu_util_avg_1min', 'cpu_util_avg_5min', 'mem_used_pct'):
        require(df[col].between(0, 100).all(), f'Invalid percentage feature {col}.')
    require(df['intensity'].between(0, 1).all(), 'Invalid normalized intensity.')
    for col in ('frag_file_count', 'candidate_small_files'):
        require(((df[col] >= 0) & (df[col] % 1 == 0)).all(), f'Invalid measured file count {col}.')
    require((df['candidate_small_files'] <= df['frag_file_count']).all(), 'Small files exceed total files.')
    require((df[['table_size_mb', 'avg_file_size_kb']] > 0).all().all(), 'Invalid measured table/file size.')
    for q in QUERY_IDS:
        df[f'q_{q}'] = (df['query_id'] == q).astype(float)
    df['target_ms'] = np.where(df['compaction_active'], df['query_latency_during_compaction_ms'], df['query_latency_ms'])
    df['target_ms'] = pd.to_numeric(df['target_ms'], errors='raise')
    require(np.isfinite(df['target_ms']).all() and (df['target_ms'] > 0).all(), 'Invalid physical query target.')
    require(df['timing_contract'].eq('client_submission_v1').all(),
            'Actual client-call timing contract required; historical offsets prohibited.')
    for col in [name + '_monotonic_ns' for name in TIMING_FIELDS] + list(DURATION_FIELDS):
        require(pd.api.types.is_integer_dtype(df[col].dtype) and not pd.api.types.is_bool_dtype(df[col].dtype)
                and df[col].notna().all() and (df[col] >= 0).all(),
                f'{col} must preserve observed integer nanoseconds, not rounded float clocks.')
    request, start, returned, end = (df[name + '_monotonic_ns'] for name in TIMING_FIELDS)
    require(((request <= start) & (start <= returned) & (returned <= end) & (end > start)).all(),
            'Invalid monotonic call/result ordering.')
    require((df['client_elapsed_ns'] == end - start).all()
            and (df['request_to_result_ns'] == end - request).all()
            and (df['instrumentation_before_execute_ns'] == start - request).all(),
            'Physical timing decomposition mismatch.')
    require(np.array_equal(df['client_elapsed_ns'].to_numpy(), np.rint(df['target_ms'].to_numpy() * 1_000_000)),
            'Target latency differs from the actual monotonic call/result interval.')
    return df


def validate_splits_and_events(df, events, protocol):
    required = {'experiment_id', 'compaction_event_id', 'start_time', 'end_time', 'rewritten_data_files_count', 'status'}
    require(required <= set(events), 'Missing physical compaction-event evidence.')
    require(events[list(required)].notna().all().all(), 'Incomplete compaction events.')
    require(not events.duplicated(['experiment_id', 'compaction_event_id']).any(), 'Duplicate compaction events.')
    events = events.copy()
    require(events['status'].isin(('success', 'no_op')).all(), 'Failed/unknown rewrite events cannot validate training labels.')
    for col in ('start_time', 'end_time'):
        require(events[col].map(lambda x: isinstance(x, str) and re.search(r'(?:Z|[+-]\d{2}:\d{2})$', x) is not None).all(),
                f'Event {col} requires timezone-qualified ISO timestamps.')
        events[col] = pd.to_datetime(events[col], utc=True, errors='raise', format='ISO8601')
    require((events['end_time'] > events['start_time']).all(), 'Invalid rewrite interval.')
    rewrites = pd.to_numeric(events['rewritten_data_files_count'], errors='raise')
    require(np.isfinite(rewrites).all() and (rewrites >= 0).all() and (rewrites % 1 == 0).all(),
            'Invalid rewritten-file counts.')
    events['rewritten_data_files_count'] = rewrites
    require(((events['status'] == 'success') == (rewrites > 0)).all(), 'Rewrite status/count inconsistency.')
    for _, row in df.iterrows():
        overlap = events[(events['experiment_id'] == row['experiment_id'])
                         & (events['start_time'] < row['query_end_time'])
                         & (events['end_time'] > row['query_start_time'])]
        if row['compaction_active']:
            require(len(overlap) == 1 and overlap.iloc[0]['status'] == 'success'
                    and overlap.iloc[0]['compaction_event_id'] == row['compaction_event_id'],
                    'Compaction label lacks one matching useful rewrite interval.')
        else:
            require(overlap.empty and pd.isna(row['compaction_event_id']),
                    'Baseline query overlaps rewrite or carries a rewrite event ID.')
    groups = {split: df[df['split'] == split] for split in SPLITS}
    require(all(len(g) for g in groups.values()), 'All three disjoint splits must be populated.')
    for left, right in zip(SPLITS, SPLITS[1:]):
        require(groups[left]['query_end_time'].max() + pd.Timedelta(seconds=protocol['purge_seconds'])
                <= groups[right]['feature_timestamp'].min(), 'Chronological split/purge gap violated.')
    for experiment, group in df.groupby('experiment_id'):
        require(group['split'].nunique() == 1, f'Experiment {experiment} appears in multiple splits.')
    # A rewrite event cannot supply labels on both sides of a split.
    for _, group in df[df['compaction_active']].groupby(['experiment_id', 'compaction_event_id']):
        require(group['split'].nunique() == 1, 'Compaction event leakage across splits.')
    for regime in (True, False):
        for split in SPLITS:
            part = df[(df['split'] == split) & (df['compaction_active'] == regime)]
            counts = part.groupby('query_id').size()
            require(all(counts.get(q, 0) >= protocol['min_queries_per_split_per_query'] for q in QUERY_IDS),
                    f'Insufficient query coverage for regime={regime}, split={split}.')
            if regime:
                require(part[['experiment_id', 'compaction_event_id']].drop_duplicates().shape[0]
                        >= protocol['min_compaction_events_per_split'], f'Insufficient independent rewrite events in {split}.')
            if split == 'calibration':
                blocks = part['experiment_id'].nunique()
                require(math.ceil((blocks + 1) * (1 - protocol['alpha'])) <= blocks,
                        'Too few calibration experiment blocks for a finite requested conformal order statistic.')


def train_conformal_model(X_train, y_train, X_calib, y_calib, *, alpha, model_parameters, calibration_groups):
    require(len(y_train) > 0 and len(y_calib) > 0, 'Empty train/calibration split.')
    require(len(calibration_groups) == len(y_calib), 'Calibration groups must match measurements.')
    pipeline = Pipeline([('scaler', StandardScaler()), ('model', GradientBoostingRegressor(**model_parameters))])
    pipeline.fit(X_train, y_train)
    residuals = np.abs(np.asarray(y_calib) - pipeline.predict(X_calib))
    require(np.isfinite(residuals).all(), 'Nonfinite calibration residuals.')
    scores = pd.Series(residuals).groupby(np.asarray(calibration_groups), sort=False).max().to_numpy()
    rank = math.ceil((len(scores) + 1) * (1 - alpha))
    require(rank <= len(scores), 'Requested conformal bound is not finite with these experiment blocks.')
    return pipeline, float(np.sort(scores)[rank - 1])


def train_and_save_models(df, model_dir, *, protocol, compaction_events, provenance):
    original_hashes = {name: sha256(path) for name, path in provenance.items()}
    validate_protocol(protocol)
    prepared = prepare_training_dataframe(df)
    raw_paths = [path for name, path in provenance.items() if name.startswith('raw_statement_events_')]
    require(bool(raw_paths), 'Raw statement event ledgers are required before any model fitting.')
    bind_training_rows(prepared, raw_paths)
    validate_splits_and_events(prepared, compaction_events, protocol)
    require(all(sha256(path) == original_hashes[name] for name, path in provenance.items()),
            'Registered inputs changed during validation; refuse fitting.')
    destination = Path(model_dir).resolve()
    require(not destination.exists(), 'Use a new model directory; never overwrite earlier evidence.')
    fitted, metadata = {}, {'schema_version': 'validated_cost_models_v1', 'validation_status': 'accepted',
                            'features': FEATURE_LIST, 'alpha': protocol['alpha'],
                            'code_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                cwd=Path(__file__).resolve().parents[2], text=True).strip()}
    for name, regime in [('model_a', True), ('model_b', False)]:
        parts = {s: prepared[(prepared['split'] == s) & (prepared['compaction_active'] == regime)] for s in SPLITS}
        train, calib, test = (parts[s] for s in SPLITS)
        model, bound = train_conformal_model(train[FEATURE_LIST], train['target_ms'], calib[FEATURE_LIST],
                                            calib['target_ms'], alpha=protocol['alpha'],
                                            model_parameters=protocol['model_parameters'],
                                            calibration_groups=calib['experiment_id'])
        preds = model.predict(test[FEATURE_LIST])
        require(np.isfinite(preds).all(), f'{name} produced nonfinite predictions.')
        detail = {}
        for q in QUERY_IDS:
            mask = test['query_id'] == q
            actual, predicted = test.loc[mask, 'target_ms'], preds[mask.to_numpy()]
            mae = float(mean_absolute_error(actual, predicted))
            coverage = float(np.mean(np.abs(actual.to_numpy() - predicted) <= bound))
            median = float(train.loc[train['query_id'] == q, 'target_ms'].median())
            baseline_mae = float(np.mean(np.abs(actual.to_numpy() - median)))
            improvement = (baseline_mae - mae) / baseline_mae if baseline_mae > 0 else (0.0 if mae == 0 else -math.inf)
            detail[str(q)] = {'mae_ms': mae, 'coverage': coverage, 'n': int(mask.sum()), 'median_baseline_mae_ms': baseline_mae}
            require(mae <= protocol['maximum_test_mae_ms_by_query'][str(q)]
                    and coverage >= protocol['minimum_test_coverage']
                    and improvement >= protocol['minimum_relative_mae_improvement'],
                    f'{name} query {q} failed preregistered acceptance: {detail[str(q)]}')
        fitted[name] = model
        metadata[name] = {'q_hat': bound, 'acceptance_passed': True, 'per_query_metrics': detail,
                          'calibration_unit': 'maximum absolute residual per experiment block',
                          'split_samples': {s: len(part) for s, part in parts.items()}}
    # Only publish a complete, accepted, self-contained bundle after every gate.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.training-') as temp:
        staging = Path(temp) / 'bundle'
        staging.mkdir()
        for name, source in provenance.items():
            require(sha256(source) == original_hashes[name], f'Input changed during training: {source}')
            target = staging / f'{name}{Path(source).suffix}'
            shutil.copyfile(source, target)
            metadata[name] = {'path': target.name, 'sha256': sha256(target)}
            require(metadata[name]['sha256'] == original_hashes[name], f'Input changed during evidence copy: {source}')
        metadata['execution_evidence'] = [value for name, value in metadata.items()
                                          if name.startswith(('execution_evidence_', 'raw_statement_events_'))]
        for name, model in fitted.items():
            target = staging / ('model_a_compaction.joblib' if name == 'model_a' else 'model_b_baseline.joblib')
            joblib.dump(model, target)
            metadata[name]['artifact'] = {'path': target.name, 'sha256': sha256(target)}
        (staging / 'model_metadata.json').write_text(json.dumps(metadata, indent=2, allow_nan=False))
        require(not destination.exists(), 'Model directory appeared during training; refusing overwrite.')
        os.rename(staging, destination)
    return fitted['model_a'], fitted['model_b'], metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--data-manifest', required=True)
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--model-dir', '--output-dir', dest='model_dir', required=True)
    args = parser.parse_args()
    try:
        declaration, base = load_json(args.data_manifest)
        require(declaration.get('schema_version') == 'physical_training_data_v1'
                and declaration.get('origin') == 'physical_spark_iceberg', 'Only declared physical measurements are allowed.')
        source = verified_file(declaration.get('training_data'), base)
        require(source == Path(args.input).resolve(), 'Input differs from registered training dataset.')
        event_path = verified_file(declaration.get('compaction_events'), base)
        evidence = declaration.get('execution_evidence')
        require(isinstance(evidence, list) and evidence, 'Physical execution evidence is required.')
        evidence_paths = [verified_file(item, base) for item in evidence]
        raw_specs = declaration.get('raw_statement_events')
        require(isinstance(raw_specs, list) and raw_specs, 'Declare raw statement-event JSONL artifacts.')
        raw_paths = [verified_file(item, base) for item in raw_specs]
        protocol, _ = load_json(args.protocol)
        frame, events = pd.read_csv(source), pd.read_csv(event_path)
        require(sha256(source) == declaration['training_data']['sha256']
                and sha256(event_path) == declaration['compaction_events']['sha256'],
                'Registered measurements changed while being read.')
        train_and_save_models(frame, args.model_dir, protocol=protocol,
                              compaction_events=events, provenance={
                                  'training_data': source, 'compaction_events': event_path,
                                  'training_protocol': Path(args.protocol), 'data_manifest': Path(args.data_manifest),
                                  **{f'execution_evidence_{i}': path for i, path in enumerate(evidence_paths)},
                                  **{f'raw_statement_events_{i}': path for i, path in enumerate(raw_paths)}})
    except Exception as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps({'status': 'accepted', 'model_dir': args.model_dir}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
