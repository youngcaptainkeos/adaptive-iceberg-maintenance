"""Append-only physical evidence primitives; no workload or policy generation."""
import json
import math
import os
from pathlib import Path
import threading
import time
from datetime import datetime, timezone
import urllib.request
import uuid

from experiment_validation import ValidationError, require


def stamp():
    return {'utc': datetime.now(timezone.utc).isoformat(), 'monotonic_ns': time.monotonic_ns()}


class EventLog:
    """Exclusive new log; persist each record before returning to its caller."""
    def __init__(self, path, experiment_id):
        require(bool(experiment_id), 'Experiment ID required')
        self.experiment_id = experiment_id
        self.lock = threading.Lock()
        self.stream = Path(path).open('x', encoding='utf-8')

    def emit(self, kind, **fields):
        record = dict(fields, schema_version='physical_event_v1',
                      experiment_id=self.experiment_id, kind=kind, recorded=stamp())
        encoded = json.dumps(record, allow_nan=False, default=str)
        with self.lock:
            self.stream.write(encoded + '\n')
            self.stream.flush()
            os.fsync(self.stream.fileno())
        return record

    def close(self):
        with self.lock:
            self.stream.close()


class StatementRecorder:
    """Request lifetime is not Spark execution time; retain the distinction."""
    def __init__(self, log):
        self.log = log

    def execute(self, cursor, sql, *, role, query_id=None):
        measurement_id = uuid.uuid4().hex
        marker = 'capstone_event_' + measurement_id
        request_start = stamp()
        self.log.emit('statement_requested', measurement_id=measurement_id,
                      marker=marker, role=role, query_id=query_id, sql=sql,
                      request_start=request_start, timing_contract='client_submission_v1')
        # Durable intent logging precedes the RPC. Exclude its I/O from the
        # measured client service interval, while retaining total request lifetime.
        execute_start = stamp()
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


class SparkEvidence:
    """Capture raw REST responses. Matching markers is evidence, not overlap proof."""
    def __init__(self, base_url, app_id, timeout_seconds, log):
        require(base_url.startswith('http://127.0.0.1:') or base_url.startswith('https://'),
                'Use local REST or HTTPS')
        require('/' not in app_id and bool(app_id), 'Invalid app ID')
        require(math.isfinite(timeout_seconds) and timeout_seconds > 0, 'Positive REST timeout required')
        self.url = base_url.rstrip('/') + '/api/v1/applications/' + app_id
        self.timeout = timeout_seconds
        self.log = log

    def capture(self, resource):
        require(resource in ('jobs', 'stages', 'environment'), 'Unsupported REST resource')
        return self._capture(resource)

    def capture_tasks(self, stage_id, attempt_id, task_count):
        require(all(isinstance(v, int) and not isinstance(v, bool) and v >= 0
                    for v in (stage_id, attempt_id, task_count)) and task_count > 0,
                'Declare valid stage attempt and positive task count')
        payload = self._capture(f'stages/{stage_id}/{attempt_id}/taskList?length={task_count}')
        require(isinstance(payload, list) and len(payload) == task_count,
                'Incomplete task-attempt REST evidence')
        return payload

    def _capture(self, resource):
        started = stamp()
        try:
            with urllib.request.urlopen(self.url + '/' + resource, timeout=self.timeout) as response:
                payload = json.load(response)
            self.log.emit('spark_rest', resource=resource, request_start=started,
                          response_end=stamp(), payload=payload)
            return payload
        except Exception as exc:
            self.log.emit('spark_rest_failed', resource=resource, request_start=started,
                          error_type=type(exc).__name__, error=str(exc))
            raise


