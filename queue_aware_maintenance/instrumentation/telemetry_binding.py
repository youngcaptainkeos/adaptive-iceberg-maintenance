"""Independently check exact feature-window bounds against raw observed counters."""
import json
from pathlib import Path
from experiment_validation import require


def ordered_sum(values):
    # Specify left-to-right IEEE additions across Python versions. Built-in sum
    # changed its float algorithm in Python 3.12; do not loosen exact evidence gates.
    result = 0.0
    for value in values:
        result += value
    return result


def verify_window(rows, window, *, max_interval_seconds, max_age_seconds, minimum_coverage_fraction):
    require(window.get('window_contract') == 'completed_counter_window_v1',
            'Exact recorded window bounds required; no inferred historical cutoff')
    low, high = (window['window_start_monotonic_ns'], window['window_end_monotonic_ns'])
    require(all(isinstance(v, int) and not isinstance(v, bool) for v in (low, high))
            and 0 <= low < high and high-low == int(window['window_seconds']*1e9), 'Invalid exact window bounds')
    frontier = window['last_available_sample_end_monotonic_ns']
    require(isinstance(frontier, int) and not isinstance(frontier, bool) and low < frontier <= high,
            'Invalid explicitly recorded available-sample frontier')
    origins = [r for r in rows if r['kind'] == 'telemetry_origin']
    require(len(origins) == 1, 'Exactly one actual counter origin required per observer ledger')
    previous = origins[0]['counters']
    intervals = []
    for row in rows:
        if row['kind'] != 'telemetry_interval':
            continue
        current = row['counters']
        require(row['start'] == previous['timestamp'] and row['end'] == current['timestamp'],
                'Broken raw counter interval chain')
        elapsed = (current['timestamp']['monotonic_ns']-previous['timestamp']['monotonic_ns'])/1e9
        total = current['cpu_total_s']-previous['cpu_total_s']
        idle = current['cpu_idle_s']-previous['cpu_idle_s']
        read = current['read_bytes']-previous['read_bytes']
        write = current['write_bytes']-previous['write_bytes']
        require(elapsed > 0 and total > 0 and 0 <= idle <= total and read >= 0 and write >= 0,
                'Counter reset/invalid observed interval')
        require(row['elapsed_seconds'] == elapsed and row['cpu_busy_fraction'] == (total-idle)/total
                and row['read_bytes_per_second'] == read/elapsed and row['write_bytes_per_second'] == write/elapsed,
                'Counter-derived telemetry rates differ from raw measurements')
        require(row['available_memory_bytes'] == current['available_memory_bytes']
                and row['total_memory_bytes'] == current['total_memory_bytes']
                and 0 <= current['available_memory_bytes'] <= current['total_memory_bytes']
                and current['total_memory_bytes'] > 0, 'Invalid observed memory counters')
        if low < row['end']['monotonic_ns'] <= frontier:
            intervals.append(row)
        previous = current
    require(intervals and intervals[0]['start']['monotonic_ns'] <= low
            and intervals[-1]['end']['monotonic_ns'] == frontier, 'Insufficient raw history/frontier missing')
    require(all(r['elapsed_seconds'] <= max_interval_seconds for r in intervals), 'Raw sampling gap')
    freshness = (high-intervals[-1]['end']['monotonic_ns'])/1e9
    require(0 <= freshness <= max_age_seconds, 'Raw window is stale or uses future samples')
    weights = [(r['end']['monotonic_ns']-max(low,r['start']['monotonic_ns']))/1e9 for r in intervals]
    coverage = ordered_sum(weights)
    require(coverage/window['window_seconds'] >= minimum_coverage_fraction, 'Raw coverage below declared gate')
    values = {'covered_seconds':coverage, 'freshness_seconds':freshness}
    for name in ('cpu_busy_fraction', 'read_bytes_per_second', 'write_bytes_per_second'):
        values[name] = ordered_sum(w*r[name] for w,r in zip(weights,intervals))/coverage
    values['memory_used_fraction'] = ordered_sum(w*(r['total_memory_bytes']-r['available_memory_bytes'])/r['total_memory_bytes'] for w,r in zip(weights,intervals))/coverage
    require(window['feature_timestamp'] == intervals[-1]['end']['utc'], 'Feature UTC differs from last available sample')
    require(window['measured_at']['monotonic_ns'] >= high, 'Window recorded before its cutoff')
    require(all(window[name] == value for name,value in values.items()), 'Reported feature window differs from raw-counter reconstruction')
    return {'intervals':len(intervals), 'exact_cutoff_verified':True, **values}


def verify_ledger(path, config):
    rows = [json.loads(line) for line in Path(path).open()]
    require(all(r['schema_version'] == 'physical_event_v1' and r['experiment_id'] == config['experiment_id'] for r in rows),
            'Mixed/unknown observer ledger')
    windows = [r for r in rows if r['kind'] == 'validated_window']
    require(len(windows) == len(config['window_seconds'])
            and [r['window_seconds'] for r in windows] == config['window_seconds'], 'Missing declared windows')
    return [verify_window(rows,w,max_interval_seconds=config['max_interval_seconds'],max_age_seconds=config['max_age_seconds'],minimum_coverage_fraction=config['minimum_coverage_fraction']) for w in windows]
