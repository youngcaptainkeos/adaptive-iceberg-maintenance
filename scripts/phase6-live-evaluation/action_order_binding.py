"""Bind registered action order to actual submissions and raw active-task observations."""
from experiment_validation import require
from statement_timing import check_completed_statement


def verify_action_order(records, cfg):
    order = cfg.get('action_order')
    if order is None:
        require(not any(r['kind'] == 'query_task_observed_active' for r in records),
                'Unregistered query-first observation')
        return None  # Historical protocols make no new order-contract assertion.
    require(order in ('rewrite_first', 'query_first'), 'Unknown registered order')
    requests = {r['measurement_id']: r for r in records if r['kind'] == 'statement_requested'}
    completed = {r['measurement_id']: check_completed_statement(r) for r in records
                 if r['kind'] == 'statement_completed'}
    queries = [r for r in requests.values() if r['role'] == 'during_rewrite']
    actions = [r for r in requests.values() if r['role'] == 'maintenance']
    require(len(queries) == len(actions) == 1, 'One actual query/action pair required')
    query, action = queries[0], actions[0]
    require(query['measurement_id'] in completed and action['measurement_id'] in completed,
            'Unfinished action-order pair')
    q = completed[query['measurement_id']]
    a = completed[action['measurement_id']]
    first, second = (q, a) if order == 'query_first' else (a, q)
    require(first['client_execute_start']['monotonic_ns'] < second['client_execute_start']['monotonic_ns'],
            'Actual submission order differs from registration')
    kind = 'query_task_observed_active' if order == 'query_first' else 'rewrite_task_observed_active'
    observations = [r for r in records if r['kind'] == kind]
    require(len(observations) == 1, 'Missing/ambiguous active-task trigger')
    observed = observations[0]
    if order == 'query_first':
        require(observed['measurement_id'] == query['measurement_id'], 'Active query identity differs')
    target = 'local.' + cfg['destination_table'].removeprefix('local.')
    def matches(stage):
        text = str(stage.get('description', ''))
        identity = query['marker'] in text if order == 'query_first' else (
            text.startswith('Rewriting ') and text.endswith(' in ' + target))
        return identity and stage.get('status') == 'ACTIVE' and stage.get('numActiveTasks', 0) > 0
    preceding = [r for r in records if r['kind'] == 'spark_rest'
                 and r['resource'] == 'stages?status=active'
                 and r['recorded']['monotonic_ns'] <= observed['recorded']['monotonic_ns']]
    require(preceding, 'No recorded active-stage response')
    response = preceding[-1]
    stages = [s for s in response['payload'] if matches(s)]
    require(response['app_id'] == cfg['spark_app_id'] and stages
            and observed['stage_ids'] == [s['stageId'] for s in stages],
            'Trigger differs from raw application/task response')
    require(response['request_start']['monotonic_ns'] <= response['response_end']['monotonic_ns']
            and first['client_execute_start']['monotonic_ns'] <= response['response_end']['monotonic_ns']
            <= observed['recorded']['monotonic_ns']
            <= second['request_start']['monotonic_ns'], 'Active-stage trigger chronology differs')
    return {'action_order': order, 'query_measurement_id': query['measurement_id'],
            'maintenance_measurement_id': action['measurement_id'], 'trigger_stage_ids': observed['stage_ids'],
            'actual_submission_order_verified': True, 'raw_active_task_trigger_verified': True,
            'scope': 'Submission order and actual active-task trigger; completed task overlap is a separate gate.'}
