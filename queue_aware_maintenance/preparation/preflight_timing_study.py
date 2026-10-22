#!/usr/bin/env python3
"""Exercise intervention rules on real previously observed decision frontiers."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,ast,json,csv,subprocess
from pathlib import Path
from queue_aware_maintenance.core.common import checked,require,sha,write_json,now
from queue_aware_maintenance.policies.controller_factory import build_policy
from queue_aware_maintenance.models.costs import EmpiricalCosts
from queue_aware_maintenance.models.forecast import SeasonalArrivalForecast

def run(protocol,output):
 cfg=json.loads(Path(protocol).read_text());out=Path(output);out.mkdir(exist_ok=False,parents=True);report={'status':'running','started_utc':now(),'protocol_sha256':sha(protocol),'new_SQL_executed':False}
 try:
  for p in PACKAGE_ROOT.rglob('*.py'):ast.parse(p.read_text())
  import run_episode,audit_episode,run_timing_study
  for n,h in cfg['code_sha256'].items():require(sha(source_file(n))==h,'Timing source changed '+n)
  proof=json.loads(checked(cfg['previous_raw_audit']).read_text());require(proof['status']=='passed_preserved_incomplete_cohort_raw_audit','Prior raw audit not complete')
  d=Path(cfg['preflight_observed_episode']);saved=json.loads((d/'result.json').read_text());require(sha(d/'events.jsonl')==saved['events_sha256'],'Changed development observations')
  actual=json.loads((d/'config.json').read_text());require(sha(d/'mapped_arrivals.csv')==actual['mapping']['sha256'],'Changed real mapped source');mapping={r['source_query_id']:r for r in csv.DictReader((d/'mapped_arrivals.csv').open())};events=[json.loads(line) for line in (d/'events.jsonl').open() if '"kind": "controller_decision"' in line];require(events,'No actual decision frontiers')
  costs=EmpiricalCosts.load(checked(cfg['episode_template']['model']));forecast=SeasonalArrivalForecast(actual['arrivals'],origin=actual['observation_origin_utc'],history_days=actual['forecast_history_days'],bin_seconds=actual['decision_interval_seconds'],freeze_source_time=actual['forecast_history_freeze_utc'])
  checks=[]
  for action in cfg['actions']:
   ecfg=dict(cfg['episode_template'],policy=action['policy'])
   if action['policy']=='fixed_start':ecfg['fixed_start_seconds']=action['seconds']
   policy=build_policy(ecfg,costs,forecast);seen_before=seen_after=False
   for event in events:
    prior=event['decision'];queued=[mapping[i] for i in prior['queued_source_ids']];elapsed=prior['elapsed_seconds'];r=policy.decide(elapsed_seconds=elapsed,queued=queued,last_offered_query_id=None,files=ecfg['initial_file_count'])
    expected=action['policy']=='fixed_start' and action['seconds']<=elapsed<ecfg['horizon_seconds'];require(r['execute_now']==expected and r['queued_source_ids']==prior['queued_source_ids'],'Actual-frontier intervention check failed')
    if action['policy']=='fixed_start':seen_before|=elapsed<action['seconds'];seen_after|=elapsed>=action['seconds']
   if action['policy']=='fixed_start':require(seen_after and (action['seconds']==0 or seen_before),'Actual source lacks registered boundary coverage')
   checks.append({'action':action['name'],'actual_frontiers_checked':len(events),'physical_execution':False})
  require(len(cfg['orders'])==2 and cfg['orders'][1]==list(reversed(cfg['orders'][0])),'Unbalanced repeated order')
  require(all(sorted(o)==sorted(a['name'] for a in cfg['actions']) for o in cfg['orders']),'Missing intervention in repeat')
  delivery=cfg.get('documentation_delivery','immediate_push')
  if delivery=='immediate_push':subprocess.run(['git','push','--dry-run','origin','main'],cwd=cfg['canonical_repository'],check=True)
  else:require(delivery=='worker_commits_deferred_push_v1' and cfg.get('deferred_push_user_authorization')=='Proceed; defer documentation pushes','Deferred publication requires explicit user authorization')
  subprocess.run(['git','var','GIT_AUTHOR_IDENT'],cwd=cfg['canonical_repository'],check=True,stdout=subprocess.DEVNULL)
  subprocess.run(['git','var','GIT_COMMITTER_IDENT'],cwd=cfg['canonical_repository'],check=True,stdout=subprocess.DEVNULL)
  report['documentation_delivery']=delivery
  report.update(status='passed_actual_frontier_timing_preflight_only',checks=checks,source_events_sha256=saved['events_sha256'],limitations=['Real previous elapsed times/queue IDs exercise intervention behavior, not physical timing benefit.','No generated data or SQL. Forecast and cost model remain unchanged; fixed intervention does not use predictions.'])
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:report['ended_utc']=now();write_json(out/'result.json',report)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.protocol,a.output)
