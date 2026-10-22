#!/usr/bin/env python3
"""Wait for one identity-bound real collection, then audit its entire cohort once."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,json,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
from queue_aware_maintenance.core.common import checked,require,sha,write_json,now,utc


def process(pid):
 p=Path('/proc')/str(pid)
 try:
  stat=(p/'stat').read_text().split(') ',1)[1].split()
  return {'start_ticks':int(stat[19]),'state':stat[0],'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()}
 except FileNotFoundError:return None


def run(protocol,expected_sha):
 require(sha(__file__)==expected_sha,'Follow-up source changed')
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'waiting_for_identity_bound_collection','started_utc':now(),'source_sha256':expected_sha,'protocol_sha256':sha(protocol),'no_physical_operations':True}
 def save():
  temp=out/'progress.tmp';temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(out/'progress.json')
 save()
 try:
  while True:
   current=process(cfg['coordinator_pid'])
   if current is None or current['state']=='Z':break
   require(current['start_ticks']==cfg['coordinator_start_ticks'] and cfg['coordinator_command_contains'] in current['command'],'Coordinator identity changed; never follow a reused PID')
   if datetime.now(timezone.utc)>=utc(cfg['no_new_analysis_after_utc']):
    report.update(status='deadline_reached_collection_preserved_analysis_unattempted',observed_process=current);return 0
   time.sleep(cfg['poll_seconds'])
  require(datetime.now(timezone.utc)<utc(cfg['no_new_analysis_after_utc']),'No new analysis after authorized deadline')
  runtime=Path(cfg['analysis_runtime']);require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=runtime,text=True).strip()==cfg['analysis_revision'],'Analysis runtime revision changed')
  for name,digest in cfg['analysis_source_sha256'].items():require(sha(source_file(name, repository=runtime))==digest,'Frozen analysis source changed: '+name)
  cohort=Path(cfg['cohort_result']);r=json.loads(cohort.read_text());report['cohort_result_sha256']=sha(cohort)
  require(r['status']=='completed_full_physical_feasibility_pending_independent_comparison' and (r['passed'],r['failed'],r['unattempted'])==(8,0,0),'Incomplete/failed cohort preserved; no survivor analysis')
  for p in Path('/proc').iterdir():
   if p.name.isdigit():
    actual=process(int(p.name))
    require(actual is None or str(source_file('run_episode.py', repository=runtime)) not in actual['command'],'Physical client still live; analysis not admitted')
  semantics=checked(cfg['semantics_audit']);registration=Path(cfg['comparison_protocol']);comparison=Path(cfg['comparison_output_directory']);require(not registration.exists() and not comparison.exists(),'Do not overwrite or rerun previous analysis')
  command=[sys.executable,'-B',str(source_file('register_comparison.py', repository=runtime)),'--cohort-result',str(cohort),'--semantics-audit',str(semantics),'--protocol',str(registration),'--output-directory',str(comparison)]
  with (out/'registration.log').open('x') as log:subprocess.run(command,cwd=runtime,stdout=log,stderr=subprocess.STDOUT,check=True)
  require(datetime.now(timezone.utc)<utc(cfg['no_new_analysis_after_utc']),'Analysis launch cutoff reached after evidence binding')
  command=[sys.executable,'-B','-u',str(runtime/'scripts/phase6-live-evaluation/run_with_failure_alert.py'),'--label',cfg['comparison_label'],'--receipt',cfg['comparison_failure_receipt'],'--',sys.executable,'-B','-u',str(source_file('compare_study.py', repository=runtime)),'--protocol',str(registration)]
  with Path(cfg['comparison_log']).open('x') as log:
   child=subprocess.Popen(command,cwd=runtime,stdout=log,stderr=subprocess.STDOUT);report.update(status='whole_cohort_analysis_running',analysis_wrapper_pid=child.pid,analysis_started_utc=now(),command=command);save();rc=child.wait()
  report['analysis_returncode']=rc;require(rc==0,'Whole-cohort analysis failed; preserve original failure')
  result=json.loads((comparison/'result.json').read_text());require(result['status']=='passed_complete_physical_and_raw_reconstruction_feasibility','Independent comparison did not pass')
  report.update(status='completed_whole_cohort_analysis_pending_final_requirements_and_mirror',comparison_result_sha256=sha(comparison/'result.json'),goal_complete=False);return 0
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:report['ended_utc']=now();save();write_json(out/'result.json',report);print(json.dumps(report),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--expected-sha256',required=True);a=p.parse_args();sys.exit(run(a.protocol,a.expected_sha256))
