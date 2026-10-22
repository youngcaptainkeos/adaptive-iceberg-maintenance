"""Registered planning estimate plus real exclusive-lock admission; not a guarantee."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,fcntl,json
from pathlib import Path
from datetime import timedelta
from queue_aware_maintenance.core.common import checked,require,utc,now,write_json,sha

def evaluate(cfg,prepared,repo):
 diagnostics=json.loads(checked(cfg['resource_admission']['model_diagnostics']).read_text());bywindow={d['window_index']:d for d in diagnostics};clock=utc(now());cursor=clock;arms=[]
 for window,order in zip(prepared['workloads'],cfg['registered_orders']):
  for policy in order:
   duration=bywindow[window['window_index']]['noaction_model_drain_seconds']+cfg['episode_template']['telemetry']['warmup_seconds'];arms.append({'window_index':window['window_index'],'policy':policy,'estimated_start_utc':cursor.isoformat(),'estimated_duration_seconds':duration});cursor+=timedelta(seconds=duration)
 require(arms,'Empty admission population');start_cutoff=utc(cfg['no_new_episode_after_utc']);operation_cutoff=utc(cfg['no_new_operation_after_utc']);last_start=utc(arms[-1]['estimated_start_utc']);total=(cursor-clock).total_seconds();last_offset=(last_start-clock).total_seconds();latest=min(start_cutoff-timedelta(seconds=last_offset),operation_cutoff-timedelta(seconds=total));locks=[]
 for name in ('.physical_correctness.lock','.queue_aware_study.lock'):
  with (Path(repo)/'results'/name).open('a') as f:
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True;fcntl.flock(f,fcntl.LOCK_UN)
   except BlockingIOError:free=False
  locks.append({'name':name,'free_at_check':free})
 return {'observed_utc':clock.isoformat(),'admitted_at_check':all(x['free_at_check'] for x in locks) and last_start<start_cutoff and cursor<operation_cutoff,'resource_locks':locks,'estimated_arms':arms,'estimated_total_seconds':total,'estimated_terminal_utc':cursor.isoformat(),'latest_model_feasible_launch_utc':latest.isoformat(),'limitations':['Planning estimate, not a physical bound: no-action empirical drain plus registered warmup; initialization, final audits, drift and observer overhead remain additional.','All exclusive resources and cutoffs must be checked again immediately before launch.','No compression, partial-cohort substitution or acceptance-gate change permitted to meet budget.']}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--study-protocol',required=True);p.add_argument('--output',required=True);a=p.parse_args();cfg=json.loads(Path(a.study_protocol).read_text());prepared=json.loads(checked(cfg['core_preparation']).read_text());report=evaluate(cfg,prepared,REPOSITORY_ROOT);report.update(status='audited_resource_admission_decision_only',study_protocol_sha256=sha(a.study_protocol),code_sha256=sha(__file__),new_SQL_executed=False);write_json(a.output,report);print(json.dumps(report),flush=True)
