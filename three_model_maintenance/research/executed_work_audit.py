"""Independent saved-raw executed-work audit; never physical acceptance.

No network, SQL, result repair, fitted models or collector changes. Preparation
pins a registration; execution belongs on worker3 through the failure wrapper.
"""
import argparse
import json
import re
import traceback
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlsplit

from .common import integer, now, read, require, sha, utc, write_new
from .capture_retained_tasks import validate_tasks
from .ownership import exact_bindings

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = 'saved_raw_executed_work_audit_v1'
CODE = [
    'three_model_maintenance/__init__.py',
    'three_model_maintenance/research/__init__.py',
    'three_model_maintenance/research/executed_work_audit.py',
    'three_model_maintenance/research/common.py',
    'three_model_maintenance/research/ownership.py',
    'three_model_maintenance/research/capture_retained_tasks.py',
    'scripts/phase6-live-evaluation/run_with_failure_alert.py',
    'scripts/phase6-live-evaluation/failure_notifications.py',
    'docs/experiment_protocols/failure_notifications.json',
    'scripts/launch_executed_work_audit.py',
]


def relative_file(root, name):
    """Require canonical, repository-relative evidence names and no symlinks."""
    require(type(name) is str and name, 'Missing path')
    part = PurePosixPath(name)
    require(not part.is_absolute() and '..' not in part.parts and str(part) == name,
            'Noncanonical evidence path: ' + name)
    path = root / name
    require(path.resolve().is_relative_to(root.resolve()) and path.is_file(),
            'Missing/escaping evidence file: ' + name)
    cursor = path
    while cursor != root:
        require(not cursor.is_symlink(), 'Symlink evidence path: ' + name)
        cursor = cursor.parent
    return path


def spark_time(value):
    require(type(value) is str and value.endswith('GMT'), 'Explicit Spark GMT time required')
    return utc(value[:-3] + '+00:00')


def prepare(reference_protocol, latest_start, output):
    """Copy old evidence pins, bind new code, but perform no scientific audit."""
    require(utc(latest_start) > utc(now()), 'Fresh audit window required')
    reference_protocol = reference_protocol.resolve()
    require(reference_protocol.is_relative_to(ROOT), 'Reference must be in repository')
    ref = read(reference_protocol)
    require(ref['schema'] == 'saved_raw_ownership_history_diagnostic_v1',
            'Unsupported reference registration')
    cfg = dict(schema=CONTRACT, status='registered_not_executed',
               latest_start_utc=latest_start, episode=ref['episode'],
               application_url=ref['application_url'], expected_completed_calls=6,
               expected_calls_rationale='The original capability registered each of six SF10 templates once.',
               inputs=dict(ref['inputs']), code={name: sha(ROOT/name) for name in CODE},
               reference_protocol=str(reference_protocol.relative_to(ROOT)),
               reference_protocol_sha256=sha(reference_protocol),
               rationale='Independently reconstruct raw ownership, observed histories, executed-stage/task counts and task receipts. No old gate is relaxed; dependency gaps remain separate.',
               SQL_allowed=False, REST_allowed=False, physical_acceptance_allowed=False)
    # This binds exactly the old registered bytes; it does not recompute new pins
    # from a possibly changed raw directory, or invent absent evidence.
    write_new(output, cfg)


