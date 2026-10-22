#!/usr/bin/env python3
"""Actual-source integration checks for explicit legacy/repaired controller versions."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,ast,json
from pathlib import Path
from queue_aware_maintenance.core.common import checked,require,write_json,sha,now
from queue_aware_maintenance.models.costs import EmpiricalCosts
from queue_aware_maintenance.models.forecast import SeasonalArrivalForecast
from queue_aware_maintenance.policies.controller_factory import build_policy
from queue_aware_maintenance.observability.sampler_factory import build_sampler
from queue_aware_maintenance.observability.publication_sampler import PublicationTelemetrySampler
from physical_measurements import EventLog,TelemetrySampler

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False);report={'status':'running','started_utc':now(),'physical_validation_passed':False}
 try:
  for p in PACKAGE_ROOT.rglob('*.py'):ast.parse(p.read_text())
  import run_episode,compare_study,register_comparison
  prepared=json.loads(checked(cfg['core_preparation']).read_text());proof=json.loads(checked(cfg['snapshot_model_verification']).read_text());costs=EmpiricalCosts.load(checked(prepared['model']));diagnostics=json.loads((Path(cfg['core_preparation']['path']).parent/'model_diagnostics.json').read_text());decisions=[]
  forecast=SeasonalArrivalForecast(cfg['arrivals'],origin=cfg['observation_origin_utc'],history_days=cfg['forecast_history_days'],bin_seconds=cfg['decision_interval_seconds'],freeze_source_time=prepared['workloads'][0]['start'])
  for w in prepared['workloads']:
   for version in ('fluid_v1','snapshot_whole_call_v2'):
    for policy in cfg['policies']:
     episode=dict(cfg,policy_model_version=version,policy=policy,source_start_utc=w['start'],source_end_utc=w['end']);controller=build_policy(episode,costs,forecast);d=controller.decide(elapsed_seconds=0,queued=[],last_offered_query_id=None,files=cfg['initial_file_count'])
     if policy=='queue_aware':
      reference=diagnostics[w['window_index']]['forecast_decision'] if version=='fluid_v1' else proof['diagnostics'][w['window_index']]['past_only_forecast_decision'];require(d['chosen']==reference['chosen'] and d['candidates']==reference['candidates'],'Controller wiring changes registered model decisions')
     if policy=='no_maintenance':require(not d['execute_now'],'Null control rewrites')
     if policy=='immediate':require(d['execute_now'],'Immediate control waits')
     decisions.append({'window_index':w['window_index'],'version':version,'policy':policy,'decision':d})
  require(run_episode.build_policy is build_policy,'Physical runner not wired to versioned factory')
  if 'telemetry_publication_validation' in cfg:
   log=EventLog(out/'factory_configuration.jsonl','future_runner_factory_configuration')
   try:
    actual=build_sampler(cfg,log);require(type(actual) is PublicationTelemetrySampler,'Future observer factory selects old polling');legacy=build_sampler(dict(cfg,telemetry_wait_contract='interval_poll_v1'),log);require(type(legacy) is TelemetrySampler,'Old observer version silently upgraded');require(run_episode.build_sampler is build_sampler,'Physical runner bypasses observer factory');log.emit('factory_configuration_validated',telemetry_wait_contract=cfg['telemetry_wait_contract'],actual_validation=cfg['telemetry_publication_validation'],independent_audit=cfg['telemetry_publication_audit'],real_counters_sampled_in_this_configuration_check=False)
   finally:log.close()
  report.update(status='passed_actual_source_versioned_controller_wiring_only',decisions=decisions,checks=['All sources parse and final analysis/registration modules import','Sixteen actual-source policy/window/version constructions execute','Legacy choices preserve original core decisions; snapshot choices preserve repaired proof','Physical runner imports the same versioned factory'],limitations=['No new physical episode run; frozen active study still fluid_v1.','New snapshot controller needs fresh physical registration and real validation.'])
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:report.update(ended_utc=now(),protocol_sha256=sha(protocol),code_sha256=sha(__file__),factory_sha256=sha(source_file('controller_factory.py')),runner_sha256=sha(source_file('run_episode.py')));write_json(out/'result.json',report);print(json.dumps({k:v for k,v in report.items() if k!='decisions'}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
