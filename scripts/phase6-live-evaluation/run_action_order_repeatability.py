#!/usr/bin/env python3
"""Sequential preregistered real episodes; audit each before the next, stop on any gate failure."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from experiment_validation import load_json, require, verified_file, sha256


def run(config_path, expected_revision):
    cfg, base = load_json(config_path)
    repo = Path(__file__).resolve().parents[2]
    require(cfg['schema_version'] == 'action_order_repeatability_pilot_v1'
            and cfg['purpose'] == 'diagnostic_repeatability_only_no_training', 'Unreviewed cohort')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
            == expected_revision, 'Full cohort revision differs')
    require(subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', 'scripts/phase6-live-evaluation/*.py'],
                           cwd=repo, capture_output=True).returncode == 0, 'Dirty cohort Python')
    episodes = [verified_file(spec, base) for spec in cfg['episode_configs']]
    settings = [json.loads(p.read_text()) for p in episodes]
    require(len(settings) == len(cfg['registered_order']) and len({c['experiment_id'] for c in settings}) == len(settings)
            and len({c['destination_table'] for c in settings}) == len(settings), 'Duplicate/incomplete episode registration')
    require([c['action_order'] for c in settings] == cfg['registered_order'], 'Episode order changed')
    require(all(c['query_id'] == cfg['query_id'] and c['no_new_operation_after_utc'] == cfg['no_new_operation_after_utc']
                and c['session_roles'] == ['metadata', 'maintenance', 'query'] for c in settings), 'Mixed cohort scope')
    common = ('source', 'generator_provenance', 'preparation_result', 'engine', 'spark_app_id',
              'spark_rest_url', 'telemetry', 'layout', 'rewrite_options', 'decision_feature_contract',
              'decision_state_contract', 'metadata_max_age_seconds')
    require(all(all(c[k] == settings[0][k] for k in common) for c in settings), 'Non-order condition changed')
    lock = (repo / 'results' / '.action_order_repeatability.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    output = (base / cfg['output_directory']).resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(config_path, output / 'config.json')
    code = output / 'code'
    code.mkdir()
    for p in Path(__file__).parent.glob('*.py'):
        # Freeze the tracked code used by runner and independent export, no archive.
        if p.name in ('run_action_order_repeatability.py', 'run_matched_measurement_pilot.py',
                      'export_matched_observations.py', 'action_order_binding.py', 'experiment_validation.py',
                      'physical_measurements.py', 'run_correctness_pilot.py', 'engine_overlap.py',
                      'query_observation_binding.py', 'statement_timing.py', 'telemetry_binding.py', 'engine_label_binding.py'):
            shutil.copy2(p, code / p.name)
    shutil.copy2(Path(__file__).parent/'review_action_order_repeatability.py',code/'review_action_order_repeatability.py')
    deadline = datetime.fromisoformat(cfg['no_new_operation_after_utc'])
    report = {'schema_version': cfg['schema_version'], 'status': 'running', 'code_revision': expected_revision,
              'started_utc': datetime.now(timezone.utc).isoformat(), 'attempts': [],
              'code_sha256': {p.name: sha256(p) for p in code.iterdir()},
              'scope': 'Bounded real SF1 order/repeatability diagnostics; no cost training, uncertainty or common-horizon scheduling acceptance.'}
    def checkpoint():
        (output / 'progress.json').write_text(json.dumps(report, indent=2) + '\n')
    checkpoint()
    try:
        for index, (path, episode) in enumerate(zip(episodes, settings), start=1):
            require(datetime.now(timezone.utc) < deadline, 'No new episode after cohort cutoff')
            require(sha256(path)==cfg['episode_configs'][index-1]['sha256'],'Registered episode file changed')
            require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
                    == expected_revision, 'Cohort HEAD changed; refuse dependent episode')
            with urllib.request.urlopen(episode['spark_rest_url'].rstrip('/') + '/api/v1/applications/'
                                        + episode['spark_app_id'] + '/jobs?status=running', timeout=episode['rest_timeout_seconds']) as response:
                jobs = json.load(response)
            require(not jobs, 'Other active Spark work; do not start episode')
            attempt = {'index': index, 'experiment_id': episode['experiment_id'], 'action_order': episode['action_order'],
                       'protocol_sha256': sha256(path), 'started_utc': datetime.now(timezone.utc).isoformat(),
                       'pre_episode_running_spark_jobs': jobs, 'status': 'running',
                       'raw_directory': str((base / episode['output_directory']).resolve())}
            report['attempts'].append(attempt)
            checkpoint()
            with (output / f'episode_{index:02d}.log').open('x') as log:
                result = subprocess.run([sys.executable, str(Path(__file__).parent / 'run_matched_measurement_pilot.py'),
                                         '--config', str(path), '--expected-revision', expected_revision], cwd=repo, stdout=log, stderr=subprocess.STDOUT)
            attempt['returncode'] = result.returncode
            attempt['ended_utc'] = datetime.now(timezone.utc).isoformat()
            require(result.returncode == 0, 'Physical episode failed; preserve and audit before any next episode')
            receipt = Path(attempt['raw_directory']) / 'result.json'
            require(sha256(receipt.parent/'config.json')==attempt['protocol_sha256'],'Executed configuration differs from registration')
            attempt['result_sha256'] = sha256(receipt)
            export = output / f'episode_{index:02d}_export'
            with (output / f'episode_{index:02d}_export.log').open('x') as log:
                checked = subprocess.run([sys.executable, str(Path(__file__).parent / 'export_matched_observations.py'),
                                          '--pilot-directory', attempt['raw_directory'], '--result-sha256', attempt['result_sha256'],
                                          '--output-directory', str(export)], cwd=repo, stdout=log, stderr=subprocess.STDOUT)
            require(checked.returncode == 0, 'Independent raw export failed; refuse dependent episode')
            manifest = json.loads((export / 'export_record.json').read_text())
            require(manifest['action_order_check']['action_order'] == episode['action_order'], 'Raw verified order differs')
            attempt.update(status='passed_measurement_and_raw_export_only', export_directory=str(export),
                           export_record_sha256=sha256(export / 'export_record.json'))
            checkpoint()
            print(json.dumps(attempt), flush=True)
        report['status'] = 'completed_registered_diagnostic_episodes_only'
    except Exception as exc:
        report['status'] = 'stopped_after_failed_gate_preserve_all'
        report['error_type'] = type(exc).__name__
        report['error'] = str(exc)
        if report['attempts'] and report['attempts'][-1]['status'] == 'running':
            report['attempts'][-1]['status'] = 'failed_gate_preserved'
        raise
    finally:
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        checkpoint()
        with (output / 'result.json').open('x') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
        lock.close()
    print(json.dumps({'status': report['status'], 'attempts': len(report['attempts'])}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--expected-revision', required=True)
    args = parser.parse_args()
    run(args.config, args.expected_revision)