def audit(cfg):
    require(cfg['schema'] == CONTRACT, 'Unknown executed-work contract')
    require(cfg['SQL_allowed'] is False and cfg['REST_allowed'] is False
            and cfg['physical_acceptance_allowed'] is False, 'Wrong audit scope')
    episode = ROOT/cfg['episode']; archive = episode/'direct_archive'
    require(archive.resolve().is_relative_to(ROOT), 'Archive path escapes repository')
    pins = cfg['inputs']

    def evidence(path):
        name = str(path.relative_to(ROOT))
        require(name in pins, 'Unregistered evidence read: ' + name)
        result = relative_file(ROOT, name)
        require(sha(result) == pins[name], 'Evidence checksum differs: ' + name)
        return read(result)

    events_path = episode/'events.jsonl'
    name = str(events_path.relative_to(ROOT))
    require(name in pins and sha(relative_file(ROOT, name)) == pins[name], 'Unpinned event ledger')
    from .common import decode
    events = [decode(line) for line in events_path.read_text().splitlines()]
    requested = [r for r in events if r['kind'] == 'statement_requested']
    completed = [r for r in events if r['kind'] == 'statement_completed']
    expected = integer(cfg['expected_completed_calls'], 'expected calls', 1)
    require(len(requested) == len(completed) == expected, 'Incomplete offered call population')
    require({r['measurement_id'] for r in requested} ==
            {r['measurement_id'] for r in completed}, 'Call/request populations differ')
    original = evidence(episode/'result.json')
    require(original['status'] != 'running', 'Original episode still running')
    checkpoints = sorted(archive.glob('checkpoint_*'))
    require(checkpoints and all(p.is_dir() and not p.is_symlink() for p in checkpoints),
            'Missing/noncanonical checkpoints')
    require([p.name for p in checkpoints] ==
            [f'checkpoint_{i:05d}' for i in range(1, len(checkpoints)+1)], 'Checkpoint sequence gap')
    # The pin manifest must cover the complete archive tree, including files not
    # consumed by this independent audit. No added raw history may go unnoticed.
    archive_entries = list(archive.rglob('*'))
    require(not any(p.is_symlink() for p in archive_entries), 'Symlink inside archive inventory')
    actual = {str(p.relative_to(ROOT)) for p in archive_entries if p.is_file()}
    registered = {p for p in pins if p.startswith(str(archive.relative_to(ROOT))+'/')}
    require(actual == registered, 'Archive file inventory differs from registration')
    observations = []; task_payloads = {}; final_sql = []; receipt_total = 0
    for cp in checkpoints:
        files = sorted(cp.glob('receipt_*.json'))
        require(files and [p.name for p in files] ==
                [f'receipt_{i:05d}.json' for i in range(len(files))], 'Receipt sequence gap')
        response_paths = set(); pages = []; previous_end = None
        for file in files:
            r = evidence(file); resource = r['resource']
            require(r['url'] == cfg['application_url']+'/'+resource,
                    'Response URL/application/resource mismatch')
            require(r['http_status'] == 200, 'Unsuccessful raw response')
            start = integer(r['request_start_monotonic_ns'], 'request clock')
            end = integer(r['response_end_monotonic_ns'], 'response clock')
            require(start <= end and (previous_end is None or previous_end <= start),
                    'Reversed/overlapping serial archive requests')
            require(utc(r['request_start_utc']) <= utc(r['response_end_utc']), 'Reversed UTC receipt')
            previous_end = end
            raw = archive/r['raw_path']
            require(raw.parent == cp and raw.name == file.name.replace('receipt_', 'response_'),
                    'Response path is not paired with receipt')
            require(str(raw) not in response_paths, 'Duplicate response path')
            response_paths.add(str(raw))
            payload = evidence(raw)
            require(sha(raw) == r['raw_sha256'], 'Receipt/body checksum mismatch')
            if resource.startswith('sql?'):
                q = parse_qs(urlsplit(r['url']).query)
                offset = integer(int(q['offset'][0]), 'SQL offset')
                length = integer(int(q['length'][0]), 'SQL page length', 1)
                require(type(payload) is list and len(payload) <= length, 'Invalid SQL page')
                pages.append((offset, length, payload))
            elif resource in ('jobs', 'stages'):
                require(type(payload) is list, 'Expected engine inventory list')
                observations.append((resource, payload))
            else:
                match = re.fullmatch(r'stages/(\d+)/(\d+)/taskList\?length=(\d+)', resource)
                require(match is not None, 'Unregistered response type: ' + resource)
                sid, attempt, count = map(int, match.groups())
                require(attempt == 0, 'Retried task stage')
                validate_tasks(payload, count)
                key = (sid, attempt)
                require(key not in task_payloads or task_payloads[key] == payload,
                        'Conflicting saved task population')
                task_payloads[key] = payload
            receipt_total += 1
        require(response_paths == {str(p) for p in cp.glob('response_*.json')},
                'Raw response without receipt')
        if cp == checkpoints[-1]:
            terminal_receipt = evidence(cp/'result.json')
            require(terminal_receipt['terminal'] is True, 'Mandatory terminal checkpoint absent')
            require(pages, 'Final SQL pages missing')
            position = 0
            for i, (offset, length, rows) in enumerate(pages):
                require(offset == position, 'SQL pagination offset gap')
                require(len(rows) == length if i < len(pages)-1 else len(rows) < length,
                        'SQL inventory lacks terminal short page')
                final_sql.extend(rows); position += length
    bindings = exact_bindings(requested, completed, final_sql)['bindings']
    job_owner = {}
    for mid, binding in bindings.items():
        require(binding['success_job_ids'], 'Completed SQL has no explicit successful jobs')
        for jid in binding['success_job_ids']:
            require(jid not in job_owner, 'Job shared between measured calls')
            job_owner[jid] = mid
    jobs = {}; references = set(); job_observations = 0
    for resource, rows in observations:
        if resource != 'jobs': continue
        require(len({integer(j['jobId'], 'job ID') for j in rows}) == len(rows), 'Duplicate jobs within frame')
        for job in rows:
            jid = job['jobId']
            if jid not in job_owner: continue
            job_observations += 1
            require(job['status'] in ('RUNNING','SUCCEEDED'), 'Adverse owned job history')
            for field in ('numFailedTasks','numKilledTasks','numFailedStages'):
                require(integer(job[field], field) == 0, 'Failed/killed owned job work')
            ids = job['stageIds']; require(type(ids) is list and ids, 'Missing job stage references')
            require(len({integer(s, 'stage ID') for s in ids}) == len(ids), 'Duplicate job stage reference')
            if jid in jobs:
                require(set(ids) == set(jobs[jid]['stageIds']), 'Owned job reference set changed')
                if jobs[jid]['status'] == 'SUCCEEDED':
                    fields = ('status','submissionTime','completionTime','numCompletedStages',
                              'numSkippedStages','numCompletedTasks','numSkippedTasks','numTasks')
                    require(all(job[f] == jobs[jid][f] for f in fields), 'Terminal job regressed/changed')
            jobs[jid] = job; references.update(ids)
    require(set(jobs) == set(job_owner), 'Missing owned job observation')
    stages = {}; stage_observations = 0
    for resource, rows in observations:
        if resource != 'stages': continue
        keys = [(integer(s['stageId'], 'stage ID'), integer(s['attemptId'], 'attempt ID')) for s in rows]
        require(len(keys) == len(set(keys)), 'Duplicate stage attempts within frame')
        for stage, key in zip(rows, keys):
            if key[0] not in references: continue
            stage_observations += 1
            require(key[1] == 0 and stage['status'] in ('PENDING','ACTIVE','COMPLETE','SKIPPED'),
                    'Adverse/retried stage history')
            for field in ('numFailedTasks','numKilledTasks'):
                require(integer(stage[field], field) == 0, 'Failed/killed referenced stage work')
            if key in stages and stages[key]['status'] in ('COMPLETE','SKIPPED'):
                fields = ('status','numTasks')
                require(all(stage[f] == stages[key][f] for f in fields), 'Terminal stage regressed/changed')
                if stages[key]['status'] == 'COMPLETE':
                    require(stage['submissionTime'] == stages[key]['submissionTime'] and
                            stage['completionTime'] == stages[key]['completionTime'] and
                            stage['numCompleteTasks'] == stages[key]['numCompleteTasks'],
                            'Completed stage evidence changed')
            stages[key] = stage
    require(all(s['status'] in ('COMPLETE','SKIPPED') for s in stages.values()),
            'Observed referenced stage still nonterminal')
    proofs = []; executed_owner = {}; all_task_ids = set(); unknown_occurrences = []
    for jid, job in sorted(jobs.items()):
        require(job['status'] == 'SUCCEEDED', 'Nonterminal owned job')
        lo, hi = spark_time(job['submissionTime']), spark_time(job['completionTime'])
        require(lo <= hi, 'Reversed job interval')
        counts = {f: integer(job[f], f) for f in ('numCompletedStages','numSkippedStages',
                  'numCompletedTasks','numSkippedTasks','numTasks')}
        require(len(job['stageIds']) == counts['numCompletedStages']+counts['numSkippedStages'],
                'Job completed/skipped stage totals differ')
        require(counts['numTasks'] == counts['numCompletedTasks']+counts['numSkippedTasks'],
                'Job completed/skipped task totals differ')
        executed = []; remaining = []
        for sid in job['stageIds']:
            key = (sid, 0); stage = stages.get(key)
            if stage is None:
                remaining.append(dict(stage_id=sid, observed_state=None))
                unknown_occurrences.append(dict(job_id=jid, stage_id=sid))
                continue
            if stage['status'] == 'SKIPPED':
                remaining.append(dict(stage_id=sid, observed_state='SKIPPED')); continue
            start, end = spark_time(stage['submissionTime']), spark_time(stage['completionTime'])
            require(start <= end, 'Reversed completed stage interval')
            if end < lo:
                remaining.append(dict(stage_id=sid, observed_state='COMPLETE',
                                      relation='completed_before_job')); continue
            require(lo <= start <= end <= hi, 'Ambiguous overlapping referenced-stage interval')
            require(key not in executed_owner, 'Executed stage belongs to multiple measured jobs')
            count = integer(stage['numTasks'], 'executed stage tasks', 1)
            require(integer(stage['numCompleteTasks'], 'complete tasks') == count, 'Stage task totals differ')
            require(key in task_payloads, 'Executed stage lacks raw task response')
            tasks = task_payloads[key]; validate_tasks(tasks, count)
            for task in tasks:
                tid = integer(task['taskId'], 'task ID')
                require(tid not in all_task_ids, 'Duplicate executed task across stages/jobs')
                all_task_ids.add(tid)
                launched = spark_time(task['launchTime'])
                require(start <= launched <= end, 'Task launch outside stage interval')
            executed_owner[key] = jid
            executed.append(dict(stage_id=sid, attempt_id=0, tasks=count))
        require(len(executed) == counts['numCompletedStages'], 'Executed stage count differs from job counter')
        require(sum(s['tasks'] for s in executed) == counts['numCompletedTasks'],
                'Executed task count differs from job counter')
        require(len(remaining) == counts['numSkippedStages'], 'Remaining-reference aggregate count differs')
        proofs.append(dict(job_id=jid, measurement_id=job_owner[jid], executed=executed,
                           remaining_references=remaining, remaining_reference_states_imputed=False))
    absent = sorted(references-{sid for sid, _ in stages})
    return dict(executed_work_observed_coverage='complete_under_saved_counter_contract',
                dependency_inventory_complete=not absent, absent_dependency_stage_ids=absent,
                absent_reference_occurrences=unknown_occurrences, calls=len(completed),
                owned_jobs=len(jobs), job_observations=job_observations,
                stage_observations=stage_observations, executed_stages=len(executed_owner),
                executed_tasks=len(all_task_ids), receipts_checked=receipt_total,
                bindings=bindings, job_proofs=proofs, original_result_status=original['status'])


