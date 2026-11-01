"""Independently bind real child counter frames to durable parent publications."""
import hashlib
import json
from pathlib import Path
from three_model_maintenance.runtime.counter_process import CONTRACT, encode


def require(value, message):
    if not value:
        raise ValueError(message)


def audit(directory, telemetry, *, validation_windows=False, expected_until=None, expected_journal=None,
          expected_lifecycle=None):
    directory = Path(directory)
    raw = (directory/'telemetry_acquisition.jsonl').read_bytes()
    rows = [json.loads(s) for s in (directory/'events.jsonl').read_text().splitlines()]
    starts = [r for r in rows if r['kind'] == 'telemetry_acquisition_started']
    ends = [r for r in rows if r['kind'] == 'telemetry_acquisition_finished']
    require(len(starts) == len(ends) == 1, 'Missing/duplicate acquisition lifecycle')
    start, end = starts[0], ends[0]
    if expected_until is not None:
        require(start['until_utc'] == expected_until, 'Acquisition deadline differs from registration')
    if expected_journal is not None:
        require(start['journal_path'] == str(expected_journal), 'Acquisition journal identity differs')
    if expected_lifecycle is not None:
        require(expected_lifecycle == 'workload_and_terminal_archive_then_cooperative_finish_v1',
                'Unknown counter acquisition lifecycle')
        terminal_archives = [r for r in rows if r['kind'] == 'terminal_engine_archive_checkpoint' and r['terminal']]
        phases = [r for r in rows if r['kind'] == 'telemetry_acquisition_phase_complete']
        require(len(terminal_archives) == len(phases) == 1 and phases[0]['contract'] == expected_lifecycle,
                'Missing registered acquisition phase boundary')
        terminal_time = terminal_archives[0]['recorded']['monotonic_ns']
        phase_time = phases[0]['recorded']['monotonic_ns']
        child_terminals = [frame for frame in map(json.loads, raw.splitlines())
                           if frame['kind'] == 'telemetry_acquisition_terminal']
        require(len(child_terminals) == 1 and terminal_time <= child_terminals[0]['recorded']['monotonic_ns'],
                'Actual child acquisition terminal precedes workload archive')
        require(terminal_time <= end['recorded']['monotonic_ns'] <= phase_time,
                'Counter acquisition stopped before workload terminal archive')
        later_sql = [r for r in rows if r['kind'] == 'statement_requested' and r['recorded']['monotonic_ns'] > terminal_time]
        require(later_sql and all(phase_time <= r['request_start']['monotonic_ns'] for r in later_sql),
                'Validation SQL preceded cooperative acquisition completion')
    require(start['contract'] == end['contract'] == CONTRACT and end['returncode'] == 0
            and start['interval_seconds'] == telemetry['interval_seconds'], 'Different acquisition contract')
    copies = [r for r in rows if 'acquisition_source' in r]
    publications = [r for r in rows if r['kind'] == 'telemetry_acquisition_publication']
    raw_lines = raw.splitlines(keepends=True)
    require(len(raw_lines) == len(copies) == len(publications) == end['frame_count'], 'Dropped/duplicate acquisition publication')
    require(start['recorded']['monotonic_ns'] <= copies[0]['recorded']['monotonic_ns']
            and publications[-1]['recorded']['monotonic_ns'] <= end['recorded']['monotonic_ns'],
            'Acquisition lifecycle order differs')
    previous_hash, offset, previous_counters, samples = '', 0, None, []
    terminal = False
    for index, (line, parent) in enumerate(zip(raw_lines, copies)):
        frame = json.loads(line); source = parent['acquisition_source']; envelope = source['envelope']
        require(line == (encode(frame)+'\n').encode() and frame == envelope['frame'], 'Raw counter bytes differ')
        chain = hashlib.sha256(previous_hash.encode()+line).hexdigest(); offset += len(line)
        require(frame['sequence'] == index and frame['contract'] == CONTRACT and
                frame['child_pid'] == start['child_pid'] == end['child_pid'] and frame['boot_id'] == start['boot_id']
                and envelope['previous_chain_sha256'] == previous_hash and envelope['chain_sha256'] == chain
                and envelope['raw_sha256'] == hashlib.sha256(line).hexdigest()
                and envelope['end_offset'] == offset, 'Counter sequence/hash/identity differs')
        previous_hash = chain
        require(frame['recorded']['monotonic_ns'] <= envelope['child_durable_after']['monotonic_ns']
                <= source['received']['monotonic_ns'] <= parent['recorded']['monotonic_ns'], 'Counter publication chronology differs')
        publication = publications[index]
        require(publication['sequence'] == index and publication['child_kind'] == frame['kind']
                and parent['recorded']['monotonic_ns'] <= publication['parent_durable_after']['monotonic_ns']
                <= publication['recorded']['monotonic_ns'], 'Missing durable publication handoff')
        require(parent['kind'] == frame['kind'] and all(parent[k] == v for k, v in frame['fields'].items()),
                'Counter fields changed on publication')
        kind, fields = frame['kind'], frame['fields']
        require(not terminal and ((index == 0) == (kind == 'telemetry_origin')), 'Invalid origin/terminal order')
        if kind == 'telemetry_acquisition_terminal':
            require(index == len(raw_lines)-1 and fields['reason'] == 'cooperative_stop', 'Incomplete acquisition')
            terminal = True
            continue
        require(kind in ('telemetry_origin', 'telemetry_interval'), 'Unexpected acquisition frame')
        current = fields['counters']
        require(frame['read_started']['monotonic_ns'] <= current['timestamp']['monotonic_ns']
                <= frame['read_ended']['monotonic_ns'] <= frame['recorded']['monotonic_ns'], 'Invalid read clocks')
        if kind == 'telemetry_interval':
            require(previous_counters is not None, 'Interval lacks counter origin')
            elapsed = (current['timestamp']['monotonic_ns']-previous_counters['timestamp']['monotonic_ns'])/1e9
            total = current['cpu_total_s']-previous_counters['cpu_total_s']
            idle = current['cpu_idle_s']-previous_counters['cpu_idle_s']
            read = current['read_bytes']-previous_counters['read_bytes']
            write = current['write_bytes']-previous_counters['write_bytes']
            require(0 < elapsed <= telemetry['max_interval_seconds'] and total > 0 and 0 <= idle <= total
                    and read >= 0 and write >= 0, 'Real counter interval fails original gate')
            expected = dict(start=previous_counters['timestamp'], end=current['timestamp'], elapsed_seconds=elapsed,
                cpu_busy_fraction=(total-idle)/total, read_bytes_per_second=read/elapsed,
                write_bytes_per_second=write/elapsed, available_memory_bytes=current['available_memory_bytes'],
                total_memory_bytes=current['total_memory_bytes'], counters=current)
            require(fields == expected, 'Counter arithmetic differs from raw deltas')
            samples.append(fields)
        previous_counters = current
    require(terminal and samples and end['journal_sha256'] == hashlib.sha256(raw).hexdigest()
            and end['journal_bytes'] == len(raw) and end['chain_sha256'] == previous_hash, 'Incomplete journal receipt')
    window_proofs, windows = [], []
    if validation_windows:
        from telemetry_binding import verify_window
        records = [r for r in rows if r['kind'] == 'process_sampling_validation_windows']
        require(len(records) == 1 and [w['window_seconds'] for w in records[0]['windows']] == telemetry['window_seconds'],
                'Missing original declared validation windows')
        windows = records[0]['windows']
        for window in windows:
            window_proofs.append(verify_window(rows, window,
                max_interval_seconds=telemetry['max_interval_seconds'], max_age_seconds=telemetry['max_age_seconds'],
                minimum_coverage_fraction=telemetry['minimum_coverage_fraction']))
    else:
        # SF10's existing observation audit independently reconstructs these
        # windows; this additional gate binds their frontiers to new handoffs.
        observations = [r for r in rows if r['kind'] in ('query_observation', 'maintenance_decision_observation')]
        require(observations, 'Missing physical observation windows')
        windows = [w for observation in observations for w in observation['windows']]
    for window in windows:
        for parent, publication in zip(copies, publications):
            if parent['kind'] == 'telemetry_interval' and parent['end']['monotonic_ns'] <= window['last_available_sample_end_monotonic_ns']:
                require(publication['recorded']['monotonic_ns'] <= window['window_end_monotonic_ns'],
                        'Window uses counter before durable parent publication')
    return dict(status='passed_raw_counter_handoff_and_original_interval_gate_only',
                journal_sha256=end['journal_sha256'], sample_count=len(samples),
                maximum_interval_seconds=max(s['elapsed_seconds'] for s in samples),
                child_pid=start['child_pid'], boot_id=start['boot_id'],
                independent_window_proofs=window_proofs,
                durable_publication_frontiers_checked=len(windows),
                measured_child_cpu=copies[-1]['acquisition_source']['envelope']['frame']['fields'],
                no_imputed_samples=True, physical_workload_pass_claimed=False)
