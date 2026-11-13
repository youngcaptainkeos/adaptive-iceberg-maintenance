"""Exact SQL execution/job binding reference for a prospective capture repair.

Caller must separately bind archival time, engine/app identity, complete stage/
task attempts and explicit counters. This function alone cannot certify Gate A.
"""
from .common import integer, require


def exact_bindings(requests, completed_calls, sql_inventory):
    request_by_id = {r['measurement_id']: r for r in requests}
    require(requests and completed_calls and sql_inventory, 'No actual ownership population')
    require(len(request_by_id) == len(requests), 'Duplicate request identities')
    require(len({r['marker'] for r in requests}) == len(requests), 'Repeated request SQL marker')
    require(len({r['measurement_id'] for r in completed_calls}) == len(completed_calls), 'Duplicate completed calls')
    require(len({r['id'] for r in sql_inventory}) == len(sql_inventory), 'Repeated SQL execution IDs')
    by_description = {}
    for row in sql_inventory:
        integer(row['id'], 'SQL execution ID')
        by_description.setdefault(row['description'], []).append(row)
    bindings = {}
    used_executions = set()
    for call in completed_calls:
        mid = call['measurement_id']
        require(mid in request_by_id, 'Completed call without original request')
        request = request_by_id[mid]
        require(call['marker'] == request['marker'], 'Request/completion marker differs')
        matches = by_description.get('/* ' + request['marker'] + ' */\n' + request['sql'], [])
        require(len(matches) == 1, 'Absent or ambiguous exact marked SQL: ' + mid)
        row = matches[0]
        require(row['id'] not in used_executions, 'SQL execution assigned to multiple calls')
        used_executions.add(row['id'])
        require(row['status'] == 'COMPLETED', 'SQL execution is not terminal COMPLETED')
        for field in ('successJobIds', 'runningJobIds', 'failedJobIds'):
            require(type(row[field]) is list, 'Explicit SQL job list required: ' + field)
            require(len(set(row[field])) == len(row[field]), 'Duplicate SQL/job link')
            for value in row[field]:
                integer(value, field)
        require(not row['runningJobIds'] and not row['failedJobIds'], 'Running/failed jobs remain in SQL execution')
        bindings[mid] = {'sql_execution_id': row['id'], 'success_job_ids': sorted(row['successJobIds'])}
    return {'bindings': bindings, 'completed_calls': len(completed_calls),
            'scope': 'exact_SQL_job_links_only', 'task_completeness_certified': False,
            'all_unknown_engine_work_certified': False, 'original_failure_accepted': False}