def run(protocol, output):
    output.mkdir(parents=True, exist_ok=False)
    result = dict(schema=CONTRACT, status='running', started_utc=now(),
                  protocol_sha256=sha(protocol), physical_episode_accepted=False,
                  original_failure_accepted=False, training_eligible=False,
                  SQL_executed=False, REST_requested=False)
    lock_stream = None
    try:
        require(ROOT == Path('/mnt/nfs-storage/shashank_prafullathta/implementation'),
                'Execute saved-evidence validation only from the registered worker3 checkout')
        import fcntl
        lock_stream = (ROOT/'results'/'.executed_work_audit.lock').open('a')
        fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cfg = read(protocol)
        require(cfg['status'] == 'registered_not_executed', 'Wrong registration state')
        require(utc(now()) < utc(cfg['latest_start_utc']), 'Audit admission expired')
        def verify():
            require(sha(protocol) == result['protocol_sha256'], 'Protocol changed')
            require(cfg['code'] == {name: sha(ROOT/name) for name in CODE}, 'Code pins differ')
            require(sha(relative_file(ROOT, cfg['reference_protocol'])) ==
                    cfg['reference_protocol_sha256'], 'Reference registration changed')
            for name, digest in cfg['inputs'].items():
                require(sha(relative_file(ROOT, name)) == digest, 'Input changed: '+name)
        verify()
        reference = read(relative_file(ROOT, cfg['reference_protocol']))
        require(reference['schema'] == 'saved_raw_ownership_history_diagnostic_v1',
                'Wrong reference registration schema')
        require(cfg['inputs'] == reference['inputs'] and cfg['episode'] == reference['episode']
                and cfg['application_url'] == reference['application_url'],
                'Original evidence pins or identity changed')
        result.update(audit(cfg))
        verify()
        result['status'] = 'passed_saved_raw_executed_work_only'
        result['limitations'] = [
            'Observed archived histories only; unobserved intermediate engine events remain unknown.',
            'Aggregate skipped counts do not identify individual absent dependency states.',
            'No raw result-value correctness re-audit, host telemetry, overlap certification or whole-controller cost.',
            'A pass is not complete dependency inventory, prospective integration or physical campaign acceptance.',
        ]
    except Exception as exc:
        result.update(status='failed_preserved', error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        try:
            result['ended_utc'] = now(); write_new(output/'result.json', result)
            print(json.dumps(result), flush=True)
        finally:
            if lock_stream is not None: lock_stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare', help='Bind existing evidence pins; no audit')
    p.add_argument('--reference-protocol', type=Path, required=True)
    p.add_argument('--latest-start', required=True)
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('run', help='Worker3 detached saved-raw audit')
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args.reference_protocol, args.latest_start, args.output)
    else: run(args.protocol, args.output)


if __name__ == '__main__': main()
