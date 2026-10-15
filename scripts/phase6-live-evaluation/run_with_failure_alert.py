#!/usr/bin/env python3
"""Run a real test/job with failure alert; no synthetic test and no retries."""
import argparse,subprocess,sys
from failure_notifications import notify_failure

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--label',required=True);p.add_argument('--receipt',required=True)
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();command=a.command
    if command and command[0]=='--':command=command[1:]
    if not command:p.error('A real command is required')
    try:
        result=subprocess.run(command);rc=result.returncode
        if rc:notify_failure(a.label,f'Command failed with exit status {rc}. Inspect the registered run log; no automatic retry.',a.receipt)
    except Exception as exc:
        notify_failure(a.label,'Execution failed: '+str(exc),a.receipt);raise
    sys.exit(rc if rc>=0 else 128-rc)
