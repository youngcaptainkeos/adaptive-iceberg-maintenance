"""Describe actual failed-episode sampling gaps; never repair or accept evidence."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run(episode, output):
    output.mkdir(parents=True, exist_ok=False)
    paths = [episode / n for n in ('config.json', 'failure.json', 'events.jsonl')]
    before = {str(p): sha(p) for p in paths}
    cfg, failure = (json.loads(p.read_text()) for p in paths[:2])
    limit = cfg['telemetry']['max_interval_seconds']
    events = [json.loads(line) for line in paths[2].read_text().splitlines()]
    samples = [e for e in events if e['kind'] == 'telemetry_interval']
    checkpoints = [e for e in events if e['kind'] == 'terminal_engine_archive_checkpoint']
    gaps = []
    for sample in samples:
        if sample['elapsed_seconds'] <= limit:
            continue
        lo, hi = sample['start']['monotonic_ns'], sample['end']['monotonic_ns']
        overlap = [c['checkpoint_number'] for c in checkpoints
                   if c['capture_started']['monotonic_ns'] < hi
                   and c['capture_ended']['monotonic_ns'] > lo]
        gaps.append(dict(start=sample['start'], end=sample['end'],
                         elapsed_seconds=sample['elapsed_seconds'],
                         overlapping_archive_checkpoints=overlap))
    completed = Counter(e['role'] for e in events if e['kind'] == 'statement_completed')
    after = {str(p): sha(p) for p in paths}
    if before != after:
        raise ValueError('Evidence changed during diagnostic')
    result = dict(status='completed_failed_evidence_diagnostic_only',
                  recorded_utc=datetime.now(timezone.utc).isoformat(),
                  episode_directory=str(episode), input_sha256=before,
                  failure=failure, registered_max_interval_seconds=limit,
                  telemetry_interval_count=len(samples),
                  maximum_interval_seconds=max(s['elapsed_seconds'] for s in samples),
                  gaps=gaps, completed_calls_by_role=dict(completed),
                  periodic_checkpoint_count=sum(not c['terminal'] for c in checkpoints),
                  terminal_checkpoint_count=sum(c['terminal'] for c in checkpoints),
                  checkpoint_wall_ns=[c['observer_wall_ns'] for c in checkpoints],
                  event_counts=dict(Counter(e['kind'] for e in events)),
                  limitations=['Temporal overlap is not causal attribution.',
                               'No missing samples imputed; failed evidence remains failed.',
                               'No physical retry, model fitting or acceptance performed.'])
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.episode.resolve(), args.output.resolve())
