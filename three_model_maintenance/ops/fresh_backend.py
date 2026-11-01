"""Start one fresh isolated Spark identity; never stop or restart a process."""
import argparse,ast,fcntl,json,os,subprocess,traceback
from pathlib import Path
from three_model_maintenance.experiments.sf10_scratch_recovery import backend
from three_model_maintenance.contracts import require
from three_model_maintenance.training.data import read,save,sha
from three_model_maintenance.experiments.sf10_campaign import REPO,now


def run(protocol):
    cfg=read(protocol)
    require(cfg['scope']=='fresh_isolated_backend_only_no_SQL_no_restart','Unknown fresh backend scope')
    require(subprocess.check_output(['git','show','HEAD:'+str(protocol.relative_to(REPO))],cwd=REPO)==protocol.read_bytes(),'Uncommitted backend registration')
    for spec in cfg['sources']+cfg['binaries']:
        path=Path(spec['path']);path=path if path.is_absolute() else REPO/path
        require(sha(path)==spec['sha256'],'Changed registered backend input '+str(path))
        if path.suffix=='.py':ast.parse(path.read_text(),filename=str(path))
    root=Path(cfg['output_directory']);root.mkdir(parents=True,exist_ok=False);save(root/'registration.json',cfg)
    locks=[];state=dict(status='starting_fresh_isolated_backend',pid=os.getpid(),started_utc=now(),protocol_sha256=sha(protocol),SQL_executed=False)
    try:
        for n in ('.three_model_collection.lock','.queue_aware_study.lock','.common_horizon_cohort.lock','.physical_correctness.lock'):
            f=(REPO/'results'/n).open('a');locks.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=[]
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');comm=(p/'comm').read_text().strip()
            except (FileNotFoundError,ProcessLookupError):continue
            if comm=='java' and ('org.apache.spark' in cmd or 'HiveThriftServer2' in cmd):existing.append(dict(pid=int(p.name),command=cmd))
        save(root/'existing_spark_processes.json',dict(processes=existing,observed_utc=now()))
        require(not existing,'Existing Spark process found; do not replace or restart it')
        url,app=backend(cfg,root)
        state.update(status='ready_fresh_isolated_backend_only',base_url=url,spark_app_id=app,service_retained=True)
    except Exception as e:state.update(status='failed_preserved_no_restart',error=str(e),traceback=traceback.format_exc());raise
    finally:
        state['ended_utc']=now();save(root/'result.json',state)
        for f in locks:f.close()
    print(json.dumps(state),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);a=p.parse_args();run(a.protocol.resolve())
