#!/usr/bin/env python3
"""Inventory every retained isolated SF1 attempt; never approve training or drop failures."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(results_directory, output):
    root = Path(results_directory).resolve()
    files = sorted(root.glob('sf1_*/events.jsonl'))
    if not files or Path(output).exists():
        raise ValueError('Actual evidence required; refuse output overwrite')
    attempts = []
    for path in files:
        before = digest(path)
        raw = path.read_bytes()
        if not raw.endswith(b'\n'):
            raise ValueError('Incomplete raw record; preserve and revisit: ' + str(path))
        rows = [json.loads(line) for line in raw.splitlines()]
        identities = {r['experiment_id'] for r in rows}
        if len(identities) != 1 or any(r['schema_version'] != 'physical_event_v1' for r in rows):
            raise ValueError('Mixed episode scope')
        protocols = [r for r in rows if r['kind'].endswith('_protocol')]
        if len(protocols) != 1:
            raise ValueError('Ambiguous protocol')
        protocol = protocols[0]
        cfg = protocol.get('configuration', protocol.get('config'))
        if not isinstance(cfg, dict):
            raise ValueError('Missing actual protocol')
        if cfg.get('purpose') not in ('physical_correctness_only', 'physical_matching_and_feature_integrity_only'):
            raise ValueError('Non-diagnostic protocol outside this inventory contract')
        requested = [r for r in rows if r['kind'] == 'statement_requested']
        completed = [r for r in rows if r['kind'] == 'statement_completed']
        failed = [r for r in rows if r['kind'] == 'statement_failed']
        for records in (requested, completed, failed):
            if len({r['measurement_id'] for r in records}) != len(records):
                raise ValueError('Duplicate statement identity')
        requests = {r['measurement_id'] for r in requested}
        outcomes = {r['measurement_id'] for r in completed + failed}
        if len(outcomes) != len(completed) + len(failed) or not outcomes <= requests:
            raise ValueError('Conflicting or unrequested outcomes')
        failures = [r for r in rows if r['kind'] in ('pilot_failed', 'matched_pilot_failed', 'preparation_failed')]
        accepted = [r for r in rows if r['kind'] in ('pilot_accepted', 'matched_pilot_accepted', 'preparation_accepted')]
        result_path = path.parent / 'result.json'
        if accepted and failures or len(accepted) > 1 or len(failures) > 1:
            raise ValueError('Conflicting terminal episode evidence')
        result_hash = None
        if result_path.exists():
            result_hash = digest(result_path)
            result = json.loads(result_path.read_text())
            if len(accepted) != 1 or any(accepted[0].get(k) != v for k, v in result.items()):
                raise ValueError('Result does not bind raw terminal record')
            status = result['status']
        else:
            status = 'failed_preserved' if failures else 'unresolved_no_result'
        if status not in ('accepted_correctness_source', 'accepted_physical_correctness_pilot',
                          'accepted_matched_measurement_integrity_only', 'failed_preserved', 'unresolved_no_result'):
            raise ValueError('Unknown terminal contract; do not silently classify training')
        if accepted and requests != outcomes:
            raise ValueError('Accepted episode has unfinished statement')
        maintenance = [r for r in requested if 'rewrite_data_files' in r['sql'].lower()]
        attempts.append({'directory': path.parent.name, 'experiment_id': next(iter(identities)),
                         'reported_terminal_status': status, 'code_revision': protocol['code_revision'],
                         'events_sha256': before, 'result_sha256': result_hash,
                         'statement_requests': len(requested), 'statement_completions': len(completed),
                         'statement_failures': len(failed), 'unfinished_measurement_ids': sorted(requests - outcomes),
                         'physical_rewrite_attempts': len(maintenance),
                         'query_ids': sorted({r['query_id'] for r in requested if isinstance(r.get('query_id'), int)}),
                         'timing_contracts': dict(Counter(r.get('timing_contract', 'historical_unspecified') for r in completed)),
                         'pre_action_observation_count': sum(r['kind'] == 'maintenance_decision_observation' for r in rows),
                         'decision_feature_contract': cfg.get('decision_feature_contract'),
                         'decision_state_contract': cfg.get('decision_state_contract'),
                         'failures': [{'error_type': r.get('error_type'), 'error': r.get('error'), 'table': r.get('table')} for r in failures],
                         'training_accepted': False})
        if digest(path) != before or result_hash is not None and digest(result_path) != result_hash:
            raise ValueError('Evidence changed during inventory')
    report = {'schema_version': 'isolated_sf1_attempt_inventory_v1',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'audit_code_sha256': digest(Path(__file__)),
              'scope': 'All retained results/sf1_*/events.jsonl packages. Source preparation, failed and repaired correctness, and matched diagnostics are distinct; excluded historical RUN_* and observation-only directories are outside this scope.',
              'attempt_count': len(attempts), 'status_counts': dict(Counter(a['reported_terminal_status'] for a in attempts)),
              'accepted_training_episode_count': sum(a['training_accepted'] for a in attempts), 'attempts': attempts,
              'limitations': ['Inventories observed evidence only, not a cost schema, variance estimate or training approval.',
                              'Launches refused before evidence-directory creation remain documented in the overnight ledger, outside this raw-event inventory.',
                              'Successful diagnostics must not conceal failed attempts or combine incompatible timing/action-state contracts.']}
    with Path(output).open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'attempt_count': len(attempts), 'status_counts': report['status_counts'], 'accepted_training_episode_count': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-directory', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    inventory(args.results_directory, args.output)
