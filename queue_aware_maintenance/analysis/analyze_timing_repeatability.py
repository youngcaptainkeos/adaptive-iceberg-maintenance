#!/usr/bin/env python3
"""Descriptive clock accounting and source-load inventory; no fits or new SQL."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.core.common import checked, require, sha, utc, now, write_json


def summary(values):
    values = sorted(values)
    require(values, 'Missing measured values')
    return {'count': len(values), 'median': statistics.median(values),
            'p99_observed_order_statistic': values[min(len(values)-1, int(.99*len(values)))],
            'maximum': values[-1], 'mean': statistics.mean(values)}


def run(protocol, output):
    cfg = json.loads(Path(protocol).read_text())
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'started_utc': now(), 'protocol_sha256': sha(protocol),
              'code_sha256': sha(__file__), 'new_SQL_operations': 0, 'fitting': False,
              'causal_effect_identified': False, 'new_workloads_selected_for_launch': False}
    try:
        require(cfg['schema_version'] == 'posthoc_queue_clock_inventory_v1', 'Unknown diagnostic protocol')
        require(sha(__file__) == cfg['analysis_code_sha256'], 'Changed diagnostic source')
        comparison_path = checked(cfg['completed_comparison'])
        comparison = json.loads(comparison_path.read_text())
        require(comparison['status'] == 'passed_complete_repeated_development_raw_comparison', 'Incomplete original comparison')
        root = Path(cfg['study_directory'])
        progress = json.loads((root/'progress.json').read_text())
        require(progress['passed'] == 8 and progress['failed'] == progress['unattempted'] == 0, 'Incomplete physical study')
        rows = []
        for attempt in progress['attempts']:
            episode = root/'episodes'/attempt['experiment_id']
            result = json.loads((episode/'result.json').read_text())
            require(sha(episode/'result.json') == attempt['result_sha256'], 'Changed physical result')
            clock, calls, digest = None, [], hashlib.sha256()
            # Hash every byte, parse only clocks and completed foreground calls.
            with (episode/'events.jsonl').open('rb') as stream:
                for line in stream:
                    digest.update(line)
                    if b'"kind": "cohort_clock"' in line:
                        event = json.loads(line)
                        clock = event['start_monotonic_ns']
                    elif b'"kind": "statement_completed"' in line and b'"role": "trace_query"' in line:
                        calls.append(json.loads(line))
            require(digest.hexdigest() == result['events_sha256'], 'Changed raw events')
            require(clock is not None and len(calls) == result['completed'] == cfg['expected_arrivals_per_episode'], 'Missing actual calls/clock')
            ecfg = json.loads((episode/'config.json').read_text())
            with (episode/'mapped_arrivals.csv').open() as stream:
                arrivals = list(csv.DictReader(stream))
            require(sha(episode/'mapped_arrivals.csv') == ecfg['mapping']['sha256'], 'Changed source mapping')
            require([r['measurement_id'] for r in calls] == [r['measurement_id'] for r in result['queries']], 'Call order differs from audited FIFO')
            service, gaps, before_due, after_due, offered_backlog_gaps = [], [], [], [], []
            previous = clock
            by_template = {}
            for call, query, arrival in zip(calls, result['queries'], arrivals):
                start, end = call['client_execute_start']['monotonic_ns'], call['fetch_end']['monotonic_ns']
                scheduled = clock+int(arrival['offset_ns'])
                require(query['source_query_id'] == arrival['source_query_id'], 'Changed FIFO/source binding')
                require(end-start == query['service_ns'] and end-scheduled == query['response_ns'], 'Actual service/response mismatch')
                require(start >= previous and start >= scheduled, 'Overlapping/before-arrival serial SQL')
                gap = start-previous
                idle_before_next_scheduled_arrival = max(0, min(start, scheduled)-previous)
                gaps.append(gap)
                before_due.append(idle_before_next_scheduled_arrival)
                after_due.append(gap-idle_before_next_scheduled_arrival)
                actual_offer = scheduled+query['generator_lateness_ns']
                if actual_offer <= previous:
                    offered_backlog_gaps.append(gap)
                service.append(end-start)
                by_template.setdefault(str(query['query_id']), []).append((end-start)/1e6)
                previous = end
            span = previous-clock
            require(sum(service) == result['sum_service_ns'], 'Measured call total differs')
            require(sum(service)+sum(gaps) == span and sum(before_due)+sum(after_due) == sum(gaps), 'Walltime partition mismatch')
            require(result['sum_response_ns'] == result['sum_wait_before_call_ns']+sum(service), 'Response partition mismatch')
            rows.append({'experiment_id': attempt['experiment_id'], 'repeat': attempt['repeat'], 'action': attempt['action'],
                         'result_sha256': attempt['result_sha256'], 'events_sha256': result['events_sha256'],
                         'mean_response_seconds': result['mean_response_seconds'],
                         'waiting_fraction_of_summed_response': result['sum_wait_before_call_ns']/result['sum_response_ns'],
                         'wall_seconds_until_last_result': span/1e9, 'foreground_call_seconds': sum(service)/1e9,
                         'outside_foreground_call_seconds': sum(gaps)/1e9,
                         'outside_foreground_call_fraction_of_wall': sum(gaps)/span,
                         'gap_before_next_scheduled_arrival_seconds': sum(before_due)/1e9,
                         'gap_after_next_scheduled_arrival_due_seconds': sum(after_due)/1e9,
                         'gap_with_next_request_already_recorded_offered_seconds': sum(offered_backlog_gaps)/1e9,
                         'query_call_ms': summary([v/1e6 for v in service]),
                         'outside_call_gap_ms': summary([v/1e6 for v in gaps]),
                         'call_ms_by_template': {k: summary(v) for k,v in by_template.items()},
                         'unfinished_at_arrival_horizon': len(calls)-result['completed_before_arrival_end'],
                         'final_file_count': result['final_file_state']['file_count']})
        repeat_changes = []
        for action in ['start_0', 'start_60', 'start_600', 'no_action']:
            first, second = [next(r for r in rows if r['repeat'] == i and r['action'] == action) for i in [0,1]]
            repeat_changes.append({'action': action,
                'second_minus_first_mean_response_seconds': second['mean_response_seconds']-first['mean_response_seconds'],
                'second_minus_first_foreground_call_seconds': second['foreground_call_seconds']-first['foreground_call_seconds'],
                'second_minus_first_outside_call_seconds': second['outside_foreground_call_seconds']-first['outside_foreground_call_seconds']})
        # Inventory source-clock windows, never select an outcome-favorable window or imply idle CPU.
        trace = checked(cfg['arrivals'])
        origin = utc(cfg['source_inventory_origin_utc'])
        width = cfg['source_inventory_window_seconds']
        require(isinstance(width, int) and width > 0 and width % 60 == 0, 'Registered whole-minute source-window width required')
        windows = {}
        with trace.open() as stream:
            for r in csv.DictReader(stream):
                elapsed = (utc(r['arrival_utc'])-origin).total_seconds()
                require(elapsed >= 0, 'Source predates origin')
                index = int(elapsed)//width
                window = windows.setdefault(index, {'window_index': index, 'arrivals': 0, 'minute_counts': [0]*(width//60)})
                window['arrivals'] += 1
                window['minute_counts'][min(len(window['minute_counts'])-1, int(elapsed%width)//60)] += 1
        write_json(out/'source_window_inventory.json', {'scope': 'Nonempty source-clock windows only; unlisted windows not imputed. Complete-window eligibility and source overlap with consumed data not established here.', 'arrivals_sha256': sha(trace), 'origin': origin.isoformat(), 'window_seconds': width, 'windows': list(windows.values())})
        report.update(status='passed_descriptive_clock_accounting_and_source_inventory', episodes=rows,
                      within_action_repeat_changes=repeat_changes,
                      original_descriptive_contrasts=comparison['contrasts'],
                      source_window_inventory_sha256=sha(out/'source_window_inventory.json'),
                      limitations=[
                          'Post-hoc accounting, not causal attribution or statistical significance; no thresholds or policies tuned.',
                          'Outside-call walltime includes telemetry freshness waits, client preparation, archival/metadata work, OS scheduling, and true arrival gaps; it is not all removable overhead.',
                          'Foreground SQL calls include client/network/fetch time, not pure engine CPU; maintenance can overlap these calls and gaps.',
                          'Summed request waiting and walltime are different units of aggregation; they cannot be subtracted as if equivalent.',
                          'Actual offered timestamp precedes durable queue insertion; backlog-gap label does not measure the exact availability of the Python pending queue.',
                          'Source inventory is not an independent-data reservation, capacity calibration, complete-window proof or automatic launch selection.',
                          'Only two repeats of one development window; cache/time/resource drift remain unisolated.'])
        lines = ['# Queue timing repeatability and clock accounting', '', 'Descriptive real-evidence analysis; no new SQL, fit, threshold or policy.', '', '| Run | Action | Mean response(s) | Call wall(s) | Outside-call wall(s) | Outside-call wall % |', '|---|---|---:|---:|---:|---:|']
        for r in rows:
            lines.append(f"| {r['experiment_id']} | {r['action']} | {r['mean_response_seconds']:.3f} | {r['foreground_call_seconds']:.3f} | {r['outside_foreground_call_seconds']:.3f} | {100*r['outside_foreground_call_fraction_of_wall']:.2f} |")
        lines += ['', '## Interpretation boundaries']+['- '+v for v in report['limitations']]
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