class TelemetrySampler:
    """Independent counter samples with actual monotonic intervals and gap evidence."""
    def __init__(self, log, interval_seconds):
        require(math.isfinite(interval_seconds) and interval_seconds > 0,
                'Positive telemetry interval required')
        self.log = log
        self.interval = interval_seconds
        self.stop_event = threading.Event()
        self.failure = None
        self.samples = []
        self.lock = threading.Lock()

    def start(self):
        require(not hasattr(self, 'thread'), 'Sampler already started')
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _read(self):
        import psutil
        timestamp = stamp()
        cpu = psutil.cpu_times()
        # Linux guest times are already contained in user/nice; avoid double counting.
        total = sum(value for name, value in cpu._asdict().items() if name not in ('guest', 'guest_nice'))
        idle = cpu.idle + getattr(cpu, 'iowait', 0)
        io = psutil.disk_io_counters()
        memory = psutil.virtual_memory()
        require(io is not None, 'Disk I/O counters unavailable')
        return dict(timestamp=timestamp, cpu_total_s=total, cpu_idle_s=idle,
                    read_bytes=io.read_bytes, write_bytes=io.write_bytes,
                    available_memory_bytes=memory.available, total_memory_bytes=memory.total)

    def _run(self):
        try:
            previous = self._read()
            self.log.emit('telemetry_origin', counters=previous)
            deadline = time.monotonic() + self.interval
            while not self.stop_event.wait(max(0, deadline - time.monotonic())):
                current = self._read()
                elapsed = (current['timestamp']['monotonic_ns'] - previous['timestamp']['monotonic_ns']) / 1e9
                total = current['cpu_total_s'] - previous['cpu_total_s']
                idle = current['cpu_idle_s'] - previous['cpu_idle_s']
                read = current['read_bytes'] - previous['read_bytes']
                write = current['write_bytes'] - previous['write_bytes']
                require(elapsed > 0 and total > 0 and 0 <= idle <= total and read >= 0 and write >= 0,
                        'Counter reset or invalid telemetry interval')
                sample = dict(start=previous['timestamp'], end=current['timestamp'],
                              elapsed_seconds=elapsed, cpu_busy_fraction=(total-idle)/total,
                              read_bytes_per_second=read/elapsed, write_bytes_per_second=write/elapsed,
                              available_memory_bytes=current['available_memory_bytes'],
                              total_memory_bytes=current['total_memory_bytes'], counters=current)
                self.log.emit('telemetry_interval', **sample)
                with self.lock:
                    self.samples.append(sample)
                previous = current
                deadline += self.interval
                # Do not emit catch-up pseudo-samples after scheduler delay.
                if deadline <= time.monotonic():
                    deadline = time.monotonic() + self.interval
        except Exception as exc:
            self.failure = exc
            self.log.emit('telemetry_failed', error_type=type(exc).__name__, error=str(exc))

    def window(self, *, seconds, max_interval_seconds, max_age_seconds):
        require(all(math.isfinite(x) and x > 0 for x in (seconds, max_interval_seconds, max_age_seconds)),
                'Declare positive window, interval and age limits')
        if self.failure:
            raise ValidationError(f'Telemetry failed: {self.failure}')
        now = time.monotonic_ns()
        cutoff = now - int(seconds * 1e9)
        with self.lock:
            samples = [s for s in self.samples if cutoff < s['end']['monotonic_ns'] <= now]
        require(bool(samples), 'Telemetry warmup: no completed intervals')
        require(samples[0]['start']['monotonic_ns'] <= cutoff, 'Telemetry warmup: incomplete window')
        age = (now - samples[-1]['end']['monotonic_ns']) / 1e9
        require(0 <= age <= max_age_seconds, 'Stale or future telemetry')
        require(all(s['elapsed_seconds'] <= max_interval_seconds for s in samples), 'Telemetry sampling gap')
        weights = [max(0, (min(now, s['end']['monotonic_ns']) - max(cutoff, s['start']['monotonic_ns'])) / 1e9)
                   for s in samples]
        covered = sum(weights)
        require(covered > 0, 'No covered telemetry time')
        return dict(window_contract='completed_counter_window_v1',
                    window_start_monotonic_ns=cutoff, window_end_monotonic_ns=now,
                    feature_timestamp=samples[-1]['end']['utc'], measured_at=stamp(),
                    window_seconds=seconds, covered_seconds=covered, freshness_seconds=age,
                    cpu_busy_fraction=sum(w*s['cpu_busy_fraction'] for w,s in zip(weights,samples))/covered,
                    read_bytes_per_second=sum(w*s['read_bytes_per_second'] for w,s in zip(weights,samples))/covered,
                    write_bytes_per_second=sum(w*s['write_bytes_per_second'] for w,s in zip(weights,samples))/covered,
                    memory_used_fraction=sum(w*(s['total_memory_bytes']-s['available_memory_bytes'])/s['total_memory_bytes']
                                             for w,s in zip(weights,samples))/covered)

    def stop(self):
        # Stops only our observer thread, never a database operation/service.
        self.stop_event.set()
        if hasattr(self, 'thread'):
            self.thread.join()
        if self.failure:
            raise ValidationError(f'Telemetry failed: {self.failure}')
