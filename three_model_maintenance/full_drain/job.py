"""Persist the real child exit after cleanup; the outer failure wrapper alerts."""
import argparse
import subprocess
import sys
from pathlib import Path
from three_model_maintenance.research.common import now,read,require,sha,write_new
from .contract import ROOT,WORKER


def run(protocol,expected_head,receipt):
    require(ROOT==WORKER,'Worker-only detached job')
    require(not receipt.exists(),'Never replace a child receipt')
    cfg=read(protocol)
    record=dict(status='starting',started_utc=now(),protocol_sha256=sha(protocol),
                code_revision=expected_head,label=cfg['experiment_id'],exit_code=None)
    command=[sys.executable,'-B','-m','three_model_maintenance.full_drain.runner',
             '--protocol',str(protocol.resolve()),'--expected-head',expected_head]
    record['command']=command
    try:
        child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,start_new_session=True)
        record['pid']=child.pid
        print('Physical child PID: '+str(child.pid),flush=True)
        record['exit_code']=child.wait()
        record['status']='child_exited'
        output=Path(cfg['output_directory'])
        record['acceptance_sha256']=sha(output/'acceptance.json') if (output/'acceptance.json').is_file() else None
        record['result_sha256']=sha(output/'result.json') if (output/'result.json').is_file() else None
    except Exception as exc:
        record.update(status='failed_job_preserved',error=str(exc));raise
    finally:
        record['ended_utc']=now();write_new(receipt,record)
    return record['exit_code'] if record['exit_code']>=0 else 128-record['exit_code']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--expected-head',required=True);p.add_argument('--receipt',type=Path,required=True)
    a=p.parse_args();sys.exit(run(a.protocol,a.expected_head,a.receipt))
