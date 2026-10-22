"""New opt-in client-state/feature publication journal, separate from frozen code.

An after-fsync timestamp is a conservative observed upper bound, never the exact
instant storage committed. Publication overhead is measured, not subtracted from
query response. The state describes this client's pending calls, not Spark activity.
"""
import copy
import hashlib
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from three_model_maintenance.contracts import QUERY_FEATURES, require, timestamp


def stamp():
    return {'utc': datetime.now(timezone.utc).isoformat(), 'monotonic_ns': time.monotonic_ns()}


def clock_order(*points):
    require(all(type(p['monotonic_ns']) is int and p['monotonic_ns'] > 0 for p in points), 'Invalid monotonic clock')
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] and timestamp(a['utc']) <= timestamp(b['utc'])
                for a, b in zip(points, points[1:])), 'Capture/publication/call clock inversion')


def validate_publication(receipt):
    require(receipt['schema_version'] == 'three_model_live_feature_receipt_v1', 'Historical capture is not live publication')
    require(receipt['pending_semantics'] == 'this_client_request_pending_at_snapshot', 'Do not infer engine overlap')
    require(receipt['exact_persistence_time_utc'] is None, 'No invented exact storage timestamp')
    require(receipt['process_id'] > 0 and receipt['process_boot_id'] and receipt['measurement_id'], 'Clock/process identity required')
    require(receipt['state_version'] >= 0 and type(receipt['client_pending']) is bool and
            receipt['client_pending'] == bool(receipt['pending_measurement_ids']), 'Pending snapshot differs')
    require(receipt['queue_depth'] >= 0 and type(receipt['queue_depth']) is int, 'Invalid observed queue state')
    clock_order(receipt['capture_at'], receipt['feature_persisted_observed_at'], receipt['receipt_persisted_observed_at'])
    for capture in receipt['feature_capture_at'].values():
        clock_order(capture, receipt['capture_at'])
    require(set(receipt['feature_capture_at']) == set(receipt['feature_values']), 'Feature capture binding differs')
    require(receipt['feature_sha256'] == hashlib.sha256(json.dumps(receipt['feature_values'], sort_keys=True,
                                                                 allow_nan=False).encode()).hexdigest(), 'Changed published features')
    return receipt


