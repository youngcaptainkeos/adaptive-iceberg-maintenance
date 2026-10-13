"""Reconstruct training exposure from preserved Spark task evidence, without RPCs."""
from datetime import datetime
import json
from pathlib import Path
import re
from engine_overlap import task_intervals, overlap_evidence
from experiment_validation import require


class RecordedTasks:
    def __init__(self, resources):
        self.resources = resources

    def capture_tasks(self, stage_id, attempt_id, task_count):
        key = f'stages/{stage_id}/{attempt_id}/taskList?length={task_count}'
        require(key in self.resources, 'Missing preserved task-attempt response: ' + key)
        tasks = self.resources[key]
        require(isinstance(tasks, list) and len(tasks) == task_count, 'Incomplete preserved task response')
        return tasks


def read_engine_ledgers(paths):
    experiments = {}
    for path in paths:
        require(Path(path).suffix == '.jsonl', 'Raw physical JSONL required')
        with Path(path).open() as stream:
            for line in stream:
                row = json.loads(line)
                require(row.get('schema_version') == 'physical_event_v1', 'Unknown raw physical schema')
                experiment = experiments.setdefault(row['experiment_id'], {'requests': {}, 'completed': {}, 'failed': set(), 'resources': {}})
                kind = row['kind']
                if kind in ('statement_requested', 'statement_completed'):
                    group = experiment['requests' if kind == 'statement_requested' else 'completed']
                    require(row['measurement_id'] not in group, 'Duplicate raw statement identity')
                    group[row['measurement_id']] = row
                elif kind == 'statement_failed':
                    require(row['measurement_id'] not in experiment['failed'], 'Duplicate failed statement')
                    experiment['failed'].add(row['measurement_id'])
                elif kind == 'spark_rest':
                    resource = row['resource']
                    # Jobs/stages are evolving snapshots; the last preserved capture
                    # is the final view. Completed task responses must remain stable.
                    if '/taskList?' in resource and resource in experiment['resources']:
                        require(experiment['resources'][resource] == row['payload'], 'Conflicting completed-task captures')
                    experiment['resources'][resource] = row['payload']
    return experiments


def rewrite_evidence(experiment, measurement_id, table):
    require(re.fullmatch(r'local\.[A-Za-z_]\w*\.[A-Za-z_]\w*', table) is not None,
            'Explicit reviewed local catalog table required')
    require(measurement_id in experiment['requests'] and measurement_id in experiment['completed'],
            'Maintenance result lacks durable request/completion')
    request = experiment['requests'][measurement_id]
    result = experiment['completed'][measurement_id]
    require(request['role'] == result['role'] == 'maintenance', 'Incorrect maintenance role')
    sql = request['sql']
    match = re.search(r"\btable\s*=>\s*'([^']+)'", sql, re.IGNORECASE)
    require(re.match(r'\s*CALL\s+local\.system\.rewrite_data_files\s*\(', sql, re.IGNORECASE)
            and match is not None and match.group(1) == table.removeprefix('local.'),
            'Maintenance SQL/table binding mismatch')
    require(len(result['rows']) == 1 and len(result['columns']) == len(result['rows'][0]),
            'Malformed physical rewrite result')
    values = dict(zip(result['columns'], result['rows'][0]))
    for name in ('rewritten_data_files_count', 'added_data_files_count', 'rewritten_bytes_count'):
        require(isinstance(values.get(name), int) and not isinstance(values[name], bool) and values[name] >= 0,
                'Missing/invalid physical rewrite count: ' + name)
    if values['rewritten_data_files_count'] == 0:
        require(values['added_data_files_count'] == values['rewritten_bytes_count'] == 0,
                'No-op rewrite result inconsistent')
        return result, values, []
    require(values['rewritten_bytes_count'] > 0, 'Empty-byte rewrite cannot certify useful exposure')
    resources = experiment['resources']
    require('jobs' in resources and 'stages' in resources, 'Missing preserved engine snapshots')
    tasks = task_intervals(resources['jobs'], resources['stages'], RecordedTasks(resources), rewrite_table=table, request=result)
    return result, values, tasks


def query_exposure(experiment, measurement_id, rewrite_tasks):
    require(measurement_id in experiment['completed'], 'Query lacks completed raw result')
    result = experiment['completed'][measurement_id]
    resources = experiment['resources']
    require('jobs' in resources and 'stages' in resources, 'Missing preserved engine snapshots')
    tasks = task_intervals(resources['jobs'], resources['stages'], RecordedTasks(resources), marker=result['marker'])
    return overlap_evidence(tasks, rewrite_tasks)


def bind_engine_labels(frame, events, raw_paths, tables):
    experiments = read_engine_ledgers(raw_paths)
    require(isinstance(tables, dict) and tables, 'Declare experiment-to-physical-table bindings')
    event_keys = set(zip(events['experiment_id'], events['compaction_event_id']))
    reconstructed = {}
    for experiment_id in frame['experiment_id'].unique():
        require(experiment_id in experiments and experiment_id in tables, 'Missing experiment engine/table provenance')
        raw = experiments[experiment_id]
        maintenance = {key for key, value in raw['requests'].items() if value['role'] == 'maintenance'}
        # Refuse a hidden rewrite under another role, an incomplete/failed rewrite,
        # or an omitted no-op. These can interfere with nominal control queries.
        for key, value in raw['requests'].items():
            if re.match(r'\s*CALL\s+local\.system\.rewrite_data_files\s*\(', value['sql'], re.IGNORECASE):
                require(key in maintenance, 'Rewrite request hidden under a non-maintenance role')
        require(not maintenance & raw['failed'] and maintenance <= raw['completed'].keys(),
                'Failed/incomplete maintenance prevents training-label certification')
        require({(experiment_id, key) for key in maintenance} == {key for key in event_keys if key[0] == experiment_id},
                'Compaction CSV omits or invents raw maintenance attempts')
        for key in maintenance:
            result, values, tasks = rewrite_evidence(raw, key, tables[experiment_id])
            event = events[(events['experiment_id'] == experiment_id) & (events['compaction_event_id'] == key)]
            require(len(event) == 1, 'Nonunique maintenance CSV binding')
            event = event.iloc[0]
            start = result.get('client_execute_start', result['request_start'])
            for column, physical in [('start_time', start['utc']), ('end_time', result['fetch_end']['utc'])]:
                require(datetime.fromisoformat(event[column].replace('Z', '+00:00')) == datetime.fromisoformat(physical),
                        'Maintenance CSV interval differs from physical statement')
            require(event['rewritten_data_files_count'] == values['rewritten_data_files_count']
                    and event['status'] == ('success' if tasks else 'no_op'), 'Maintenance CSV/result mismatch')
            reconstructed[(experiment_id, key)] = tasks
    for _, row in frame.iterrows():
        experiment_id = row['experiment_id']
        query_exposure(experiments[experiment_id], row['measurement_id'], [])
        exposures = {key: query_exposure(experiments[experiment_id], row['measurement_id'], tasks)
                     for key, tasks in reconstructed.items() if key[0] == experiment_id and tasks}
        positive = [key for key, exposure in exposures.items() if exposure['verified_task_lifetime_overlap']]
        if row['compaction_active']:
            require(positive == [(experiment_id, row['compaction_event_id'])],
                    'Treatment requires exactly its measured useful rewrite task exposure')
        else:
            require(not positive, 'Control query has physical rewrite-task contamination')
