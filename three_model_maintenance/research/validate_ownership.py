"""Replay exact ownership on genuine retained evidence and inventory capture gaps.

This diagnostic never accepts the failed physical episode. Missing task/counter
evidence is reported explicitly; it is not filled, fetched live or inferred.
"""
import argparse
import hashlib
import re
import traceback
from collections import Counter
from pathlib import Path
from .common import decode, now, read, require, sha, utc, write_new
from .ownership import exact_bindings


def run(protocol, output):
    protocol, output = Path(protocol), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'started_utc': now(), 'protocol_sha256': sha(protocol),
              'physical_episode_accepted': False, 'model_fit_performed': False,
              'SQL_executed': False, 'live_REST_requested': False}
    try:
        cfg = read(protocol)
        require(cfg['schema'] == 'retained_SQL_ownership_regression_v1', 'Unknown protocol')
        require(utc(now()) < utc(cfg['latest_start_utc']), 'Registered diagnostic start cutoff expired')
        root = Path(__file__).resolve().parents[2]
        for name, digest in cfg['code_sha256'].items():
            require(sha(root / name) == digest, 'Code differs: ' + name)
        inputs = {name: Path(spec['path']) for name, spec in cfg['inputs'].items()}
        for name, path in inputs.items():
            require(sha(path) == cfg['inputs'][name]['sha256'], 'Input differs: ' + name)
        old = read(inputs['previous_ownership'])
        inventory = read(inputs['sql_inventory'])
        receipt = read(inputs['inventory_receipt'])
        parent = read(inputs['failed_parent'])
        require(receipt['raw_sha256'] == cfg['inputs']['sql_inventory']['sha256'], 'Inventory receipt differs')
        require(old['input_sha256'][str(inputs['events'])] == cfg['inputs']['events']['sha256'], 'Old raw binding differs')
        require((parent['passed_episodes'], parent['failed_episodes'], parent['unattempted_episodes']) == (0, 1, 1)
                and parent['model_fit_performed'] is False, 'Historical failed state differs')

        requests, calls = [], []
        for line in inputs['events'].open():
            event = decode(line)
            require(event['experiment_id'] == cfg['experiment_id'], 'Mixed raw identity')
            if event['kind'] == 'statement_requested':
                requests.append(event)
            elif event['kind'] == 'statement_completed' and event['role'] == 'trace_query':
                calls.append(event)
        proof = exact_bindings(requests, calls, inventory)
        normalized = {mid: {'sql_execution_id': r['sql_execution_id'],
                            'success_job_ids': sorted(r['success_job_ids'])}
                      for mid, r in old['query_execution_bindings'].items()}
        require(proof['bindings'] == normalized, 'New exact bindings differ from saved independent diagnostic')
        require(len(calls) == cfg['expected_completed_queries'], 'Actual completed population differs')
        links = old['direct_links']
        require(len(links) == cfg['expected_rejected_links'] and not old['unresolved_queries']
                and not old['unresolved_rejected_job_links'], 'Prior diagnostic coverage differs')
        for row in links:
            binding = proof['bindings'][row['measurement_id']]
            require(row['sql_execution_id'] == binding['sql_execution_id']
                    and row['job_id'] in binding['success_job_ids'], 'Rejected job lacks direct ownership')
        write_new(output / 'exact_bindings.json', proof)

        owned = {jid for b in proof['bindings'].values() for jid in b['success_job_ids']}
        jobs, stages, tasks = {}, {}, {}
        bad_job, bad_stage = Counter(), Counter()
        frames = Counter()
        terminal = None
        for line in inputs['events'].open():
            e = decode(line)
            if e['kind'] == 'terminal_engine_archive_checkpoint' and e['terminal']:
                require(terminal is None, 'Multiple terminal checkpoints')
                terminal = e
            if e['kind'] != 'spark_rest' or terminal is not None:
                continue
            resource = e['resource']
            if resource == 'jobs':
                for job in e['payload']:
                    if job['jobId'] not in owned:
                        continue
                    frames['owned_job_observations'] += 1
                    jobs[job['jobId']] = job
                    for field in ('numFailedTasks', 'numKilledTasks', 'numFailedStages'):
                        if field not in job or type(job[field]) is not int or job[field] != 0:
                            bad_job[(job['jobId'], field)] += 1
            elif resource == 'stages':
                for stage in e['payload']:
                    key = (stage['stageId'], stage['attemptId'])
                    stages[key] = stage
                    for field in ('numFailedTasks', 'numKilledTasks', 'attemptId'):
                        if field not in stage or type(stage[field]) is not int or stage[field] != 0:
                            bad_stage[(stage['stageId'], field)] += 1
            else:
                match = re.fullmatch(r'stages/(\d+)/(\d+)/taskList\?length=(\d+)', resource)
                if match:
                    sid, attempt, count = map(int, match.groups())
                    payload = e['payload']
                    valid = (type(payload) is list and len(payload) == count
                             and all(type(t.get('taskId')) is int and type(t.get('index')) is int
                                     and type(t.get('attempt')) is int and t['attempt'] == 0
                                     and t.get('status') == 'SUCCESS'
                                     and type(t.get('duration')) in (int, float) and t['duration'] > 0
                                     for t in payload))
                    if valid:
                        valid = (len({t['taskId'] for t in payload}) == count
                                 and {t['index'] for t in payload} == set(range(count)))
                    key = (sid, attempt, count)
                    item = {'valid_explicit_task_population': valid,
                            'payload_sha256': hashlib.sha256(__import__('json').dumps(payload, sort_keys=True).encode()).hexdigest()}
                    tasks.setdefault(key, []).append(item)

        stage_ids = {sid for j in jobs.values() for sid in j['stageIds']}
        missing_tasks, complete_stages, other_stages = [], [], []
        for key, stage in stages.items():
            if key[0] not in stage_ids:
                continue
            if stage['status'] != 'COMPLETE':
                other_stages.append({'stage_id': key[0], 'attempt_id': key[1], 'status': stage['status']})
                continue
            complete_stages.append(key)
            count = stage.get('numTasks')
            available = tasks.get((*key, count), []) if type(count) is int else []
            if not any(t['valid_explicit_task_population'] for t in available):
                missing_tasks.append({'stage_id': key[0], 'attempt_id': key[1],
                                      'num_tasks': count, 'saved_task_frames': len(available)})
        gaps = {'terminal_archive_present': terminal is not None,
                'owned_job_ids_missing_from_raw_prefix': sorted(owned - jobs.keys()),
                'owned_jobs_without_successful_latest_observation': sorted(j for j, v in jobs.items() if v['status'] != 'SUCCEEDED'),
                'referenced_stage_ids_missing_from_raw_prefix': sorted(stage_ids - {sid for sid, _ in stages}),
                'complete_stage_attempts_without_complete_saved_tasks': missing_tasks,
                'other_referenced_stage_states': other_stages,
                'invalid_or_missing_job_counter_observations': [dict(job_id=k[0], field=k[1], observations=n) for k,n in sorted(bad_job.items())],
                'invalid_or_missing_stage_counter_observations': [dict(stage_id=k[0], field=k[1], observations=n) for k,n in sorted(bad_stage.items()) if k[0] in stage_ids]}
        write_new(output / 'capture_gap_inventory.json', gaps)
        for name, path in inputs.items():
            require(sha(path) == cfg['inputs'][name]['sha256'], 'Input changed while reading: ' + name)
        for name, digest in cfg['code_sha256'].items():
            require(sha(root / name) == digest, 'Code changed while running: ' + name)
        require(sha(protocol) == report['protocol_sha256'], 'Protocol changed while running')
        report.update(status='passed_exact_ownership_regression_capture_gaps_diagnostic_only',
                      exact_completed_query_bindings=len(calls), directly_owned_rejected_links=len(links),
                      distinct_owned_jobs=len(owned), observed_owned_jobs=len(jobs),
                      referenced_stage_ids=len(stage_ids), complete_stage_attempts_observed=len(complete_stages),
                      complete_stage_attempts_missing_saved_tasks=len(missing_tasks),
                      job_counter_issue_id_fields=len(bad_job),
                      stage_counter_issue_id_fields=sum(k[0] in stage_ids for k in bad_stage),
                      raw_prefix_frame_counts=dict(frames), terminal_archive_present=terminal is not None,
                      original_counts={'passed': 0, 'failed': 1, 'unattempted': 1},
                      limitations=['Post-hoc SQL metadata does not provide prospective archive provenance.',
                                   'Gap inventory is not stage completion/counter certification or exhaustive unknown-job coverage.',
                                   'Skipped/reused stages need explicit execution semantics; no missing tasks are invented.',
                                   'Original failed episode stays failed; no new physical data or metric improvement.'])
    except Exception as exc:
        report.update(status='failed_preserved', error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        report['ended_utc'] = now()
        write_new(output / 'result.json', report)
        print(report, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.protocol, args.output)
