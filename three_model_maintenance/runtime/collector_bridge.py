"""Opt-in integration with preserved physical recorder; no retrospective state inference."""
import json
from pathlib import Path
from three_model_maintenance.runtime.publication import PublicationJournal, clock_order, validate_publication
from three_model_maintenance.contracts import require


def build_classes(cfg):
    from physical_measurements import EventLog as PhysicalLog, StatementRecorder as PhysicalRecorder
    from experiment_validation import sha256

    class BoundLog(PhysicalLog):
        def __init__(self, path, experiment_id):
            super().__init__(path, experiment_id)
            self.journal = PublicationJournal(Path(path).parent / 'feature_publication.jsonl',
                experiment_id=experiment_id, protocol_sha256=cfg['_protocol_sha256'],
                max_feature_age_ns=cfg['three_model_capture']['max_feature_age_ns'],
                require_unchanged_state_at_call=True)
            self.observations = {}
            self.publications = {}
            self.unsubmitted = set()

        def emit(self, kind, **fields):
            with self.lock:
                event = super().emit(kind, **fields)
                if kind == 'queue_transition':
                    proof = fields['measurement_id'] if fields['measurement_id'] in self.unsubmitted else None
                    self.journal.queue_transition(fields['source']['source_query_id'], fields['state'],
                                                  unsubmitted_measurement_id=proof)
                elif kind == 'query_observation':
                    self.observations[fields['measurement_id']] = event
                elif kind == 'statement_not_submitted':
                    self.unsubmitted.add(fields['measurement_id'])
                return event

        def close(self):
            self.journal.close()
            super().close()

    class BoundRecorder(PhysicalRecorder):
        def execute(self, cursor, sql, *, role, query_id=None, measurement_id=None,
                    prepare_submission=None, latest_start_ns=None):
            if role == 'maintenance':
                require(measurement_id, 'Explicit maintenance identity required')
                self.log.journal.maintenance_requested(measurement_id)
                try:
                    result = super().execute(cursor, sql, role=role, query_id=query_id, measurement_id=measurement_id)
                except Exception:
                    self.log.journal.maintenance_returned(measurement_id, outcome='failed')
                    raise
                self.log.journal.maintenance_returned(measurement_id, outcome='completed')
                return result
            if role != 'trace_query':
                return super().execute(cursor, sql, role=role, query_id=query_id, measurement_id=measurement_id,
                                       prepare_submission=prepare_submission, latest_start_ns=latest_start_ns)
            require(prepare_submission is not None and latest_start_ns is not None, 'Registered durable preparation and actual-RPC cutoff required')

            def prepare_bound():
                if prepare_submission() is False:
                    return False
                observed = self.log.observations[measurement_id]
                values = {'query_id': observed['query_id'], **observed['file_state']}
                clocks = {name: observed['recorded'] for name in values}
                for window in observed['windows']:
                    for name in ('cpu_busy_fraction', 'memory_used_fraction', 'read_bytes_per_second', 'write_bytes_per_second'):
                        field = name + '_' + str(window['window_seconds']) + 's'
                        values[field] = window[name]; clocks[field] = window['measured_at']
                context = {name: observed[name] for name in ('table', 'snapshot_id', 'snapshot_measurement_id', 'file_inventory_measurement_id')}
                context['metadata_semantics'] = 'observed_cached_metadata_for_explicit_query_snapshot_not_fresh_inventory_RPC'
                receipt = self.log.journal.publish(measurement_id=measurement_id, feature_values=values,
                                                   feature_capture_at=clocks, source_context=context)
                self.log.publications[measurement_id] = receipt
                self.log.emit('three_model_feature_publication', measurement_id=measurement_id, publication=receipt)
                return True

            result = super().execute(cursor, sql, role=role, query_id=query_id, measurement_id=measurement_id,
                                     prepare_submission=prepare_bound, latest_start_ns=latest_start_ns)
            if result is not None and result.get('submitted') is not False:
                receipt = self.log.publications[measurement_id]
                validate_publication(receipt)
                clock_order(receipt['receipt_persisted_observed_at'], result['client_execute_start'], result['fetch_end'])
                require(all(result['client_execute_start']['monotonic_ns'] - p['monotonic_ns'] <=
                            cfg['three_model_capture']['max_feature_age_ns'] for p in receipt['feature_capture_at'].values()),
                        'Actual query began with expired captured feature; preserve failed physical evidence')
                self.log.emit('three_model_query_binding', measurement_id=measurement_id, publication=receipt,
                              client_execute_start=result['client_execute_start'], fetch_end=result['fetch_end'])
            return result
    return BoundLog, BoundRecorder


