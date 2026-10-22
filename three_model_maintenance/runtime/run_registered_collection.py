"""Detached serial mapping -> audit -> one physical development episode. No retries."""
import argparse
import ast
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from three_model_maintenance.contracts import require
from three_model_maintenance.preparation.fit_registration import intervals_overlap

REPO = Path(__file__).resolve().parents[2]
LEGACY = REPO / 'scripts/phase6-live-evaluation'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(protocol):
    cfg = json.loads(protocol.read_text()); out = Path(cfg['output_directory'])
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(protocol, out / 'registration.json')
    report = {'status': 'running', 'pid': os.getpid(), 'started_utc': datetime.now(timezone.utc).isoformat(),
              'protocol_sha256': sha(protocol), 'stages': [], 'physical_attempted': False, 'model_fit_performed': False}
    locks = []
    def save():
        (out / 'progress.json').write_text(json.dumps(report, indent=2) + '\n')
    def stage(label, command):
        record = {'label': label, 'command': command, 'started_utc': datetime.now(timezone.utc).isoformat()}
        report['stages'].append(record); save()
        with (out / (label + '.log')).open('x') as stream:
            result = subprocess.run([sys.executable, '-B', str(LEGACY / 'run_with_failure_alert.py'), '--label', cfg['label'] + '_' + label,
                                     '--receipt', str(out / (label + '_failure_alert.json')), '--', *command], cwd=REPO, stdout=stream, stderr=subprocess.STDOUT)
        record.update(returncode=result.returncode, ended_utc=datetime.now(timezone.utc).isoformat()); save()
        require(result.returncode == 0, 'Stage failed: ' + label + '; preserve failed and unattempted work')
    try:
        require(cfg['schema_version'] == 'three_model_live_collection_v1', 'Unknown registration')
        for name in ('.three_model_collection.lock', '.queue_aware_study.lock', '.common_horizon_cohort.lock'):
            lock = (REPO / 'results' / name).open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); locks.append(lock)
        # Physical collector itself acquires .physical_correctness.lock. Probe now,
        # but do not hold an extra descriptor that would compete with that child.
        with (REPO / 'results/.physical_correctness.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.flock(lock, fcntl.LOCK_UN)
        for spec in cfg['source_files']:
            path = REPO / spec['path']; require(sha(path) == spec['sha256'], 'Changed frozen implementation')
            if path.suffix == '.py':ast.parse(path.read_text(), filename=str(path))
        # Imports/constructors already validated in previous real-evidence audit;
        # parse all registered sources before physical work, with no fake cursor.
        if 'frontier_regression' in cfg:
            spec = cfg['frontier_regression']; registration = REPO / spec['path']
            require(sha(registration) == spec['sha256'], 'Regression registration changed')
            stage('frontier_regression', [sys.executable, '-B', '-m', 'three_model_maintenance.audits.frontier_guard', '--config', str(registration)])
            reg_cfg = json.loads(registration.read_text())
            result_path = (registration.parent / reg_cfg['output_directory']).resolve() / 'result.json'
            result = json.loads(result_path.read_text())
            require(result['status'] == 'passed_real_failed_frontier_regression_only' and
                    result['guard_source_sha256'] == sha(REPO / 'three_model_maintenance/runtime/submission.py'), 'Guard regression missing or stale')
            report['frontier_regression_sha256'] = sha(result_path); save()
        if 'prior_verified_export' in cfg:
            spec = cfg['prior_verified_export']; prior = Path(spec['directory'])
            require(sha(prior / 'result.json') == spec['result_sha256'] and sha(prior / 'events.jsonl') == spec['events_sha256'], 'Prior terminal evidence changed')
            stage('prior_live_export', [sys.executable, '-B', '-m', 'three_model_maintenance.preparation.export_live_candidates',
                                        '--directory', str(prior), '--output', spec['output_directory']])
            report['prior_candidate_export_sha256'] = sha(Path(spec['output_directory']) / 'result.json'); save()
        mapping_config = REPO / cfg['mapping_config']['path']
        require(sha(mapping_config) == cfg['mapping_config']['sha256'], 'Mapping registration changed')
        stage('mapping', [sys.executable, '-B', str(LEGACY / 'prepare_trace_benchmark_mapping.py'), '--config', str(mapping_config)])
        mapping_cfg = json.loads(mapping_config.read_text())
        mapping_dir = (mapping_config.parent / mapping_cfg['output_directory']).resolve()
        mapping_audit = mapping_dir / 'source_mapping_audit.json'
        stage('mapping_audit', [sys.executable, '-B', str(LEGACY / 'audit_trace_benchmark_mapping.py'), '--config', str(mapping_config),
                                '--mapping-directory', str(mapping_dir), '--output', str(mapping_audit)])
        mapping_record = mapping_dir / 'mapping_record.json'; mapping = json.loads(mapping_record.read_text())
        registry_path = REPO / cfg['consumed_registry']['path']
        require(sha(registry_path) == cfg['consumed_registry']['sha256'], 'Consumed source registry changed')
        registry = json.loads(registry_path.read_text())
        expanded = {'start_utc': (datetime.fromisoformat(mapping['source_interval_start_utc']) - timedelta(seconds=cfg['source_history_seconds'])).isoformat(),
                    'end_utc': mapping['source_interval_end_utc']}
        require(all(not intervals_overlap(expanded, prior) for prior in registry['consumed_families']), 'Source/history overlaps consumed cost family')
        report['source_registration'] = {'expanded_interval': expanded, 'role': 'engineering_development_only',
                                         'independent_test_accepted': False, 'mapping_sha256': sha(mapping_record)}; save()
        episode = dict(cfg['episode_template'])
        episode['mapping_record'] = {'path': str(mapping_record), 'sha256': sha(mapping_record)}
        episode['mapping_audit'] = {'path': str(mapping_audit), 'sha256': sha(mapping_audit)}
        require(datetime.now(timezone.utc) < datetime.fromisoformat(cfg['no_new_episode_after_utc']), 'Episode cutoff reached')
        path = out / 'physical_registration.json'; path.write_text(json.dumps(episode, indent=2) + '\n')
        for spec in cfg['source_files']:
            require(sha(REPO / spec['path']) == spec['sha256'], 'Implementation changed before physical launch')
        report['physical_registration_sha256'] = sha(path); report['physical_attempted'] = True; save()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
        stage('physical', [sys.executable, '-B', '-m', 'three_model_maintenance.runtime.collect', '--config', str(path), '--expected-revision', revision])
        raw = Path(episode['output_directory']); result = json.loads((raw / 'result.json').read_text())
        require(result['three_model_publication_audit']['status'] == 'verified_live_publication_and_direct_client_state_only', 'Missing real publication audit')
        report.update(status='physical_passed_export_pending', physical_result_sha256=sha(raw / 'result.json'),
                      live_publication=result['three_model_publication_audit'], physical_output_directory=str(raw))
        if cfg.get('export_candidates_after_raw_audit') is True:
            candidate_out = out / 'candidates'
            stage('candidate_export', [sys.executable, '-B', '-m', 'three_model_maintenance.preparation.export_live_candidates',
                                       '--directory', str(raw), '--output', str(candidate_out)])
            candidate_receipt = json.loads((candidate_out / 'result.json').read_text())
            require(candidate_receipt['status'] == 'verified_live_candidate_export_not_fit_authorized', 'Unverified candidate export')
            report['candidate_export_sha256'] = sha(candidate_out / 'result.json')
            report['complete_history_condition_counts'] = candidate_receipt['complete_history_condition_counts']
        observed = report.get('complete_history_condition_counts', report['live_publication']['observed_conditions'])
        report['A_B_support_status'] = ('both_conditions_observed_not_fit_approval' if all(observed.values())
                                        else 'blocked_missing_observed_condition')
        report['status'] = 'completed_one_real_development_measurement_only'
    except Exception as exc:
        report.update(status='failed_preserved_no_retry', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        report['ended_utc'] = datetime.now(timezone.utc).isoformat(); save()
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        for lock in locks:lock.close()
    # Human explicitly authorized ntfy. Success notification is evidence-linked;
    # delivery failure is retained without changing experiment status.
    notice = {'topic': cfg['notification_topic'], 'experiment_status': report['status']}
    try:
        request = urllib.request.Request(cfg['notification_topic'], data=(cfg['label'] + ': completed real development measurement. Observed conditions=' + str(report.get('complete_history_condition_counts', report['live_publication']['observed_conditions'])) + '; ' + report['A_B_support_status'] + '. No models trained.').encode(),
                                         headers={'Title': 'Capstone measurement completed'}, method='POST')
        with urllib.request.urlopen(request, timeout=10) as response:notice.update(delivered=True, http_status=response.status)
    except Exception as exc:notice.update(delivered=False, error=str(exc))
    (out / 'completion_notification.json').write_text(json.dumps(notice, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--protocol', type=Path, required=True)
    run(parser.parse_args().protocol.resolve())
