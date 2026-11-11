"""Describe the original foreign-work gate using genuine saved REST histories.

Descriptive only: missing terminal states remain unknown, never inferred clean.
"""
import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'scripts/phase6-live-evaluation'))
from engine_archive import merged_engine_frames
from engine_overlap import engine_time
from three_model_maintenance.audits.telemetry_gap_diagnostic import sha


def run(episode, output):
    output.mkdir(parents=True, exist_ok=False)
    path=episode/'events.jsonl';before=sha(path)
    rows=[json.loads(line) for line in path.open()]
    cfg=json.loads((episode/'config.json').read_text())
    requests={r['measurement_id']:r for r in rows if r['kind']=='statement_requested'}
    calls=[r for r in rows if r['kind']=='statement_completed' and r['role']=='trace_query']
    jobs,_=merged_engine_frames(rows);markers=[r['marker'] for r in requests.values()]
    table=cfg['destination_table'];histories=defaultdict(list)
    for event in rows:
        if event['kind']=='spark_rest' and event['resource']=='jobs':
            for job in event['payload']:
                histories[job['jobId']].append(dict(request_start=event['request_start'],
                    response_end=event['response_end'],recorded=event['recorded'],job=job))
    failures=[];rejected_ids=set()
    for call in calls:
        a=datetime.fromisoformat(call['client_execute_start']['utc']).timestamp()
        b=datetime.fromisoformat(call['fetch_end']['utc']).timestamp()
        active=[j for j in jobs if engine_time(j['submissionTime'])<b and
                (not j.get('completionTime') or engine_time(j['completionTime'])>a)]
        rejected=[j for j in active if not (any(m in str(j.get('description','')) for m in markers)
            or (str(j.get('description','')).startswith('Rewriting ') and str(j.get('description','')).endswith(' in '+table)))]
        if not active or rejected:
            rejected_ids.update(j['jobId'] for j in rejected)
            failures.append(dict(measurement_id=call['measurement_id'],query_id=call['query_id'],
                client_execute_start=call['client_execute_start'],fetch_end=call['fetch_end'],
                cause='empty_active_inventory' if not active else 'unattributed_overlapping_job',
                active_job_count=len(active),rejected_job_ids=[j['jobId'] for j in rejected]))
    if before!=sha(path):raise ValueError('Raw evidence changed')
    result=dict(status='completed_foreign_work_diagnostic_only',source_episode=str(episode),
        events_sha256=before,completed_queries=len(calls),known_jobs=len(jobs),
        failing_queries=len(failures),first_failure=failures[0] if failures else None,
        failures=failures,rejected_job_histories={str(j):histories[j] for j in sorted(rejected_ids)},original_episode_accepted=False,
        limitations=['Missing completionTime does not prove a job stayed active.',
                    'Descriptions alone cannot prove ownership of unattributed work.',
                    'No gate change, physical retry, fit or acceptance performed.'])
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('failures','first_failure','rejected_job_histories')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--episode',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.episode.resolve(),a.output.resolve())
