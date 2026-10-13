#!/usr/bin/env python3
"""Read-only P0 evidence inventory. Never executes queries, writes, or models.

Uses saved physical CSVs and an optional read-only worker3 inventory. Findings
identify blockers; absence of a finding does not certify scientific validity.
Exit 2 means blockers were found, exit 0 means this bounded audit found none.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from datetime import datetime, timezone


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def training_summary(path, root):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        rows = list(reader)
    times = [float(row['elapsed_s']) for row in rows if row.get('elapsed_s')]
    queries = [row for row in rows if row.get('query_id')]
    return {
        'path': str(path.relative_to(root)), 'sha256': digest(path),
        'rows': len(rows), 'columns': columns,
        'elapsed_s': times[-1] if times else None,
        'median_sampling_s': statistics.median(b - a for a, b in zip(times, times[1:]))
        if len(times) > 1 else None,
        'queries_with_id': len(queries),
        'compaction_labelled_queries': sum(row.get('compaction_active') == 'True'
                                         for row in queries),
        'missing_event_columns': sorted({'query_start_time', 'query_end_time',
                                        'compaction_event_id'} - set(columns)),
    }


def audit(root, remote):
    findings = []

    def blocker(code, description, path=None, line=None):
        findings.append({'severity': 'blocker', 'code': code,
                         'description': description, 'path': path, 'line': line})

    # These are source-code patterns, not experiment or decision parameters.
    rules = {
        'scripts/phase6-live-evaluation/google_trace_mapper.py': [
            ('SYNTHETIC_TRACE_FALLBACK', 'diurnal =',
             'Missing workload trace silently selects a synthetic demand curve.')],
        'scripts/phase6-live-evaluation/train_cost_benefit_models.py': [
            ('FABRICATED_COMPACTION_LABELS', "df_synth['query_latency_during_compaction_ms']",
             'Training can invent compaction targets from baseline latency.'),
            ('FILENAME_CONTROLS_VALIDITY', 'is_test_run = "test"',
             'Input filename activates relaxed/synthetic training behavior.'),
            ('TRAIN_CALIBRATION_TEST_REUSE', 'X_calib_a, y_calib_a = X_a, y_a',
             'Small-sample path reuses training observations for calibration and test.'),
            ('FIXED_CALIBRATION_BOUND', 'q_hat = 50.0',
             'A fixed bound substitutes for missing or zero calibration evidence.')],
        'scripts/phase6-live-evaluation/run_cost_benefit_agent.py': [
            ('FIXED_FRAGMENTATION_PROJECTION', "t_defer['frag_file_count']",
             'Projection adds a fixed file increment without measured ingestion dynamics.'),
            ('SAMPLE_BASED_CPU_WINDOW', 'cpu_1min = np.mean',
             'Live CPU windows count decision ticks rather than elapsed seconds.'),
            ('QUERY_EVIDENCE_DISCARDED', 'read_driver.completed_queries.clear()',
             'Evaluation clears per-query evidence after reporting interval summaries.')],
        'scripts/phase6-live-evaluation/collect_training_data.py': [
            ('COMPLETION_TIME_REGIME_LABEL', 'lat_compaction = lat_ms if compaction_active',
             'Completion collection flag replaces actual query/compaction temporal overlap.'),
            ('METADATA_FAILURE_AS_HEALTHY_STATE', 'return {"frag_file_count": 0',
             'Unavailable metadata is represented as a zero-file table.')],
        'run_everything.sh': [
            ('STALE_POLICY_LAUNCHER', '--policy SOTAThresholdPolicy',
             'Master launcher requests a policy rejected by the current agent CLI.')],
    }
    for name, checks in rules.items():
        path = root / name
        if not path.exists():
            blocker('MISSING_SOURCE', 'Expected pipeline source is missing.', name)
            continue
        lines = path.read_text().splitlines()
        for code, pattern, description in checks:
            match = next((i for i, line in enumerate(lines, 1) if pattern in line), None)
            if match is not None:
                blocker(code, description, name, match)

    trace = root / 'datasets/google_binned_events.csv'
    if not trace.exists():
        blocker('MISSING_TRACE', 'Configured default workload trace is absent.',
                str(trace.relative_to(root)))

    runs = [training_summary(path, root) for path in sorted(
        (root / 'results/runs').glob('run_*/data/training_data.csv'))]
    for run in runs:
        if run['missing_event_columns']:
            blocker('INCOMPLETE_EVENT_PROVENANCE',
                    'CSV lacks query intervals/maintenance linkage; overlap cannot be verified.',
                    run['path'])
        if 'query_id' not in run['columns']:
            blocker('LEGACY_QUERY_SCHEMA', 'Historical training CSV has no query identity.',
                    run['path'])

    metadata_path = root / 'scripts/phase6-live-evaluation/models/model_metadata.json'
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else None
    if metadata is None or not {'q_0', 'q_1', 'q_2', 'q_3'}.issubset(metadata.get('features', [])):
        blocker('LEGACY_DEFAULT_MODELS', 'Default model artifacts lack query-aware features.',
                str(metadata_path.relative_to(root)))

    comparison = None
    if remote:
        hashes = remote['source_sha256']
        missing = sorted(name for name in hashes if not (root / name).exists())
        different = sorted(name for name, sha in hashes.items()
                           if (root / name).is_file() and digest(root / name) != sha)
        comparison = {'observed_at': remote['observed_at'], 'head': remote['head'],
                      'remote_sources': len(hashes), 'remote_only_sources': missing,
                      'source_sha256': hashes,
                      'differing_sources': different, 'trace_exists': remote['trace_exists'],
                      'runs': remote['runs'], 'status': remote['status']}
        if missing or different:
            blocker('LOCAL_REMOTE_DIVERGENCE',
                    f'{len(missing)} remote sources absent locally; {len(different)} differ. '
                    'Matching Git HEAD does not establish workspace identity.')
        if not remote['trace_exists']:
            blocker('REMOTE_MISSING_TRACE', 'Default workload trace is absent on worker3.')

    return {
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Source patterns, saved CSV schema, model metadata, optional remote source hashes. '
                 'No live benchmark executed; physical origin and scientific claims are not certified.',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'status': 'BLOCKED' if findings else 'NO_BLOCKERS_FOUND_IN_BOUNDED_AUDIT',
        'findings': findings, 'local_training_artifacts': runs,
        'default_model_metadata': metadata, 'remote_snapshot': comparison,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--remote-inventory', type=Path)
    args = parser.parse_args()
    remote = json.loads(args.remote_inventory.read_text()) if args.remote_inventory else None
    report = audit(args.repo.resolve(), remote)
    print(json.dumps(report, indent=2))
    return 2 if report['findings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
