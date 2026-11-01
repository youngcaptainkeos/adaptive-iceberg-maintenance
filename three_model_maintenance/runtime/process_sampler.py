"""Durable parent publication of an independent real acquisition subprocess."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading

from experiment_validation import require, ValidationError
from physical_measurements import stamp
from three_model_maintenance.runtime.counter_process import CONTRACT, boot_id, encode
from three_model_maintenance.runtime.notifying_sampler import NotifyingTelemetrySampler


def validate_acquisition(cfg):
    contract = cfg.get('telemetry_acquisition_contract')
    require(contract in (None, CONTRACT), 'Unknown telemetry acquisition contract')
    if contract is not None:
        require(cfg.get('telemetry_persistence_contract') == 'independent_counter_sampling_durable_publish_v1'
                and cfg.get('telemetry_availability_contract') == 'wait_for_real_durable_sample_v1',
                'Independent acquisition requires original durable availability contracts')
        require(cfg.get('telemetry_lifecycle_contract') == 'workload_and_terminal_archive_then_cooperative_finish_v1'
                and cfg.get('terminal_engine_archive_contract') == 'completed_calls_before_final_validation_v1',
                'Register counter acquisition through workload/terminal archive before validation-only SQL')
    return contract is not None


class ProcessTelemetrySampler(NotifyingTelemetrySampler):
    def __init__(self, log, interval_seconds, *, journal, until):
        super().__init__(log, interval_seconds, asynchronous_persistence=False)
        self.journal, self.until = Path(journal), until
        self.stop_requested = False
        self.control_lock = threading.Lock()
        self.stopped = False

    def start(self):
        require(not hasattr(self, 'thread'), 'Sampler already started')
        self.stderr = self.journal.with_suffix('.stderr.log').open('xb')
        command = [sys.executable, '-B', '-u', '-m',
                   'three_model_maintenance.runtime.counter_process', '--journal', str(self.journal),
                   '--interval', str(self.interval), '--until', self.until]
        self.child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=self.stderr, text=True, start_new_session=True)
        try:
            self.log.emit('telemetry_acquisition_started', contract=CONTRACT, child_pid=self.child.pid,
                          boot_id=boot_id(), journal_path=str(self.journal), command=command,
                          interval_seconds=self.interval, until_utc=self.until)
        except Exception:
            self._request_stop()
            for _ in self.child.stdout:
                pass
            self.child.wait(); self.stderr.close()
            raise
        self.thread = threading.Thread(target=self._receive, daemon=True)
        self.thread.start()

    def _failure(self, exc):
        with self.available:
            if self.failure is None:
                self.failure = exc
            self.available.notify_all()

    def _request_stop(self):
        with self.control_lock:
            if self.stop_requested:
                return
            self.stop_requested = True
            try:
                self.child.stdin.write('stop\n'); self.child.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                self._failure(exc)

    def _receive(self):
        sequence, previous_hash, offset, terminal = 0, '', 0, False
        try:
            # Continue draining even if publication fails, so cooperative child
            # completion cannot deadlock on a full stdout pipe.
            for line in self.child.stdout:
                if self.failure is not None:
                    continue
                try:
                    received = stamp(); envelope = json.loads(line); frame = envelope['frame']
                    raw = (encode(frame)+'\n').encode()
                    chain = hashlib.sha256(previous_hash.encode()+raw).hexdigest()
                    require(not terminal and frame['sequence'] == sequence and frame['contract'] == CONTRACT
                            and frame['boot_id'] == boot_id() and frame['child_pid'] == self.child.pid
                            and envelope['previous_chain_sha256'] == previous_hash
                            and envelope['chain_sha256'] == chain
                            and envelope['raw_sha256'] == hashlib.sha256(raw).hexdigest()
                            and envelope['end_offset'] == offset+len(raw), 'Invalid acquisition handoff')
                    require(frame['recorded']['monotonic_ns'] <= envelope['child_durable_after']['monotonic_ns']
                            <= received['monotonic_ns'], 'Invalid cross-process acquisition clocks')
                    kind, fields = frame['kind'], frame['fields']
                    require(kind in ('telemetry_origin', 'telemetry_interval',
                                     'telemetry_acquisition_terminal'), 'Acquisition child reported failure')
                    require((sequence == 0) == (kind == 'telemetry_origin'), 'Invalid acquisition origin')
                    if kind == 'telemetry_acquisition_terminal':
                        require(self.stop_requested and fields['reason'] == 'cooperative_stop',
                                'Unrequested acquisition completion')
                        terminal = True
                    self.log.emit(kind, **fields, acquisition_source=dict(envelope=envelope, received=received))
                    self.log.emit('telemetry_acquisition_publication', sequence=sequence,
                                  parent_durable_after=stamp(), child_kind=kind)
                    if kind == 'telemetry_interval':
                        self._published_interval(fields)
                    sequence += 1; previous_hash = chain; offset += len(raw)
                except Exception as exc:
                    self._failure(exc); self._request_stop()
            rc = self.child.wait()
            require(self.failure is None and rc == 0 and terminal, 'Incomplete/failed acquisition child')
            raw = self.journal.read_bytes()
            require(len(raw) == offset, 'Acquisition journal length differs')
            self.log.emit('telemetry_acquisition_finished', contract=CONTRACT, child_pid=self.child.pid,
                          returncode=rc, frame_count=sequence, chain_sha256=previous_hash,
                          journal_sha256=hashlib.sha256(raw).hexdigest(), journal_bytes=len(raw))
        except Exception as exc:
            self._failure(exc)
        finally:
            # A lifecycle failure still requests natural observer completion.
            if self.child.poll() is None:
                self._request_stop()
                for _ in self.child.stdout:
                    pass
                self.child.wait()
            self.stderr.close()
            self.child.stdin.close(); self.child.stdout.close()

    def stop(self):
        if hasattr(self, 'thread') and not self.stopped:
            self._request_stop(); self.thread.join(); self.stopped = True
        if self.failure:
            raise ValidationError('Telemetry acquisition failed: '+str(self.failure))
