"""Action-specific last-moment gates; the legacy query recorder is unchanged."""
from physical_measurements import stamp
from three_model_maintenance.runtime.submission import sample_age_reason


def execute_action(recorder, cursor, sql, mid, prepare, latest_start_ns, frontiers,
                   max_sample_age_ns, inventory_end_ns, max_metadata_age_ns):
    log = recorder.log
    marker = 'capstone_event_' + mid
    log.journal.maintenance_requested(mid)
    try:
        with log.lock:
            prepare()
            requested = stamp()
            log.emit('statement_requested', measurement_id=mid, marker=marker,
                     role='maintenance', query_id=None, sql=sql, request_start=requested,
                     timing_contract='client_submission_v1')
        sample_ends = frontiers()
        start = stamp()
        reason = sample_age_reason(start['monotonic_ns'], sample_ends, max_sample_age_ns)
        if start['monotonic_ns'] >= latest_start_ns:
            reason = 'registered_action_cutoff_before_rpc'
        if not 0 <= start['monotonic_ns'] - inventory_end_ns <= max_metadata_age_ns:
            reason = 'stale_action_inventory_before_rpc'
        if reason:
            log.emit('statement_not_submitted', measurement_id=mid, marker=marker,
                     role='maintenance', query_id=None, request_start=requested,
                     checked_at=start, latest_start_monotonic_ns=latest_start_ns,
                     reason=reason, timing_contract='client_submission_v1')
            raise ValueError('Required action not submitted: ' + reason)
        try:
            cursor.execute(f'/* {marker} */\n{sql}')
            returned = stamp()
            columns = [c[0] for c in cursor.description] if cursor.description else []
            rows = cursor.fetchall() if cursor.description else []
            end = stamp()
            log.emit('statement_completed', measurement_id=mid, marker=marker,
                     role='maintenance', query_id=None, request_start=requested,
                     client_execute_start=start, execute_return=returned, fetch_end=end,
                     timing_contract='client_submission_v1', columns=columns, rows=rows,
                     client_elapsed_ns=end['monotonic_ns']-start['monotonic_ns'],
                     request_to_result_ns=end['monotonic_ns']-requested['monotonic_ns'],
                     instrumentation_before_execute_ns=start['monotonic_ns']-requested['monotonic_ns'])
        except Exception as exc:
            log.emit('statement_failed', measurement_id=mid, marker=marker,
                     role='maintenance', query_id=None, request_start=requested,
                     client_execute_start=start, failure_time=stamp(), error_type=type(exc).__name__,
                     error=str(exc), timing_contract='client_submission_v1')
            raise
    except Exception:
        log.journal.maintenance_returned(mid, outcome='failed')
        raise
    log.journal.maintenance_returned(mid, outcome='completed')
    return dict(measurement_id=mid, marker=marker, columns=columns, rows=rows,
                request_start=requested, client_execute_start=start, execute_return=returned,
                fetch_end=end)
