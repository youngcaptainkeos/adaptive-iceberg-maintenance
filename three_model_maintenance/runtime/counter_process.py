"""Real host counter acquisition isolated from the collector's Python GIL.

The acquisition journal precedes pipe delivery. Cooperative control or a finite
registered UTC deadline ends the child naturally; nothing is terminated/killed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import select
import sys
import time
import psutil

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/phase6-live-evaluation'))
from physical_measurements import TelemetrySampler, stamp

CONTRACT = 'subprocess_counter_journal_v1'


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def run(journal, interval, until):
    deadline = datetime.fromisoformat(until)
    if not (deadline.tzinfo and datetime.now(timezone.utc) < deadline
            and math.isfinite(interval) and interval > 0):
        raise ValueError('Register finite future aware deadline and positive cadence')
    sampler = TelemetrySampler(None, interval)
    previous_hash, sequence = '', 0
    with journal.open('xb') as stream:
        def publish(kind, fields, read_started=None, read_ended=None):
            nonlocal previous_hash, sequence
            frame = dict(contract=CONTRACT, sequence=sequence, kind=kind, fields=fields,
                         child_pid=os.getpid(), boot_id=boot_id(), recorded=stamp(),
                         read_started=read_started, read_ended=read_ended)
            raw = (encode(frame) + '\n').encode()
            chain = hashlib.sha256(previous_hash.encode() + raw).hexdigest()
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            envelope = dict(frame=frame, raw_sha256=hashlib.sha256(raw).hexdigest(),
                            chain_sha256=chain, previous_chain_sha256=previous_hash,
                            end_offset=stream.tell(), child_durable_after=stamp())
            print(encode(envelope), flush=True)
            sequence += 1; previous_hash = chain

        try:
            read_start = stamp(); previous = sampler._read(); read_end = stamp()
            publish('telemetry_origin', dict(counters=previous,
                acquisition_environment=dict(python=sys.version, psutil_version=psutil.__version__)), read_start, read_end)
            tick = time.monotonic() + interval
            while True:
                remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
                if remaining <= 0:
                    raise ValueError('Registered acquisition deadline reached before cooperative completion')
                ready, _, _ = select.select([sys.stdin], [], [], min(remaining, max(0, tick-time.monotonic())))
                if ready:
                    command = sys.stdin.readline()
                    if command != 'stop\n':
                        raise ValueError('Parent EOF or unknown acquisition control')
                    usage = resource.getrusage(resource.RUSAGE_SELF)
                    publish('telemetry_acquisition_terminal', dict(reason='cooperative_stop',
                        cpu_user_seconds=usage.ru_utime, cpu_system_seconds=usage.ru_stime,
                        cpu_scope='getrusage snapshot before terminal serialization/fsync and process exit'))
                    return
                if time.monotonic() < tick:
                    continue
                read_start = stamp(); current = sampler._read(); read_end = stamp()
                elapsed = (current['timestamp']['monotonic_ns']-previous['timestamp']['monotonic_ns'])/1e9
                total = current['cpu_total_s']-previous['cpu_total_s']
                idle = current['cpu_idle_s']-previous['cpu_idle_s']
                read = current['read_bytes']-previous['read_bytes']
                write = current['write_bytes']-previous['write_bytes']
                if not (elapsed > 0 and total > 0 and 0 <= idle <= total and read >= 0 and write >= 0):
                    raise ValueError('Counter reset or invalid acquisition interval')
                sample = dict(start=previous['timestamp'], end=current['timestamp'], elapsed_seconds=elapsed,
                    cpu_busy_fraction=(total-idle)/total, read_bytes_per_second=read/elapsed,
                    write_bytes_per_second=write/elapsed, available_memory_bytes=current['available_memory_bytes'],
                    total_memory_bytes=current['total_memory_bytes'], counters=current)
                publish('telemetry_interval', sample, read_start, read_end)
                previous = current; tick += interval
                if tick <= time.monotonic():
                    tick = time.monotonic() + interval
        except Exception as exc:
            publish('telemetry_acquisition_error', dict(error_type=type(exc).__name__, error=str(exc)))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--interval', type=float, required=True)
    parser.add_argument('--until', required=True)
    args = parser.parse_args()
    run(args.journal.resolve(), args.interval, args.until)
