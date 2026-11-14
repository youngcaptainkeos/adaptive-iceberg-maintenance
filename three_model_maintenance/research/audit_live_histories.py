"""Read-only raw ownership/history diagnostic, never campaign acceptance.

Reconstructs ownership without trusting collector selection. Reviews every saved
owned job/stage observation; absent observations stay unknown. Completeness is
limited to archived responses, not all engine events or unknown SQL jobs.
"""
import argparse
import json
import traceback
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .common import read, sha, require, integer, now, utc, write_new
from .ownership import exact_bindings


def run(protocol, output):
    output.mkdir(parents=True, exist_ok=False)
    cfg = read(protocol)
    report = dict(status='running', started_utc=now(), SQL_executed=False,
                  REST_requested=False, original_failure_accepted=False,
                  training_eligible=False, protocol_sha256=sha(protocol))
    try:
        root = Path(__file__).resolve().parents[2]
        require(utc(now()) < utc(cfg['latest_start_utc']), 'Admission expired')
        def frozen():
            for p, h in cfg['code'].items():
                require(sha(root / p) == h, 'Code changed: ' + p)
            for p, h in cfg['inputs'].items():
                require(sha(root / p) == h, 'Input changed: ' + p)
        frozen()
        episode = root / cfg['episode']
        archive = episode / 'direct_archive'
        checkpoints = sorted(archive.glob('checkpoint_*'))
        require(checkpoints, 'No archived checkpoints')
        events = [json.loads(x) for x in (episode / 'events.jsonl').read_text().splitlines()]
        requests = [e for e in events if e['kind'] == 'statement_requested']
        calls = [e for e in events if e['kind'] == 'statement_completed']
        require(len(requests) == len(calls) == 6, 'Six complete calls required')
        observations = []; final_sql = []
        for cp in checkpoints:
            pages = []
            for file in sorted(cp.glob('receipt_*.json')):
                r = read(file); raw = (archive / r['raw_path']).resolve()
                require(raw.is_relative_to(archive.resolve()), 'Raw path escape')
                require(sha(raw) == r['raw_sha256'] and r['http_status'] == 200, 'Invalid raw response')
                require(r['url'].startswith(cfg['application_url'] + '/'), 'Application differs')
                require(r['response_end_monotonic_ns'] >= r['request_start_monotonic_ns'], 'Reversed response interval')
                data = read(raw)
                observations.append((cp.name, r['resource'], data))
                if r['resource'].startswith('sql?'):
                    query = parse_qs(urlparse(r['url']).query)
                    pages.append((int(query['offset'][0]), int(query['length'][0]), data))
            if cp == checkpoints[-1]:
                pages.sort(key=lambda p: p[0]); expected = 0
                require(pages, 'Final SQL inventory absent')
                for i, (offset, length, rows) in enumerate(pages):
                    require(offset == expected and length > 0 and type(rows) is list, 'SQL pagination gap')
                    require(len(rows) == length if i < len(pages)-1 else len(rows) < length, 'SQL pagination not terminal')
                    expected += length; final_sql.extend(rows)
        bindings = exact_bindings(requests, calls, final_sql)['bindings']
        ids = [j for b in bindings.values() for j in b['success_job_ids']]
        require(ids and len(ids) == len(set(ids)), 'Empty or shared job ownership')
        owned = set(ids); stage_ids = set(); job_frames = []; stage_frames = []
        for cp, resource, rows in observations:
            if resource == 'jobs':
                for j in rows:
                    if j['jobId'] not in owned: continue
                    for field in ('numFailedTasks', 'numKilledTasks', 'numFailedStages'):
                        require(integer(j[field], field) == 0, 'Adverse owned job observation')
                    require(j['status'] in ('RUNNING', 'SUCCEEDED'), 'Unexpected owned job state')
                    require(type(j['stageIds']) is list and len(j['stageIds']) == len(set(j['stageIds'])), 'Invalid stage references')
                    for sid in j['stageIds']: stage_ids.add(integer(sid, 'stage ID'))
                    job_frames.append((cp, j))
        require({j['jobId'] for _, j in job_frames} == owned, 'Owned jobs missing from raw')
        for cp, resource, rows in observations:
            if resource == 'stages':
                for s in rows:
                    if s['stageId'] not in stage_ids: continue
                    require(integer(s['attemptId'], 'attempt ID') == 0, 'Observed stage retry')
                    for field in ('numFailedTasks', 'numKilledTasks'):
                        require(integer(s[field], field) == 0, 'Adverse referenced stage observation')
                    require(s['status'] in ('ACTIVE','PENDING','COMPLETE','SKIPPED'), 'Unexpected referenced stage state')
                    stage_frames.append((cp,s))
        latest = {j['jobId']: j for _,j in job_frames}
        require(all(j['status']=='SUCCEEDED' for j in latest.values()), 'Owned job not terminal')
        # Compare independently reconstructed ownership with the prior diagnostic.
        prior = read(root / cfg['reconciliation'])
        require(set(p['job_id'] for p in prior['job_proofs']) == owned, 'Prior reconciliation ownership differs')
        present = {s['stageId'] for _,s in stage_frames}
        report.update(status='passed_saved_raw_ownership_history_diagnostic_only',
            calls=len(calls), directly_owned_jobs=len(owned), job_observations=len(job_frames),
            referenced_stage_ids=len(stage_ids), stage_observations=len(stage_frames),
            absent_reference_ids=sorted(stage_ids-present), bindings=bindings,
            limitations=['Only observed archived histories; no guarantee about unobserved intermediate engine events.',
                         'Missing dependency-stage states remain unknown; no original gate acceptance.',
                         'Prior task/count diagnostic is cross-checked for ownership, not independently reimplemented here.',
                         'No fresh runtime validation, compaction, policy benefit or training eligibility.'])
        frozen()
    except Exception as exc:
        report.update(status='failed_preserved', error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        report['ended_utc'] = now(); write_new(output/'result.json', report)
        print(json.dumps(report), flush=True)

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.protocol,a.output)
