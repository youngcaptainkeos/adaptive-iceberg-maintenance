"""Read-only checks for real client-submission records; no clock-offset repair."""
from datetime import datetime
import json
from pathlib import Path
from experiment_validation import require

TIMING_FIELDS = ('request_start', 'client_execute_start', 'execute_return', 'fetch_end')
DURATION_FIELDS = ('client_elapsed_ns', 'request_to_result_ns', 'instrumentation_before_execute_ns')


def integer_ns(value, name):
    require(isinstance(value, int) and not isinstance(value, bool) and value >= 0,
            name + ' must be an observed nonnegative integer nanosecond value')
    return value


def check_completed_statement(record):
    require(record.get('schema_version') == 'physical_event_v1'
            and record.get('kind') == 'statement_completed', 'Completed physical statement required')
    require(record.get('timing_contract') == 'client_submission_v1',
            'Actual call-start timing contract required; historical offset repair prohibited')
    require(all(record.get(k) is not None for k in ('experiment_id', 'measurement_id', 'marker', 'role')),
            'Statement identity missing')
    clocks = []
    for field in TIMING_FIELDS:
        value = record[field]
        clocks.append(integer_ns(value['monotonic_ns'], field))
        utc = datetime.fromisoformat(value['utc'].replace('Z', '+00:00'))
        require(utc.utcoffset() is not None and utc.utcoffset().total_seconds() == 0,
                'UTC-qualified physical timestamp required')
    require(clocks[0] <= clocks[1] <= clocks[2] <= clocks[3] and clocks[3] > clocks[1],
            'Invalid monotonic statement order/duration')
    expected = (clocks[3] - clocks[1], clocks[3] - clocks[0], clocks[1] - clocks[0])
    for field, value in zip(DURATION_FIELDS, expected):
        require(integer_ns(record[field], field) == value, 'Recorded duration decomposition mismatch: ' + field)
    return record


def completed_statements(paths):
    requested, completed, failed = {}, {}, set()
    for path in paths:
        require(Path(path).suffix == '.jsonl', 'Raw physical event JSONL required for statement binding')
        with Path(path).open() as stream:
            for line in stream:
                record = json.loads(line)
                kind = record.get('kind')
                if kind not in ('statement_requested', 'statement_completed', 'statement_failed'):
                    continue
                require(record.get('schema_version') == 'physical_event_v1', 'Unknown physical event schema')
                key = (record['experiment_id'], record['measurement_id'])
                if kind == 'statement_requested':
                    require(key not in requested, 'Duplicate statement request identity')
                    requested[key] = record
                elif kind == 'statement_completed':
                    require(key not in completed and key not in failed, 'Duplicate/conflicting statement outcome')
                    completed[key] = check_completed_statement(record)
                else:
                    require(key not in failed and key not in completed, 'Duplicate/conflicting statement outcome')
                    failed.add(key)
    for key, result in completed.items():
        require(key in requested, 'Completed statement has no durable request evidence')
        intent = requested[key]
        require(intent.get('timing_contract') == 'client_submission_v1', 'Request timing contract missing')
        for field in ('request_start', 'marker', 'query_id', 'role'):
            require(intent.get(field) == result.get(field), 'Statement request/result identity differs: ' + field)
    require(failed <= requested.keys(), 'Failed statement has no durable request evidence')
    require(requested.keys() == completed.keys() | failed, 'Incomplete statement ledger cannot validate training')
    require(bool(completed), 'No completed physical statement evidence')
    return completed


def bind_training_rows(frame, paths):
    """Bind timing/identity, not telemetry, layout or task-overlap labels."""
    records = completed_statements(paths)
    for _, row in frame.iterrows():
        key = (row['experiment_id'], row['measurement_id'])
        require(key in records, 'Training row lacks a raw completed statement')
        result = records[key]
        require(isinstance(result.get('query_id'), int) and not isinstance(result['query_id'], bool),
                'Training requires a measured query identity, not a metadata statement')
        require(result.get('query_id') == row['query_id'], 'Training query identity differs from raw statement')
        require(row['timing_contract'] == result['timing_contract'], 'Training timing contract differs')
        for field in TIMING_FIELDS:
            require(row[field + '_monotonic_ns'] == result[field]['monotonic_ns'],
                    'Training monotonic clock differs from raw statement: ' + field)
        for field in DURATION_FIELDS:
            require(row[field] == result[field], 'Training duration differs from raw statement: ' + field)
        # UTC timestamps are chronology/cross-engine identifiers, not subtraction
        # targets. Compare their instants while preserving monotonic service time.
        import pandas as pd
        require(pd.Timestamp(row['query_start_time']) == pd.Timestamp(result['client_execute_start']['utc'])
                and pd.Timestamp(row['query_end_time']) == pd.Timestamp(result['fetch_end']['utc']),
                'Training UTC interval differs from actual call/result boundary')