class PublicationJournal:
    def __init__(self, path, *, experiment_id, protocol_sha256, max_feature_age_ns, require_unchanged_state_at_call):
        require(experiment_id and len(protocol_sha256) == 64 and all(c in '0123456789abcdef' for c in protocol_sha256), 'Registered identity/protocol required')
        require(type(max_feature_age_ns) is int and max_feature_age_ns > 0, 'Register maximum feature age with rationale')
        require(require_unchanged_state_at_call is True, 'Register conservative call-state stability gate')
        self.lock = threading.RLock()
        self.stream = Path(path).open('x', encoding='utf-8')
        self.experiment_id = experiment_id
        self.protocol_sha256 = protocol_sha256
        self.max_age = max_feature_age_ns
        self.version = 0
        self.pending = set()
        self.queue = {}
        self.published = {}
        self.used = set()
        self.boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.process_id = os.getpid()

    def _append(self, kind, **data):
        # All callers hold the same state/journal lock.
        record = dict(data, kind=kind, experiment_id=self.experiment_id, protocol_sha256=self.protocol_sha256,
                      process_id=self.process_id, process_boot_id=self.boot_id, captured_at=stamp())
        self.stream.write(json.dumps(record, allow_nan=False, sort_keys=True) + '\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())
        return stamp()  # Actual observation after fsync returned; no durability-time claim.

    def maintenance_requested(self, measurement_id):
        with self.lock:
            require(measurement_id and measurement_id not in self.pending, 'Duplicate pending request')
            self._append('client_maintenance_requested', measurement_id=measurement_id, next_state_version=self.version + 1)
            self.pending.add(measurement_id)
            self.version += 1

    def maintenance_returned(self, measurement_id, *, outcome):
        with self.lock:
            require(measurement_id in self.pending and outcome in ('completed', 'failed'), 'Unknown request/outcome')
            self._append('client_maintenance_returned', measurement_id=measurement_id, outcome=outcome, next_state_version=self.version + 1)
            self.pending.remove(measurement_id)
            self.version += 1

    def queue_transition(self, source_query_id, state, *, unsubmitted_measurement_id=None):
        with self.lock:
            previous = self.queue.get(source_query_id)
            allowed = {None: ('offered',), 'offered': ('queued', 'dispatched', 'failed'),
                       'queued': ('dispatched', 'failed'), 'dispatched': ('completed', 'failed')}
            requeue = previous == 'dispatched' and state == 'queued' and bool(unsubmitted_measurement_id)
            require(source_query_id and (state in allowed.get(previous, ()) or requeue), 'Invalid/duplicate queue transition')
            self._append('client_queue_transition', source_query_id=source_query_id, state=state, next_state_version=self.version + 1)
            self.queue[source_query_id] = state
            self.version += 1

    def publish(self, *, measurement_id, feature_values, feature_capture_at, source_context):
        with self.lock:
            require(measurement_id and measurement_id not in self.published, 'Duplicate publication')
            values = copy.deepcopy(feature_values); clocks = copy.deepcopy(feature_capture_at)
            require(set(values) <= QUERY_FEATURES, 'Unregistered/post-outcome predictor')
            require(values and set(clocks) == set(values) and source_context, 'Missing actual capture/source binding')
            require('maintenance_client_pending_at_feature_time' not in values and 'queue_depth_at_feature_time' not in values,
                    'Client state must come from the locked store, not inferred external flags')
            captured = stamp()
            for clock in clocks.values():
                clock_order(clock, captured)
                require(captured['monotonic_ns'] - clock['monotonic_ns'] <= self.max_age, 'Stale feature capture')
            values['maintenance_client_pending_at_feature_time'] = bool(self.pending)
            values['queue_depth_at_feature_time'] = sum(v == 'queued' for v in self.queue.values())
            clocks['maintenance_client_pending_at_feature_time'] = captured
            clocks['queue_depth_at_feature_time'] = captured
            receipt = {'schema_version': 'three_model_live_feature_receipt_v1', 'experiment_id': self.experiment_id,
                       'measurement_id': measurement_id, 'process_id': self.process_id, 'process_boot_id': self.boot_id,
                       'protocol_sha256': self.protocol_sha256, 'source_context': copy.deepcopy(source_context),
                       'capture_at': captured, 'feature_values': values, 'feature_capture_at': clocks,
                       'feature_sha256': hashlib.sha256(json.dumps(values, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                       'pending_semantics': 'this_client_request_pending_at_snapshot', 'client_pending': bool(self.pending),
                       'pending_measurement_ids': sorted(self.pending), 'queue_depth': values['queue_depth_at_feature_time'],
                       'state_version': self.version, 'exact_persistence_time_utc': None,
                       'runtime_adapter_accepted': False, 'candidate_binding_issues': []}
            receipt['feature_persisted_observed_at'] = self._append('feature_capture', receipt=receipt)
            receipt['receipt_persisted_observed_at'] = self._append('feature_publication_observed', receipt=receipt)
            validate_publication(receipt)
            self.published[measurement_id] = copy.deepcopy(receipt)
            return copy.deepcopy(receipt)

    def execute_maintenance(self, cursor, sql, *, measurement_id):
        """Track the actual client call through successful fetch or raised failure.

        Caller must use an independently registered fresh table and connection;
        this primitive neither creates tables nor retries failed maintenance.
        """
        require(sql, 'Actual maintenance SQL required')
        self.maintenance_requested(measurement_id)
        try:
            cursor.execute(sql)
            rows = cursor.fetchall() if cursor.description else []
        except Exception:
            self.maintenance_returned(measurement_id, outcome='failed')
            raise
        self.maintenance_returned(measurement_id, outcome='completed')
        return rows

    def execute_query(self, cursor, sql, *, publication, latest_start_ns):
        """Opt-in actual cursor call; never invoked by read-only historical audit.

        The registered cutoff and freshness are checked after durable intent. State
        is a feature-time snapshot; no atomic engine exposure or SQL overlap claim.
        """
        validate_publication(publication)
        measurement_id = publication['measurement_id']
        require(type(latest_start_ns) is int and latest_start_ns > 0 and sql, 'Actual query/cutoff required')
        with self.lock:
            require(publication == self.published.get(measurement_id) and measurement_id not in self.used, 'Changed/reused publication')
            if self.version != publication['state_version']:
                self._append('query_not_submitted', measurement_id=measurement_id, reason='client_state_changed_since_snapshot')
                raise ValueError('Client state changed since feature snapshot; no SQL submitted')
            self._append('query_intent', measurement_id=measurement_id, sql=sql,
                         publication_observed_at=publication['receipt_persisted_observed_at'])
            self.used.add(measurement_id)
        # Stamp after lock release, not before an unmeasured lock-release delay.
        started = stamp()
        clock_order(publication['receipt_persisted_observed_at'], started)
        refusal = ('registered_start_cutoff_reached' if started['monotonic_ns'] >= latest_start_ns
                   else 'feature_expired_before_call' if any(
                       started['monotonic_ns'] - point['monotonic_ns'] > self.max_age
                       for point in publication['feature_capture_at'].values()) else None)
        if refusal is not None:
            with self.lock:
                self._append('query_not_submitted', measurement_id=measurement_id, reason=refusal, checked_at=started)
            raise ValueError(refusal + '; no SQL submitted')
        try:
            # No journal/fsync/metadata RPC between the measured client boundary and execute.
            cursor.execute(sql)
            rows = cursor.fetchall() if cursor.description else []
            ended = stamp()
        except Exception as exc:
            with self.lock:
                self._append('query_failed', measurement_id=measurement_id, call_start=started,
                             failure_observed_at=stamp(), error_type=type(exc).__name__, error=str(exc))
            raise
        with self.lock:
            self._append('query_completed', measurement_id=measurement_id, call_start=started, fetch_end=ended,
                         elapsed_ns=ended['monotonic_ns'] - started['monotonic_ns'],
                         feature_publication=publication, returned_row_count=len(rows))
        return rows

    def close(self):
        with self.lock:
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.stream.close()
