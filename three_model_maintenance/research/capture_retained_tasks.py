"""Read retained tasks for pinned capture gaps; never repair an old episode in place."""
import argparse
import traceback
import urllib.request
from pathlib import Path
from .common import decode, integer, now, number, read, require, sha, utc, write_new


def validate_tasks(payload, count):
    """Require the actual complete successful first-attempt task population."""
    integer(count, 'task count', 1)
    require(type(payload) is list and len(payload) == count, 'Incomplete task population')
    for task in payload:
        integer(task['taskId'], 'taskId')
        integer(task['index'], 'index')
        require(type(task['attempt']) is int and task['attempt'] == 0, 'Task retry')
        require(task['status'] == 'SUCCESS', 'Unsuccessful task')
        require(number(task['duration'], 'duration') > 0, 'Nonpositive duration')
        launched = task['launchTime']
        require(type(launched) is str and launched.endswith('GMT'), 'Expected Spark UTC timestamp')
        utc(launched[:-3] + '+00:00')
    require(len({t['taskId'] for t in payload}) == count, 'Duplicate task IDs')
    require({t['index'] for t in payload} == set(range(count)), 'Incomplete task indices')


def run(protocol, output):
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='running', started_utc=now(), protocol_sha256=sha(protocol),
                  captured_stage_attempts=0, captured_tasks=0, SQL_executed=False,
                  physical_episode_accepted=False, original_raw_modified=False,
                  evidence_scope='post_hoc_retained_REST_capability_only')
    try:
        cfg = read(protocol)
        require(cfg['schema'] == 'retained_task_capture_capability_v1', 'Unknown protocol')
        require(utc(now()) < utc(cfg['latest_start_utc']), 'Start cutoff expired')
        root = Path(__file__).resolve().parents[2]
        def verify():
            for name, digest in cfg['code_sha256'].items():
                require(sha(root / name) == digest, 'Code changed: ' + name)
            for name, spec in cfg['inputs'].items():
                require(sha(spec['path']) == spec['sha256'], 'Input changed: ' + name)
            require(sha(protocol) == report['protocol_sha256'], 'Protocol changed')
        verify()
        gaps = read(cfg['inputs']['gaps']['path'])
        rows = gaps['complete_stage_attempts_without_complete_saved_tasks']
        prior = read(cfg['inputs']['receipt']['path'])
        require(prior['status'] == 'passed_exact_ownership_regression_capture_gaps_diagnostic_only', 'Dependency failed')
        require(len(rows) == cfg['expected_stage_attempts'] == prior['complete_stage_attempts_missing_saved_tasks'], 'Gap population differs')
        require(len({(r['stage_id'], r['attempt_id']) for r in rows}) == len(rows), 'Duplicate stage attempts')
        require(cfg['base_url'] == 'http://127.0.0.1:4051', 'Unregistered endpoint')
        for row in sorted(rows, key=lambda r: (r['stage_id'], r['attempt_id'])):
            require(utc(now()) < utc(cfg['latest_request_utc']), 'Request cutoff expired')
            sid = integer(row['stage_id'], 'stage ID')
            attempt = integer(row['attempt_id'], 'stage attempt')
            count = integer(row['num_tasks'], 'num tasks', 1)
            require(attempt == 0, 'Stage retry')
            resource = f'stages/{sid}/{attempt}/taskList?length={count}'
            record = dict(resource=resource, request_start=now(), stage_id=sid, attempt_id=attempt)
            try:
                url = cfg['base_url'] + '/api/v1/applications/' + cfg['app_id'] + '/' + resource
                with urllib.request.urlopen(url, timeout=cfg['timeout_seconds']) as response:
                    body = response.read()
                    (output / f'{sid}_{attempt}.raw.json').write_bytes(body)
                    record['http_status'] = response.status
                record['response_end'] = now()
                record['raw_sha256'] = sha(output / f'{sid}_{attempt}.raw.json')
                validate_tasks(decode(body), count)
                record['status'] = 'passed_task_population_only'
            except Exception as exc:
                record.update(status='failed_preserved', error=str(exc), response_end=now())
                raise
            finally:
                write_new(output / f'{sid}_{attempt}.receipt.json', record)
            report['captured_stage_attempts'] += 1
            report['captured_tasks'] += count
        verify()
        report['status'] = 'passed_retained_task_capture_capability_only'
        report['limitations'] = ['Post-hoc reads do not satisfy the original acquisition deadline.',
                                'Missing and skipped stage references remain unresolved.',
                                'No prospective collector integration or metric benefit established.']
    except Exception as exc:
        report.update(status='failed_preserved', error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        report['ended_utc'] = now()
        write_new(output / 'result.json', report)
        print(report, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    run(args.protocol, args.output)
