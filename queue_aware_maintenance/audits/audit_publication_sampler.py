#!/usr/bin/env python3
"""Independent raw-counter/window reconstruction for real publication validation."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,json
from pathlib import Path
from queue_aware_maintenance.core.common import checked,require,write_json,sha,now
from telemetry_binding import verify_window

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False);report={'status':'running','started_utc':now(),'new_SQL_executed':False,'physical_controller_validated':False}
 try:
  result_path=checked(cfg['validation_result']);result=json.loads(result_path.read_text());require(result['status']=='passed_real_durable_publication_and_original_window_gates','Real observer validation not passed');events_path=result_path.parent/'events.jsonl';require(sha(events_path)==result['events_sha256'],'Raw observer evidence changed');rows=[json.loads(x) for x in events_path.open()];registrations=[r for r in rows if r['kind']=='publication_validation_protocol'];require(len(registrations)==1,'Missing observer registration');registration=registrations[0]['configuration'];require(registrations[0]['sampler_sha256']==result['sampler_sha256'],'Observer source receipt mismatch');intervals={r['end']['monotonic_ns']:r for r in rows if r['kind']=='telemetry_interval'};observations=[r for r in rows if r['kind']=='publication_validation_observation'];require(len(observations)==result['observed_publications']>=registration['minimum_observed_publications'],'Publication population mismatch');previous=-1;checks=[]
  for obs in observations:
   sample_end=obs['sample_end_monotonic_ns'];require(sample_end in intervals and sample_end>previous,'Missing/reused observed publication');previous=sample_end;sample=intervals[sample_end]
   require(sample['recorded']['monotonic_ns']<=obs['ended']['monotonic_ns']<=obs['recorded']['monotonic_ns'],'Publication observation before raw sample event')
   age=(obs['ended']['monotonic_ns']-sample_end)/1e9;require(age==obs['publication_observed_age_seconds'] and 0<=age<=registration['telemetry']['max_age_seconds'],'Observed age differs')
   require([w['window_seconds'] for w in obs['windows']]==registration['telemetry']['window_seconds'],'Changed registered window population')
   for window in obs['windows']:
    require(window['measured_at']['monotonic_ns']<=obs['recorded']['monotonic_ns'],'Window computed after observation');checks.append(verify_window(rows,window,max_interval_seconds=registration['telemetry']['max_interval_seconds'],max_age_seconds=registration['telemetry']['max_age_seconds'],minimum_coverage_fraction=registration['telemetry']['minimum_coverage_fraction']))
  require(result['sampler_sha256']==sha(source_file('publication_sampler.py')),'Sampler source changed since actual validation')
  report.update(status='passed_independent_real_publication_window_reconstruction',validation_sha256=sha(result_path),events_sha256=sha(events_path),sampler_sha256=result['sampler_sha256'],observations=len(observations),windows_reconstructed=len(checks),telemetry=registration['telemetry'],submission_max_age_seconds=registration['submission_max_age_seconds'],maximum_observed_publication_age_seconds=max(o['publication_observed_age_seconds'] for o in observations),limitations=['Observer/window correctness only, no SQL/controller performance validation.','Durable-before-publication ordering is established by verified observer source plus actual recorded chronology, not an external disk crash-recovery test.'])
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:report.update(ended_utc=now(),protocol_sha256=sha(protocol),code_sha256=sha(__file__));write_json(out/'result.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
