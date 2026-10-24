"""Wait without experiment locks; launch SF10 only after intact prerequisite work.

Reads only terminal metadata while waiting. No SQL, generation, source scans,
model fitting, service changes or repeated scientific attempts during the wait.
"""
import argparse
import fcntl
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime,timezone
from pathlib import Path
from three_model_maintenance.contracts import require
from three_model_maintenance.training.data import read,save,sha
from three_model_maintenance.experiments.scale_query import checked

REPO=Path(__file__).resolve().parents[2]


def now():return datetime.now(timezone.utc)


def free_locks():
    held=[]
    try:
        for name in ('.three_model_collection.lock','.queue_aware_study.lock','.common_horizon_cohort.lock','.physical_correctness.lock'):
            stream=(REPO/'results'/name).open('a');held.append(stream)
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return False
        return True
    finally:
        for stream in held:stream.close()


def run(protocol):
    cfg=read(protocol)
    require(cfg['schema_version']=='deferred_sf10_after_queue_v1' and type(cfg['poll_seconds']) is int and cfg['poll_seconds']>0,'Unknown deferred registration')
    root=Path(cfg['output_directory']);root.mkdir(parents=True,exist_ok=False)
    save(root/'registration.json',cfg)
    state={'status':'source_preflight','started_utc':now().isoformat(),'pid':__import__('os').getpid(),
           'sf10_launched':False,'sf10_stages_unattempted':6,'protocol_sha256':sha(protocol),
           'SQL_executed_by_waiter':False,'source_generation_by_waiter':False,'model_fit_performed':False}
    def progress():
        temp=root/'progress.next.json';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'progress.json')
    try:
        require(subprocess.check_output(['git','show','HEAD:'+str(protocol.relative_to(REPO))],cwd=REPO)==protocol.read_bytes(),'Uncommitted wait registration')
        target=REPO/cfg['target_protocol']['path'];require(sha(target)==cfg['target_protocol']['sha256'],'Changed SF10 registration')
        require(subprocess.check_output(['git','show','HEAD:'+str(target.relative_to(REPO))],cwd=REPO)==target.read_bytes(),'SF10 target not committed unchanged')
        checked(read(target))  # AST/source/generator digests only, no source-data scan or Spark call.
        save(root/'source_preflight.json',{'status':'passed_frozen_source_AST_and_registration_only',
             'target_protocol_sha256':sha(target),'waiter_source_sha256':sha(Path(__file__)),
             'SQL_executed':False,'dataset_generated':False,'physical_plan_parser_validated':False,
             'ended_utc':now().isoformat()})
        state['status']='waiting_for_prerequisite_terminal_and_resource_release';progress()
        dependency=Path(cfg['prerequisite_directory']);deadline=datetime.fromisoformat(cfg['latest_launch_utc'])
        while True:
            require(now()<deadline,'Deferred launch deadline reached; no SF10 work launched')
            terminal=dependency/'result.json'
            if terminal.exists():
                try:result=read(terminal)
                except json.JSONDecodeError:
                    time.sleep(cfg['poll_seconds']);continue
                require(result['protocol_sha256']==cfg['prerequisite_protocol_sha256'],'Different prerequisite identity')
                require(result['status']=='completed_storage_comparison_development_only' and
                        result['passed']==4 and result['failed']==result['unattempted']==0,
                        'Prerequisite did not complete its four integrity-checked arms; SF10 remains unattempted')
                analysis=dependency/'analysis/result.json'
                require(sha(analysis)==result['analysis_sha256'] and
                        read(analysis)['status']=='passed_four_arm_raw_storage_comparison_only','Prerequisite audit missing/changed')
                if free_locks():
                    state.update(prerequisite_result_sha256=sha(terminal),prerequisite_analysis_sha256=sha(analysis))
                    break
            state['last_checked_utc']=now().isoformat();progress();time.sleep(cfg['poll_seconds'])
        require(sha(target)==cfg['target_protocol']['sha256'],'Target changed while deferred')
        checked(read(target));state.update(status='launching_sf10',sf10_launch_attempted=True,launch_utc=now().isoformat());progress()
        with (root/'sf10.log').open('x') as log:
            child_process=subprocess.Popen([sys.executable,'-B',str(REPO/'scripts/phase6-live-evaluation/run_with_failure_alert.py'),
                '--label',cfg['label']+'_sf10','--receipt',str(root/'sf10_failure_alert.json'),'--',sys.executable,'-B','-m',
                'three_model_maintenance.experiments.scale_query','--protocol',str(target)],cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
            state.update(sf10_launched=True,child_pid=child_process.pid);progress()
            returncode=child_process.wait()
        state['child_returncode']=returncode
        child_root=Path(read(target)['output_directory'])
        if (child_root/'result.json').exists():
            child=read(child_root/'result.json');state['child_result_sha256']=sha(child_root/'result.json')
            state['sf10_stages_unattempted']=6-len(child['stages'])
        require(returncode==0,'SF10 child failed; preserve failures/unattempted stages, no retry')
        require((child_root/'result.json').exists(),'Missing SF10 terminal result')
        require(child['status']=='completed_sf10_capability_only','SF10 terminal status differs')
        state['status']='completed_deferred_sf10_capability_only'
    except Exception as exc:
        state.update(status='failed_or_blocked_preserved_no_retry',error=str(exc),traceback=traceback.format_exc());raise
    finally:
        state['ended_utc']=now().isoformat();progress();save(root/'result.json',state)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True)
    run(parser.parse_args().protocol.resolve())
