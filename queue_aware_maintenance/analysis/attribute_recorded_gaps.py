#!/usr/bin/env python3
"""Locate recorded spans inside real SQL gaps, without causal attribution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.core.common import checked, require, sha, now, write_json


def union(intervals):
    merged = []
    for start, end in sorted(intervals):
        require(end >= start, 'Reversed recorded interval')
        if start == end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def intersect_length(left, right):
    i = j = total = 0
    while i < len(left) and j < len(right):
        a, b = left[i]
        c, d = right[j]
        total += max(0, min(b, d)-max(a, c))
        if b <= d:
            i += 1
        else:
            j += 1
    return total


def run(protocol, output):
    cfg = json.loads(Path(protocol).read_text())
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'started_utc': now(), 'code_sha256': sha(__file__),
              'protocol_sha256': sha(protocol), 'new_SQL_operations': 0,
              'causal_overhead_or_removability_established': False}
    try:
        require(cfg['schema_version'] == 'recorded_queue_gap_spans_v1', 'Unknown gap protocol')
        require(sha(__file__) == cfg['code_sha256'], 'Changed registered analysis source')
        clock_receipt = json.loads(checked(cfg['clock_receipt']).read_text())
        require(clock_receipt['status'] == 'passed_descriptive_clock_accounting_and_source_inventory', 'Missing clock reconstruction')
        require(len(clock_receipt['episodes']) == 8, 'Incomplete original scope')
        rows = []
        for old in clock_receipt['episodes']:
            root = Path(cfg['study_directory'])/'episodes'/old['experiment_id']
            require(sha(root/'result.json') == old['result_sha256'], 'Changed audited result')
            categories = {k: [] for k in ['spark_REST_request_to_response', 'recorded_telemetry_wait',
                'nonforeground_nonmaintenance_SQL_call', 'maintenance_SQL_call',
                'query_observation_capture_to_request_capture', 'request_capture_to_actual_execute']}
            observations, calls, clock, digest = {}, [], None, hashlib.sha256()
            with (root/'events.jsonl').open('rb') as stream:
                for line in stream:
                    digest.update(line)
                    relevant = any(('"kind": "'+kind+'"').encode() in line for kind in
                        ['cohort_clock', 'statement_completed', 'query_observation', 'spark_rest', 'query_telemetry_availability_wait'])
                    if not relevant:
                        continue
                    r = json.loads(line)
                    kind = r['kind']
                    if kind == 'cohort_clock': clock = r['start_monotonic_ns']
                    elif kind == 'query_observation':
                        require(r['measurement_id'] not in observations, 'Duplicate query feature observation')
                        observations[r['measurement_id']] = r['recorded']['monotonic_ns']
                    elif kind == 'spark_rest':
                        categories['spark_REST_request_to_response'].append((r['request_start']['monotonic_ns'], r['response_end']['monotonic_ns']))
                    elif kind == 'query_telemetry_availability_wait':
                        categories['recorded_telemetry_wait'].append((r['started']['monotonic_ns'], r['ended']['monotonic_ns']))
                    elif kind == 'statement_completed':
                        interval = (r['client_execute_start']['monotonic_ns'], r['fetch_end']['monotonic_ns'])
                        if r['role'] == 'trace_query': calls.append(r)
                        elif r['role'] == 'maintenance': categories['maintenance_SQL_call'].append(interval)
                        else: categories['nonforeground_nonmaintenance_SQL_call'].append(interval)
            require(digest.hexdigest() == old['events_sha256'] and clock is not None, 'Changed raw ledger or missing clock')
            require(len(calls) == cfg['expected_arrivals_per_episode'], 'Wrong foreground scope')
            previous, gaps, gap_records = clock, [], []
            for call in calls:
                start, end = call['client_execute_start']['monotonic_ns'], call['fetch_end']['monotonic_ns']
                observation = observations[call['measurement_id']]
                request = call['request_start']['monotonic_ns']
                require(previous <= start < end and observation <= request <= start, 'Invalid call/observation chronology')
                gaps.append((previous, start))
                gap_records.append({'measurement_id': call['measurement_id'], 'query_id': call['query_id'],
                                    'start': previous, 'end': start, 'duration_seconds': (start-previous)/1e9})
                categories['query_observation_capture_to_request_capture'].append((observation, request))
                categories['request_capture_to_actual_execute'].append((request, start))
                previous = end
            gaps = union(gaps)
            total = sum(b-a for a,b in gaps)
            require(total == round(old['outside_foreground_call_seconds']*1e9), 'Gap accounting differs from prior integer reconstruction')
            merged = {k: union(v) for k,v in categories.items()}
            tagged = union([span for spans in merged.values() for span in spans])
            covered = intersect_length(gaps, tagged)
            require(0 <= covered <= total, 'Invalid union coverage')
            by_category = {k: intersect_length(gaps, spans)/1e9 for k,spans in merged.items()}
            largest = []
            for gap in sorted(gap_records, key=lambda r:r['duration_seconds'], reverse=True)[:cfg['largest_gap_count']]:
                largest.append(dict(gap, temporal_overlap_seconds={k: intersect_length([(gap['start'],gap['end'])],spans)/1e9 for k,spans in merged.items()}))
            rows.append({'experiment_id': old['experiment_id'], 'action': old['action'], 'repeat': old['repeat'],
                         'outside_call_seconds': total/1e9, 'seconds_with_any_recorded_tag': covered/1e9,
                         'seconds_without_recorded_tags': (total-covered)/1e9,
                         'nonexclusive_category_overlap_seconds': by_category, 'largest_gaps': largest})
        report.update(status='passed_recorded_gap_span_accounting', episodes=rows,
            limitations=['Tags are temporal overlaps, not exclusive or causal components; category totals must not be summed.',
                         'Event capture timestamps precede durable writes. Capture-to-request/execute spans include bookkeeping, locking and persistence; exact fsync duration is not measured.',
                         'REST response end precedes durable payload logging; archival CPU/serialization/post-response persistence remain partly untagged.',
                         'Telemetry waits from different threads may overlap gaps; a matching interval alone does not prove foreground blocking.',
                         'No old result is corrected by subtracting a tag; no gate, policy, threshold or physical runtime is changed.'])
        lines = ['# Recorded spans inside foreground SQL gaps', '', 'Descriptive overlap, not causal overhead or removable time.', '',
                 '| Run | Outside SQL(s) | REST(s) | Telemetry wait(s) | Observation→request(s) | Request→execute(s) | Untagged(s) |',
                 '|---|---:|---:|---:|---:|---:|---:|']
        for row in rows:
            c = row['nonexclusive_category_overlap_seconds']
            lines.append(f"| {row['experiment_id']} | {row['outside_call_seconds']:.2f} | {c['spark_REST_request_to_response']:.2f} | {c['recorded_telemetry_wait']:.2f} | {c['query_observation_capture_to_request_capture']:.2f} | {c['request_capture_to_actual_execute']:.2f} | {row['seconds_without_recorded_tags']:.2f} |")
        lines += ['', '## Limits']+['- '+v for v in report['limitations']]
        (out/'report.md').write_text('\n'.join(lines)+'\n')
    except Exception as exc:
        report.update(status='failed_preserved', error=str(exc))
        raise
    finally:
        report['ended_utc'] = now()
        write_json(out/'result.json', report)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.protocol, args.output)
