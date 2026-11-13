"""Replay direct task selection against genuine pre-terminal archive frames.

No REST, SQL or new physical episode; a passing code regression does not accept
missing historical task records or prove the new network adapter in production.
"""
import argparse
import ast
import re
import traceback
from pathlib import Path
from .common import decode, now, read, require, sha, utc, write_new
from .ownership import exact_bindings
from .capture_retained_tasks import validate_tasks
from three_model_maintenance.runtime.direct_task_retention import retention_plan


def run(protocol, output):
    output.mkdir(parents=True, exist_ok=False)
    cfg = read(protocol)
    result = dict(status='running', started_utc=now(), protocol_sha256=sha(protocol),
                  SQL_executed=False, live_REST_requested=False, physical_episode_accepted=False)
    try:
        require(cfg['schema'] == 'direct_retention_saved_replay_v1', 'Unknown schema')
        require(utc(now()) < utc(cfg['latest_start_utc']), 'Admission cutoff expired')
        root = Path(__file__).resolve().parents[2]
        def verify():
            for name,digest in cfg['code_sha256'].items():
                require(sha(root/name) == digest, 'Code changed: '+name)
                ast.parse((root/name).read_text(), filename=name)
            for name,spec in cfg['inputs'].items():
                require(sha(spec['path']) == spec['sha256'], 'Input changed: '+name)
            require(sha(protocol) == result['protocol_sha256'], 'Protocol changed')
        verify()
        requests, calls, jobs, stages, tasks = [], [], [], [], {}
        terminal = False
        for line in Path(cfg['inputs']['events']['path']).open():
            e = decode(line)
            require(e['experiment_id'] == cfg['experiment_id'], 'Mixed episode identity')
            if e['kind'] == 'terminal_engine_archive_checkpoint' and e['terminal']:
                terminal = True
                break
            if e['kind'] == 'statement_requested': requests.append(e)
            elif e['kind'] == 'statement_completed' and e['role'] == 'trace_query': calls.append(e)
            elif e['kind'] == 'spark_rest':
                resource = e['resource']
                if resource == 'jobs': jobs.append(e['payload'])
                elif resource == 'stages': stages.append(e['payload'])
                else:
                    match = re.fullmatch(r'stages/(\d+)/(\d+)/taskList\?length=(\d+)', resource)
                    if match:
                        key = tuple(map(int,match.groups()))
                        validate_tasks(e['payload'], key[2])
                        if key in tasks: require(tasks[key] == e['payload'], 'Retained task frame changed')
                        tasks[key] = e['payload']
        require(terminal, 'Missing original terminal checkpoint')
        proof = exact_bindings(requests,calls,read(cfg['inputs']['sql_inventory']['path']))
        require(proof == read(cfg['inputs']['bindings']['path']), 'Exact bindings differ')
        plan = retention_plan(proof['bindings'], jobs, stages)
        old = read(cfg['inputs']['gap_inventory']['path'])
        require(plan['missing_referenced_stage_ids'] == old['referenced_stage_ids_missing_from_raw_prefix'], 'Missing stages differ')
        require(plan['missing_owned_job_ids'] == old['owned_job_ids_missing_from_raw_prefix'], 'Missing jobs differ')
        selected = {(r['stage_id'],r['attempt_id'],r['num_tasks']) for r in plan['complete_stage_task_requests']}
        missing = selected-tasks.keys()
        expected = {(r['stage_id'],r['attempt_id'],r['num_tasks']) for r in old['complete_stage_attempts_without_complete_saved_tasks']}
        require(missing == expected, 'Missing task population differs from independent inventory')
        require(len(selected) == cfg['expected_complete_stages'] and len(missing) == cfg['expected_missing_tasks'], 'Registered population differs')
        write_new(output/'direct_selection.json',plan)
        result.update(status='passed_real_saved_selection_regression_only',
                      completed_queries=len(calls), directly_owned_jobs=len(plan['directly_owned_job_ids']),
                      selected_complete_stage_attempts=len(selected),
                      selected_with_verified_saved_tasks=len(selected & tasks.keys()),
                      selected_missing_saved_tasks=len(missing),
                      referenced_stage_ids_missing=len(plan['missing_referenced_stage_ids']),
                      observed_skipped_stage_ids=len(plan['observed_skipped_stage_ids']),
                      nonterminal_stage_attempts=len(plan['nonterminal_stage_attempts']),
                      verified_saved_tasks=sum(len(tasks[k]) for k in selected & tasks.keys()),
                      original_campaign_counts=dict(passed=0,failed=1,unattempted=1),
                      limitations=['Network adapter and prospective integration remain unvalidated.',
                                   'No per-job completed/skipped reconciliation or resource attribution proof.',
                                   'Historical task/stage gaps remain gaps; old physical failure unchanged.'])
        verify()
    except Exception as exc:
        result.update(status='failed_preserved',error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        result['ended_utc'] = now()
        write_new(output/'result.json',result)
        print(result,flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.protocol,a.output)
