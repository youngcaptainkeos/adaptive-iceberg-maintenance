"""Real host sampling during retained archive processing; no SQL or dummy labels."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'scripts/phase6-live-evaluation'))
from physical_measurements import EventLog
from three_model_maintenance.runtime.process_sampler import ProcessTelemetrySampler
from three_model_maintenance.audits.archive_digest_replay import run as replay
from three_model_maintenance.audits.counter_acquisition import audit, require
from three_model_maintenance.audits.telemetry_gap_diagnostic import sha


def run(protocol):
    cfg = json.loads(protocol.read_text())
    require(subprocess.check_output(['git', 'show', 'HEAD:'+str(protocol.relative_to(REPO))], cwd=REPO)
            == protocol.read_bytes(), 'Validation registration must be committed unchanged')
    pinned = {spec['path'] for spec in cfg['inputs']}
    require(cfg['original_episode_config'] in pinned and cfg['failed_episode_events'] in pinned,
            'Original episode config and actual failed events must be SHA-pinned inputs')
    require(datetime.now(timezone.utc) < datetime.fromisoformat(cfg['no_new_work_after_utc']), 'Validation cutoff')
    for spec in cfg['inputs']:
        require(sha(Path(spec['path'])) == spec['sha256'], 'Changed real validation input')
    for spec in cfg['code_files']:
        require(sha(REPO/spec['path']) == spec['sha256'], 'Changed validation source')
    out = Path(cfg['output_directory']); out.mkdir(parents=True, exist_ok=False)
    (out/'registration.json').write_bytes(protocol.read_bytes())
    original = json.loads(Path(cfg['original_episode_config']).read_text()); telemetry = original['telemetry']
    log = EventLog(out/'events.jsonl', cfg['label'])
    sampler = ProcessTelemetrySampler(log, telemetry['interval_seconds'],
        journal=out/'telemetry_acquisition.jsonl', until=cfg['acquisition_deadline_utc'])
    try:
        started = time.monotonic(); sampler.start()
        # Exactly one full pass over genuine recorded checkpoints, not generated
        # demand or fabricated queries. The parent exercises actual JSON paths.
        replay(Path(cfg['failed_episode_events']), out/'saved_checkpoint_replay')
        time.sleep(max(0, started+telemetry['warmup_seconds']-time.monotonic()))
        windows = [sampler.window(seconds=w, max_interval_seconds=telemetry['max_interval_seconds'],
                                  max_age_seconds=telemetry['max_age_seconds']) for w in telemetry['window_seconds']]
        for window in windows:
            require(window['covered_seconds']/window['window_seconds'] >= telemetry['minimum_coverage_fraction'],
                    'Insufficient real counter coverage')
        log.emit('process_sampling_validation_windows', windows=windows)
        sampler.stop()
        proof = audit(out, telemetry, validation_windows=True)
        for spec in cfg['inputs']:
            require(sha(Path(spec['path'])) == spec['sha256'], 'Changed input after validation')
        result = dict(status='passed_real_counter_acquisition_with_saved_archive_processing_only',
            counter_audit=proof, windows=windows, protocol_sha256=sha(protocol),
            code_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
            physical_episode_accepted=False, SQL_executed=False, models_fitted=False,
            limitations=['OS scheduling, pipe backpressure and disk stalls remain real acquisition risks.',
                         'This engineering check is not an SF10 workload or terminal archive pass.'])
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
    except Exception as exc:
        (out/'failure.json').write_text(json.dumps(dict(error_type=type(exc).__name__, error=str(exc)), indent=2)+'\n')
        raise
    finally:
        try:
            sampler.stop()
        finally:
            log.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    args = parser.parse_args()
    run(args.protocol.resolve())
