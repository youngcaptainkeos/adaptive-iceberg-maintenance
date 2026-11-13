"""Supplementary streaming response accounting on an existing full-drain ledger.

This deliberately does not replace correctness, publication, task, or attribution
audits. It has no API for changing an old failed campaign to passed.
"""
import csv
import math
from pathlib import Path
from .common import decode, integer, read, require, sha


def nearest_rank(values, probability):
    require(values and 0 < probability <= 1, 'Invalid quantile')
    return sorted(values)[max(0, math.ceil(probability * len(values)) - 1)]


def _area(intervals, boundary=None):
    edges = []
    for start, end in intervals:
        require(end >= start, 'Reversed response interval')
        if boundary is not None:
            if start >= boundary:
                continue
            end = min(end, boundary)
        edges.extend(((start, 1), (end, -1)))
    require(edges, 'No observed response intervals')
    total = level = 0
    previous = min(t for t, _ in edges)
    # At equal timestamps additions first; zero-duration intervals remain valid.
    for t, delta in sorted(edges, key=lambda x: (x[0], -x[1])):
        total += level * (t - previous)
        level += delta
        require(level >= 0, 'Negative outstanding count')
        previous = t
    require(level == 0, 'Unclosed area integration')
    return total


def reconstruct(directory, expected):
    directory = Path(directory)
    required = {'events.jsonl', 'mapped_arrivals.csv', 'config.json', 'result.json'}
    require(set(expected) == required, 'Pin all four input hashes before accounting')
    require(all(sha(directory / name) == value for name, value in expected.items()), 'Changed registered accounting input')
    cfg, saved = read(directory / 'config.json'), read(directory / 'result.json')
    require(saved['status'] == 'audited_complete_real_full_drain_episode_only', 'Not an existing audited full-drain episode')
    require(cfg['experiment_id'] == saved['experiment_id'], 'Config/result identity differs')
    require(cfg['mapping']['sha256'] == expected['mapped_arrivals.csv'], 'Config/source mapping binding differs')
    require(saved['events_sha256'] == expected['events.jsonl'], 'Saved result/raw binding differs')
    with (directory / 'mapped_arrivals.csv').open() as stream:
        mapped = list(csv.DictReader(stream))
    source = {r['source_query_id']: r for r in mapped}
    require(len(source) == len(mapped) > 0, 'Empty/duplicate source population')
    clocks, initial, final, calls, requests, states, times, mids, dispatched = [], [], [], {}, {}, {}, {}, {}, []
    active = None
    action_count = 0
    adverse = {'statement_failed', 'cohort_failed_preserved', 'cohort_thread_failed', 'spark_rest_failed'}
    with (directory / 'events.jsonl').open() as stream:
        for line in stream:
            r = decode(line)
            require(r['experiment_id'] == cfg['experiment_id'], 'Mixed raw experiment identities')
            kind = r['kind']
            require(kind not in adverse, 'Adverse raw event; no complete-cohort report')
            if kind == 'cohort_clock':
                clocks.append(r)
            elif kind == 'cohort_initial_state':
                initial.append(r)
            elif kind == 'cohort_final_state':
                final.append(r)
            elif kind == 'statement_requested' and r['role'] == 'trace_query':
                mid = r['measurement_id']
                require(mid not in requests, 'Duplicate query request')
                requests[mid] = r
            elif kind == 'statement_completed':
                if r['role'] == 'maintenance':
                    action_count += 1
                if r['role'] == 'trace_query':
                    mid = r['measurement_id']
                    require(mid not in calls, 'Duplicate query completion')
                    calls[mid] = r
            elif kind == 'cohort_queue_transition':
                sid, state = r['source']['source_query_id'], r['state']
                require(sid in source and source[sid] == r['source'], 'Source row changed')
                previous = states.get(sid)
                require(previous == r['previous_state'] and (previous, state) in
                        ((None, 'offered'), ('offered', 'queued'), ('queued', 'dispatched'), ('dispatched', 'completed')),
                        'Incomplete/failed/illegal queue chain')
                t = integer(r['actual_transition']['monotonic_ns'], 'transition clock')
                require(t <= integer(r['recorded']['monotonic_ns'], 'publication clock'), 'Unpublished transition')
                if state == 'offered':
                    require(r['measurement_id'] not in mids.values(), 'Repeated measurement identity')
                    mids[sid] = r['measurement_id']
                    times[sid] = {'scheduled': integer(r['scheduled_monotonic_ns'], 'arrival clock')}
                require(mids[sid] == r['measurement_id'] and t >= max(times[sid].values()), 'Changed identity/reversed clock')
                require(r['scheduled_monotonic_ns'] == times[sid]['scheduled'], 'Retimed arrival')
                times[sid][state] = t
                states[sid] = state
                if state == 'dispatched':
                    require(active is None, 'This parser supports the registered serial-client contract only')
                    active = sid
                    dispatched.append(sid)
                if state == 'completed':
                    require(active == sid, 'Completion has no matching active slot')
                    active = None
    require(len(clocks) == len(initial) == len(final) == 1, 'Missing/ambiguous boundary evidence')
    require(active is None and set(states) == set(source) and all(s == 'completed' for s in states.values()),
            'Full cohort did not complete; partial completed-only averages are prohibited')
    require(dispatched == [r['source_query_id'] for r in mapped], 'FIFO order changed')
    require(set(calls) == set(requests) == set(mids.values()), 'Unbound call/request/arrival population')
    lo = integer(clocks[0]['start_monotonic_ns'], 'cohort start')
    hi = integer(clocks[0]['arrival_end_monotonic_ns'], 'arrival horizon')
    require(hi - lo == int(cfg['horizon_seconds'] * 1e9), 'Horizon changed')
    rows, intervals = [], []
    for sid in dispatched:
        c, request, transitions = calls[mids[sid]], requests[mids[sid]], times[sid]
        arrival = lo + int(source[sid]['offset_ns'])
        start = integer(c['client_execute_start']['monotonic_ns'], 'SQL start')
        end = integer(c['fetch_end']['monotonic_ns'], 'fetch end')
        require(c['marker'] == request['marker'], 'Call/request marker differs')
        require(lo <= arrival < hi and arrival == transitions['scheduled'], 'Source arrival outside registered horizon')
        require(arrival <= transitions['offered'] <= transitions['dispatched'] <= start < end <= transitions['completed'],
                'Actual response chronology invalid')
        response, wait, service = end - arrival, start - arrival, end - start
        require(response == wait + service == c['client_elapsed_ns'] + wait, 'Response decomposition changed')
        intervals.append((arrival, end))
        rows.append({'source_query_id': sid, 'measurement_id': mids[sid],
                     'response_ns': response, 'wait_ns': wait, 'service_ns': service,
                     'generator_lateness_ns': transitions['offered'] - arrival,
                     'completed_before_horizon': end <= hi})
    response = sum(r['response_ns'] for r in rows)
    wait = sum(r['wait_ns'] for r in rows)
    service = sum(r['service_ns'] for r in rows)
    area = _area(intervals)
    require(response == wait + service == area == saved['sum_response_ns'], 'Saved response sum or independent area differs')
    require(wait == saved['sum_wait_before_call_ns'] and service == saved['sum_service_ns'], 'Saved component sum differs')
    require(len(rows) == saved['completed'] == saved['arrival_count'] and saved['failed'] == saved['unfinished'] == 0,
            'Saved cohort counts differ')
    require(action_count == saved['maintenance_count'], 'Maintenance count differs')
    end = max(b for _, b in intervals)
    require(all(sha(directory / name) == value for name, value in expected.items()), 'Input changed while reading')
    return {'schema': 'research_response_accounting_v1', 'status': 'supplementary_full_drain_accounting_only',
            'experiment_id': cfg['experiment_id'], 'input_sha256': expected,
            'source_start_utc': cfg['source_start_utc'], 'source_end_utc': cfg['source_end_utc'],
            'mapping_sha256': expected['mapped_arrivals.csv'],
            'initial_layout_signature': initial[0]['layout_signature'],
            'initial_file_state': initial[0]['file_state'], 'final_file_state': final[0]['file_state'],
            'offered': len(rows), 'completed': len(rows), 'failed': 0, 'residual_queries': 0,
            'maintenance_count': action_count, 'sum_response_ns': response,
            'sum_wait_ns': wait, 'sum_service_ns': service, 'outstanding_area_ns': area,
            'outstanding_area_until_arrival_horizon_ns': _area(intervals, hi),
            'mean_response_seconds': response / len(rows) / 1e9,
            'response_quantiles_seconds': {str(p): nearest_rank([r['response_ns'] for r in rows], p) / 1e9
                                          for p in (0.5, 0.95, 0.99)},
            'quantile_method': 'nearest rank on the entire completed offered cohort',
            'arrival_horizon_seconds': (hi - lo) / 1e9,
            'last_query_result_after_start_seconds': (end - lo) / 1e9,
            'post_arrival_drain_seconds': max(0, end - hi) / 1e9,
            'completed_inside_arrival_horizon': sum(r['completed_before_horizon'] for r in rows),
            'attributable_cpu_core_seconds': None, 'physical_io_bytes': None,
            'resource_evidence_status': 'not reconstructed by this response-only parser',
            'query_rows': rows, 'physical_acceptance_changed': False,
            'limitations': ['Supplementary accounting does not rerun physical correctness, task, publication or attribution gates.',
                           'Client service time includes engine/driver work; it is not executor CPU.',
                           'A no-maintenance arm cannot prove equal-obligation timing-policy efficiency.']}
