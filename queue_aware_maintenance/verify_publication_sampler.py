#!/usr/bin/env python3
"""Real host counters/durable samples only; no fake clock or telemetry fixture."""
import argparse,json,time,uuid,subprocess
from pathlib import Path
from common import require,write_json,sha,now,utc
from physical_measurements import EventLog,stamp
from publication_sampler import PublicationTelemetrySampler
from datetime import datetime,timezone

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());require(datetime.now(timezone.utc)<utc(cfg['no_new_operation_after_utc']),'Validation cutoff passed');out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False);log=EventLog(out/'events.jsonl',cfg['experiment_id']);sampler=PublicationTelemetrySampler(log,cfg['telemetry']['interval_seconds'],asynchronous_persistence=True);report={'status':'running','started_utc':now(),'new_SQL_executed':False,'physical_controller_validation_passed':False};sampler.start()
 try:
  log.emit('publication_validation_protocol',configuration=cfg,revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=sha(__file__),sampler_sha256=sha(Path(__file__).parent/'publication_sampler.py'))
  time.sleep(cfg['telemetry']['warmup_seconds']);deadline=time.monotonic_ns()+int(cfg['observation_seconds']*1e9);samples=[]
  while time.monotonic_ns()<deadline:
   last=sampler.available_sample_end_ns();require(last is not None,'No actual durable sample after warmup');began=stamp();sample=sampler.wait_for_publication_after(sample_end_ns=last,deadline_ns=deadline)
   if sample is None:break
   ended=stamp();age=(ended['monotonic_ns']-sample['end']['monotonic_ns'])/1e9
   require(0<=age<=cfg['telemetry']['max_age_seconds'],'Next published sample stale')
   require(sampler.wait_for_available_sample(deadline_ns=deadline,max_age_seconds=cfg['submission_max_age_seconds'],measurement_id=uuid.uuid4().hex),'No fresh actual sample after publication')
   windows=[sampler.window(seconds=w,max_interval_seconds=cfg['telemetry']['max_interval_seconds'],max_age_seconds=cfg['telemetry']['max_age_seconds']) for w in cfg['telemetry']['window_seconds']]
   require(all(w['covered_seconds']/w['window_seconds']>=cfg['telemetry']['minimum_coverage_fraction'] for w in windows),'Coverage gate failed')
   samples.append({'started':began,'ended':ended,'sample_end_monotonic_ns':sample['end']['monotonic_ns'],'publication_observed_age_seconds':age,'windows':windows});log.emit('publication_validation_observation',**samples[-1])
  require(len(samples)>=cfg['minimum_observed_publications'],'Insufficient real publication evidence');report.update(status='passed_real_durable_publication_and_original_window_gates',observed_publications=len(samples),max_observed_publication_age_seconds=max(s['publication_observed_age_seconds'] for s in samples),checks=['Real host counters, actual time and durable event log; no fake fixtures','Condition waits unblock on strictly newer persisted samples','Original60/300s windows,95percent coverage and2s age/gap gates preserved','Submission freshness remains1s; no polling-cadence alias'],limitations=['Observer-only validation; no physical SQL/controller comparison.','Actual wake latency is measured on this server/run, not a universal latency bound.'])
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:sampler.stop();log.close();report.update(ended_utc=now(),protocol_sha256=sha(protocol),code_sha256=sha(__file__),sampler_sha256=sha(Path(__file__).parent/'publication_sampler.py'),events_sha256=sha(out/'events.jsonl'));write_json(out/'result.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
