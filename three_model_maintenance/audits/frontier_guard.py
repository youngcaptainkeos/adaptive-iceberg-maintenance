"""Regression of submission gate against all actual queries from the failed run."""
import argparse
import ast
import hashlib
import importlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/phase6-live-evaluation'))
from three_model_maintenance.runtime.submission import sample_age_reason
from three_model_maintenance.contracts import require


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(config):
    cfg = json.loads(config.read_text()); base = config.parent
    def checked(spec):
        path = (base / spec['path']).resolve(); require(sha(path) == spec['sha256'], 'Changed real regression evidence'); return path
    events_path = checked(cfg['events']); prior_path = checked(cfg['prior_diagnosis']); physical_cfg = checked(cfg['physical_config'])
    expected = json.loads(prior_path.read_text()); original = json.loads(physical_cfg.read_text())
    require(expected['events_sha256'] == sha(events_path) and expected['physical_attempt_status'] == 'failed_preserved', 'Missing actual failed evidence')
    rows = [json.loads(s) for s in events_path.open()]
    observations = {e['measurement_id']: e for e in rows if e['kind'] == 'query_observation'}
    rejected = set(); checked_count = 0
    for event in rows:
        if event['kind'] != 'statement_completed' or event['role'] != 'trace_query':continue
        checked_count += 1; observation = observations[event['measurement_id']]
        reason = sample_age_reason(event['client_execute_start']['monotonic_ns'],
                                   [w['last_available_sample_end_monotonic_ns'] for w in observation['windows']],
                                   int(original['telemetry']['max_age_seconds'] * 1e9))
        if reason is not None:
            require(reason == 'stale_sample_before_rpc', 'Unexpected historical rejection reason')
            rejected.add(event['measurement_id'])
    expected_ids = {v['measurement_id'] for v in expected['violations'] if v['role'] == 'trace_query'}
    require(rejected == expected_ids and checked_count == expected['completed_calls']['trace_query'], 'Guard differs from actual independent diagnosis')
    for spec in cfg['sources']:
        source = checked(spec); ast.parse(source.read_text(), filename=str(source))
    importlib.import_module('three_model_maintenance.runtime.collect')
    require(sha(events_path) == cfg['events']['sha256'], 'Raw evidence changed')
    result = {'status': 'passed_real_failed_frontier_regression_only', 'actual_queries': checked_count,
              'rejected_actual_stale_queries': sorted(rejected), 'allowed_actual_fresh_queries': checked_count - len(rejected),
              'source_sample_limit_seconds': original['telemetry']['max_age_seconds'],
              'guard_source_sha256': sha(ROOT / 'three_model_maintenance/runtime/submission.py'),
              'events_sha256': sha(events_path), 'protocol_sha256': sha(config), 'sql_submitted': False, 'model_fitted': False,
              'limitations': ['Reevaluates only a pure admission predicate on recorded actual clocks; no counterfactual timing claims.',
                              'New physical branch must be validated on the new experiment; old failure remains failed.']}
    out = (base / cfg['output_directory']).resolve(); out.mkdir(parents=True, exist_ok=False)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--config', type=Path, required=True)
    run(parser.parse_args().config.resolve())
