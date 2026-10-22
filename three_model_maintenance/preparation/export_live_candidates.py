"""Re-audit real live output and export candidates, never authorize fitting."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from three_model_maintenance.runtime.collect import audit
from three_model_maintenance.runtime.collector_bridge import audit_publications
from three_model_maintenance.models.latency import feature_vector
from three_model_maintenance.contracts import require


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(directory, output):
    receipt_path = directory / 'result.json'; receipt = json.loads(receipt_path.read_text())
    events_path = directory / 'events.jsonl'; before = sha(events_path)
    require(before == receipt['events_sha256'], 'Physical events differ from terminal receipt')
    raw = audit(directory); publication = audit_publications(directory)
    require(raw['events_sha256'] == before and publication == receipt['three_model_publication_audit'], 'Independent raw/publication reconstruction differs')
    events = [json.loads(line) for line in events_path.open()]
    clock = next(e for e in events if e['kind'] == 'replay_clock')['start_monotonic_ns']
    completed = {e['measurement_id']: e for e in events if e['kind'] == 'statement_completed' and e['role'] == 'trace_query'}
    offered = []; rows = []; evidence = []; counts = {'A': 0, 'B': 0}; names = None
    for event in events:
        if event['kind'] == 'queue_transition' and event['state'] == 'offered':
            offered.append(event['actual_transition']['monotonic_ns'])
        if event['kind'] != 'three_model_feature_publication':continue
        p = event['publication']; mid = p['measurement_id']
        if mid not in completed:continue  # Unsubmitted publications stay in raw inventory, never labelled.
        result = completed[mid]; values = p['feature_values']
        if names is None:names = list(values)
        require(set(values) == set(names), 'Mixed live feature contract')
        feature_vector(values, names)
        captured = p['capture_at']['monotonic_ns']; row = dict(experiment_id=p['experiment_id'], measurement_id=mid, **values)
        row.update(table=p['source_context']['table'], snapshot_id=p['source_context']['snapshot_id'],
                   feature_monotonic_ns=captured, query_start_utc=result['client_execute_start']['utc'],
                   service_target_ms=result['client_elapsed_ns'] / 1e6, client_elapsed_ns=result['client_elapsed_ns'])
        for seconds in (60, 300):
            complete = captured - clock >= seconds * 1000000000
            row[f'offered_history_complete_{seconds}s'] = complete
            row[f'offered_count_{seconds}s'] = sum(captured - seconds * 1000000000 < t <= captured for t in offered) if complete else None
        if row['offered_history_complete_300s'] and row['offered_history_complete_60s']:
            counts['A' if p['client_pending'] else 'B'] += 1
        rows.append(row)
        evidence.append({'experiment_id':p['experiment_id'], 'measurement_id':mid, 'receipt':p})
    require(len(rows) == len(completed) == publication['completed_queries'] and rows, 'Missing/duplicate export identity')
    require(len({r['measurement_id'] for r in rows}) == len(rows), 'Reused query identity')
    require(sha(events_path) == before, 'Raw changed during export')
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'queries.csv').open('x', newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with (output / 'publication_evidence.jsonl').open('x') as stream:
        for record in evidence:stream.write(json.dumps(record, allow_nan=False) + '\n')
    report={'status':'verified_live_candidate_export_not_fit_authorized','query_rows':len(rows),
            'complete_history_condition_counts':counts,'query_predictor_allowlist':names,
            'source_role':'known_day6_engineering_development_only','fit_authorized':False,'runtime_adapter_accepted':False,
            'physical_result_sha256':sha(receipt_path),'events_sha256':before,
            'journal_sha256':sha(directory / 'feature_publication.jsonl'),
            'artifact_sha256':{name:sha(output/name) for name in ('queries.csv','publication_evidence.jsonl')},
            'export_code_sha256':sha(Path(__file__)),
            'limitations':['Raw receipt copies retain runtime_adapter_accepted false; independent fit authorization still required.',
                           'One known source family; no independent validation/calibration/test or fitted model.',
                           'Early missing offered histories remain missing; no inferred original SQL mix.']}
    (output / 'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();export(args.directory.resolve(),args.output.resolve())
