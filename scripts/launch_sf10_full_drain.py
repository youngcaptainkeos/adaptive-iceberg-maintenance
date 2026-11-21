#!/usr/bin/env python3
"""Worker-only one-shot detached full-drain engineering validation launcher."""
import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from three_model_maintenance.research.common import read,require,sha,utc,now,write_new
from three_model_maintenance.full_drain.contract import validate,verify_inputs,verify_committed,WORKER


def launch(protocol,expected_head):
    require(ROOT==WORKER,'Launch only on worker3; no local SQL validation')
    cfg=validate(read(protocol));label=cfg['experiment_id']
    out=Path(cfg['output_directory']).resolve();require(out.is_relative_to(ROOT/'results') and not out.exists(),'Existing/invalid output path')
    directory=ROOT/'results'/(label+'_launch');directory.mkdir(exist_ok=False)
    receipt=dict(status='preparing',label=label,started_utc=now(),host=socket.gethostname(),
                 estimated_first_check_seconds=60,estimate='First inspection only; full drain has no assumed duration.')
    try:
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        require(head==expected_head,'Intended full HEAD mismatch');receipt['head']=head
        require(utc(now())<utc(cfg['no_new_episode_after_utc']),'New-episode cutoff reached')
        verify_committed(protocol,cfg,head)
        processes=subprocess.check_output(['ps','-eo','pid=,args='],text=True)
        for row in processes.splitlines():
            parts=row.strip().split(None,1)
            if len(parts)!=2 or int(parts[0])==os.getpid():continue
            command=parts[1]
            if 'python' not in command.split()[0]:continue
            if 'start-thriftserver.sh' in command and '--label sf10_fresh_backend_' in command:continue
            require(not any(s in command for s in ('three_model_maintenance','queue_aware_maintenance','run_with_failure_alert.py')),
                    'Another project executor is active: '+row.strip())
        verify_inputs(cfg)
        command=['nohup',sys.executable,'-B','scripts/phase6-live-evaluation/run_with_failure_alert.py',
                 '--label',label,'--receipt',str(directory/'failure_notification.json'),'--',sys.executable,'-B','-m',
                 'three_model_maintenance.full_drain.job','--protocol',str(protocol.resolve()),'--expected-head',head,
                 '--receipt',str(directory/'child_result.json')]
        receipt.update(command=command,protocol_sha256=sha(protocol),log=str(directory/'run.log'))
        write_new(directory/'admission.json',receipt)
        with (directory/'run.log').open('xb') as log:
            child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        receipt.update(status='launched',pid=child.pid,launched_utc=now())
    except Exception as exc:
        receipt.update(status='failed_launch_preserved',error=str(exc))
        sys.path.insert(0,str(ROOT/'scripts/phase6-live-evaluation'))
        from failure_notifications import notify_failure
        notify_failure(label,str(exc),directory/'failure_notification.json');raise
    finally:write_new(directory/'launch.json',receipt);print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--expected-head',required=True)
    a=p.parse_args();launch(a.protocol,a.expected_head)
