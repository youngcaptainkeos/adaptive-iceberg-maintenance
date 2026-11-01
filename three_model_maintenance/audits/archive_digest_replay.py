"""Verify a prospective hash repair against immutable real failed-run checkpoints.

No SQL or acceptance of the source episode. Timings are saved-evidence replay
costs, not proof that physical telemetry deadlines will pass.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/phase6-live-evaluation'))
from three_model_maintenance.runtime.terminal_archive import IncrementalFrameDigest
from three_model_maintenance.audits.telemetry_gap_diagnostic import sha


def run(events, output):
    output.mkdir(parents=True, exist_ok=False)
    original_sha = sha(events)
    digest = IncrementalFrameDigest()
    frames, checks = [], []
    with events.open() as stream:
        for line in stream:
            event = json.loads(line)
            if event['kind'] == 'spark_rest':
                frames.append(event)
                digest.append(event)
            elif event['kind'] == 'terminal_engine_archive_checkpoint':
                started = time.perf_counter_ns()
                legacy = hashlib.sha256(json.dumps(frames, sort_keys=True,
                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()
                legacy_ns = time.perf_counter_ns() - started
                if not (digest.count == event['source_rest_event_count']
                        and digest.hexdigest() == legacy == event['source_rest_events_sha256']):
                    raise ValueError('Saved checkpoint canonical digest differs')
                checks.append(dict(checkpoint=event['checkpoint_number'],
                    frames=digest.count, sha256=legacy,
                    legacy_full_prefix_wall_ns=legacy_ns,
                    incremental_encoding_wall_ns_cumulative=digest.encode_wall_ns))
    if not checks or original_sha != sha(events):
        raise ValueError('No real checkpoints or raw changed')
    result = dict(status='passed_actual_saved_checkpoint_digest_equivalence_only',
        events_path=str(events), events_sha256=original_sha,
        source_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        module_sha256=sha(REPO / 'three_model_maintenance/runtime/terminal_archive.py'),
        checkpoint_checks=checks, observed_rest_frame_count=len(frames),
        source_episode_still_failed=True, physical_deadline_pass_claimed=False,
        limitation='Replay timing cannot establish GIL causality or live sampling reliability.')
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run(args.events.resolve(), args.output.resolve())
