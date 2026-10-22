"""Wake on actual durable publication, avoiding sampling-cadence polling alias.

Counter acquisition/window arithmetic stay in the original sampler. No synthetic
sample, time repair, freshness relaxation or interval omission.
"""
import threading
import time
from physical_measurements import TelemetrySampler as PhysicalSampler, stamp
from experiment_validation import ValidationError


class NotifyingTelemetrySampler(PhysicalSampler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.available = threading.Condition(self.lock)

    def _published_interval(self, fields):
        # Called only after EventLog.emit has flushed/fsynced the actual interval.
        with self.available:
            self.samples.append(fields)
            self.available.notify_all()

    def _publish(self, kind, fields):
        if self.asynchronous_persistence:
            self.persistence_queue.put((kind, fields))
        else:
            self.log.emit(kind, **fields)
            if kind == 'telemetry_interval':self._published_interval(fields)

    def _persist(self):
        try:
            while True:
                item = self.persistence_queue.get()
                if item is None:return
                kind, fields = item
                self.log.emit(kind, **fields)
                if kind == 'telemetry_interval':self._published_interval(fields)
        except Exception as exc:
            with self.available:
                self.failure = exc
                self.available.notify_all()
            self.log.emit('telemetry_failed', error_type=type(exc).__name__, error=str(exc))

    def wait_for_available_sample(self, *, deadline_ns, max_age_seconds, measurement_id):
        started = stamp(); waited = False; initial_end = None; last = None
        while True:
            with self.available:
                if self.failure:raise ValidationError('Telemetry failed: ' + str(self.failure))
                last = self.samples[-1]['end']['monotonic_ns'] if self.samples else None
                if initial_end is None:initial_end = last
                now = time.monotonic_ns()
                if now >= deadline_ns:
                    outcome = 'horizon_reached_request_retained_queued'; break
                if last is not None and 0 <= (now - last) / 1e9 <= max_age_seconds:
                    outcome = 'actual_fresh_durable_sample_available'; break
                waited = True
                # Releases sampler lock while waiting. A real persisted interval
                # notifies immediately; no once-per-sampling-period phase polling.
                self.available.wait(timeout=(deadline_ns - now) / 1e9)
        # Never acquire the journal/log lock while holding the sampler lock.
        if waited or outcome != 'actual_fresh_durable_sample_available':
            self.log.emit('query_telemetry_availability_wait', measurement_id=measurement_id,
                          started=started, ended=stamp(), initial_available_sample_end_ns=initial_end,
                          actual_available_sample_end_ns=last, deadline_monotonic_ns=deadline_ns,
                          outcome=outcome, wait_contract='condition_notify_after_durable_sample_publish_v1')
        return outcome == 'actual_fresh_durable_sample_available'