def audit_publications(directory):
    directory = Path(directory)
    events = [json.loads(line) for line in (directory / 'events.jsonl').open()]
    pending = set(); queue = {}; version = 0; captures = {}; persisted = {}
    for line in (directory / 'feature_publication.jsonl').open():
        event = json.loads(line); kind = event['kind']
        if kind == 'client_maintenance_requested':
            require(event['measurement_id'] not in pending, 'Duplicate journal pending request')
            pending.add(event['measurement_id']); version += 1
        elif kind == 'client_maintenance_returned':
            require(event['measurement_id'] in pending, 'Unknown journal pending return')
            pending.remove(event['measurement_id']); version += 1
        elif kind == 'client_queue_transition':
            queue[event['source_query_id']] = event['state']; version += 1
        elif kind == 'feature_capture':
            receipt = event['receipt']; mid = receipt['measurement_id']
            require(mid not in captures and receipt['state_version'] == version, 'Duplicate/versioned feature mismatch')
            require(receipt['pending_measurement_ids'] == sorted(pending) and receipt['client_pending'] == bool(pending), 'Direct pending state mismatch')
            require(receipt['queue_depth'] == sum(s == 'queued' for s in queue.values()), 'Direct queue state mismatch')
            captures[mid] = receipt
        elif kind == 'feature_publication_observed':
            receipt = event['receipt']; mid = receipt['measurement_id']
            require(mid in captures and mid not in persisted, 'Publication without unique capture')
            require({k: v for k, v in receipt.items() if k != 'feature_persisted_observed_at'} == captures[mid], 'Captured feature changed')
            persisted[mid] = receipt
    require(not pending, 'Client maintenance remained pending at terminal audit')
    bindings = [e for e in events if e['kind'] == 'three_model_query_binding']
    completed = {e['measurement_id']: e for e in events if e['kind'] == 'statement_completed' and e['role'] == 'trace_query'}
    require(len(bindings) == len(completed) > 0, 'Missing/duplicate actual query binding')
    seen = set(); counts = {'client_pending': 0, 'client_not_pending': 0}
    for event in bindings:
        mid = event['measurement_id']; receipt = event['publication']; validate_publication(receipt)
        require(mid not in seen and mid in completed and mid in persisted, 'Unknown/duplicate query binding')
        seen.add(mid)
        require({k: v for k, v in receipt.items() if k != 'receipt_persisted_observed_at'} == persisted[mid], 'Persisted publication differs')
        result = completed[mid]
        require(event['client_execute_start'] == result['client_execute_start'] and event['fetch_end'] == result['fetch_end'], 'Call binding differs')
        clock_order(receipt['receipt_persisted_observed_at'], result['client_execute_start'], result['fetch_end'])
        counts['client_pending' if receipt['client_pending'] else 'client_not_pending'] += 1
    return {'status': 'verified_live_publication_and_direct_client_state_only', 'completed_queries': len(bindings),
            'published_features': len(captures), 'observed_conditions': counts, 'runtime_adapter_accepted': False,
            'limitations': ['One development engineering experiment; not independent model validation.',
                           'Cached layout is pinned to explicit SQL snapshot, not proof of current latest layout.',
                           'Client pending is not Spark activity or causal compaction harm. No model fitted.']}
