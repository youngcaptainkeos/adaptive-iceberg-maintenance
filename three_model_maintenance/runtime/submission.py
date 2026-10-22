"""Actual query recorder with a last-sample age gate after durable intent.

Preserves the original SQL markers, call/result timing and exception records.
No retry, fabricated sample or relaxed freshness threshold.
"""
import uuid
import re
from contextlib import nullcontext
from physical_measurements import StatementRecorder as PhysicalRecorder, stamp
from experiment_validation import require


def sample_age_reason(checked_ns, frontiers, max_age_ns):
    require(type(checked_ns) is int and checked_ns > 0 and type(max_age_ns) is int and max_age_ns > 0,
            'Registered actual clock and sample-age limit required')
    require(frontiers and all(type(v) is int and v > 0 for v in frontiers), 'Missing real sample frontiers')
    if any(v > checked_ns for v in frontiers):
        return 'future_sample_before_rpc'
    if any(checked_ns - v > max_age_ns for v in frontiers):
        return 'stale_sample_before_rpc'
    return None


class SubmissionRecorder(PhysicalRecorder):
    def execute(self, cursor, sql, *, role, query_id=None, measurement_id=None, prepare_submission=None, latest_start_ns=None, sample_frontiers=None, max_sample_age_ns=None):
        require(latest_start_ns is None or (role=='trace_query' and isinstance(latest_start_ns,int)
                and not isinstance(latest_start_ns,bool) and latest_start_ns>0
                and isinstance(query_id,int) and not isinstance(query_id,bool)),'Guarded actual query cutoff required')
        if measurement_id is None:
            measurement_id = uuid.uuid4().hex
        require(isinstance(measurement_id, str) and re.fullmatch(r'[0-9a-f]{32}', measurement_id),
                'Explicit query observation ID must be a real UUID hex identity')
        marker = 'capstone_event_' + measurement_id
        # Serialize only durable preparation/intent, never the RPC or fetch.
        # This prevents archival writes interleaving between fresh features
        # and actual submission; all original timestamps/age gates still apply.
        with self.log.lock if prepare_submission is not None else nullcontext():
            if prepare_submission is not None and prepare_submission() is False:
                return None  # Registered boundary: no intent and no SQL call.
            request_start = stamp()
            self.log.emit('statement_requested', measurement_id=measurement_id,
                          marker=marker, role=role, query_id=query_id, sql=sql,
                          request_start=request_start, timing_contract='client_submission_v1')
        # Check AFTER durable intent logging and lock release, at the actual
        # client call boundary. A queued/admitted request is not an RPC.
        frontiers = sample_frontiers() if sample_frontiers is not None else None
        execute_start = stamp()
        if latest_start_ns is not None and execute_start['monotonic_ns']>=latest_start_ns:
            self.log.emit('statement_not_submitted',measurement_id=measurement_id,marker=marker,
                          role=role,query_id=query_id,request_start=request_start,
                          checked_at=execute_start,latest_start_monotonic_ns=latest_start_ns,
                          reason='horizon_reached_before_rpc',timing_contract='client_submission_v1')
            return {'submitted':False,'measurement_id':measurement_id}
        if frontiers is not None:
            reason = sample_age_reason(execute_start['monotonic_ns'], frontiers, max_sample_age_ns)
            if reason is not None:
                self.log.emit('statement_not_submitted', measurement_id=measurement_id, marker=marker,
                              role=role, query_id=query_id, request_start=request_start, checked_at=execute_start,
                              latest_start_monotonic_ns=latest_start_ns, sample_end_monotonic_ns=frontiers,
                              max_sample_age_ns=max_sample_age_ns, reason=reason, timing_contract='client_submission_v1')
                return {'submitted': False, 'measurement_id': measurement_id, 'refusal_reason': reason}
        try:
            cursor.execute(f'/* {marker} */\n{sql}')
            execute_return = stamp()
            columns = [column[0] for column in cursor.description] if cursor.description else []
            rows = cursor.fetchall() if cursor.description else []
            fetch_end = stamp()
            self.log.emit('statement_completed', measurement_id=measurement_id,
                          marker=marker, role=role, query_id=query_id,
                          request_start=request_start, execute_return=execute_return,
                          client_execute_start=execute_start, timing_contract='client_submission_v1',
                          fetch_end=fetch_end, columns=columns, rows=rows,
                          client_elapsed_ns=fetch_end['monotonic_ns'] - execute_start['monotonic_ns'],
                          request_to_result_ns=fetch_end['monotonic_ns'] - request_start['monotonic_ns'],
                          instrumentation_before_execute_ns=execute_start['monotonic_ns'] - request_start['monotonic_ns'])
            return {'measurement_id': measurement_id, 'marker': marker,
                    'columns': columns, 'rows': rows, 'request_start': request_start,
                    'client_execute_start': execute_start,
                    'execute_return': execute_return, 'fetch_end': fetch_end}
        except Exception as exc:
            self.log.emit('statement_failed', measurement_id=measurement_id,
                          marker=marker, role=role, query_id=query_id,
                          request_start=request_start, failure_time=stamp(),
                          client_execute_start=execute_start, timing_contract='client_submission_v1',
                          error_type=type(exc).__name__, error=str(exc))
            raise

