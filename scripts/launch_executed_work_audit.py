#!/usr/bin/env python3
"""Worker3-only, one-shot detached launcher for the saved-raw audit.

Run only after transport/HEAD inspection. No retries, SQL, service changes,
physical experiment launch, or guessed original outcomes.
"""
import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from three_model_maintenance.research.common import now, read, require, sha, utc, write_new
from three_model_maintenance.research.executed_work_audit import CODE, prepare


def launch(args):
    require(ROOT == Path('/mnt/nfs-storage/shashank_prafullathta/implementation'),
            'Launch only in the registered worker3 checkout')
    require(re.fullmatch(r'[a-z0-9][a-z0-9_]{0,95}', args.label), 'Invalid unique label')
    require(re.fullmatch(r'[0-9a-f]{40}', args.expected_head), 'Full intended commit SHA required')
    output = ROOT/'results'/args.label
    require(not output.exists(), 'Output already exists; preserve original attempt')
    directory = ROOT/'results'/(args.label+'_launch')
    directory.mkdir(parents=True,exist_ok=False)
    receipt = dict(status='preparing',host=socket.gethostname(),started_utc=now(),
                   label=args.label,estimated_first_check_seconds=60,
                   estimate_rationale='Saved-file-only audit; inspect after60s, not a runtime guarantee.')
    try:
        require(utc(args.latest_start) > utc(now()), 'Fresh cutoff required before launch')
        head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        require(head == args.expected_head, 'Worker HEAD differs from intended commit')
        for name in CODE:
            committed = subprocess.check_output(['git','show',head+':'+name],cwd=ROOT)
            require(hashlib.sha256(committed).hexdigest() == sha(ROOT/name),
                    'Intended code/config is dirty: '+name)
        reference = (ROOT/args.reference_protocol).resolve()
        require(reference.is_relative_to(ROOT), 'Reference must stay inside checkout')
        committed = subprocess.check_output(['git','show',head+':'+str(reference.relative_to(ROOT))],cwd=ROOT)
        require(hashlib.sha256(committed).hexdigest() == sha(reference), 'Reference registration dirty')
        table = subprocess.check_output(['ps','-eo','pid=,args='],text=True)
        active = []
        for row in table.splitlines():
            fields = row.strip().split(None,1)
            if len(fields) != 2 or int(fields[0]) == os.getpid(): continue
            command = fields[1]
            if not re.match(r'(?:\S*/)?python(?:3(?:\.\d+)?)?\s', command): continue
            if 'start-thriftserver.sh' in command and '--label sf10_fresh_backend_' in command: continue
            if any(token in command for token in ('three_model_maintenance','queue_aware_maintenance',
                    'run_with_failure_alert.py','collect_training_data.py','train_cost_benefit_models.py')):
                active.append(row.strip())
        require(not active, 'Existing project executor(s): '+repr(active))
        receipt['head'] = head
        protocol = directory/'protocol.json'
        prepare(reference,args.latest_start,protocol)
        cfg = read(protocol)
        # Compare existing frozen evidence rather than silently repinning it.
        for name,digest in cfg['inputs'].items():
            from three_model_maintenance.research.executed_work_audit import relative_file
            require(sha(relative_file(ROOT,name)) == digest, 'Frozen input mismatch: '+name)
        require(utc(now()) < utc(args.latest_start), 'Cutoff expired during preparation')
        command = ['nohup',sys.executable,'-B','scripts/phase6-live-evaluation/run_with_failure_alert.py',
            '--label',args.label,'--receipt',str(directory/'failure_notification.json'),'--',
            sys.executable,'-B','-m','three_model_maintenance.research.executed_work_audit','run',
            '--protocol',str(protocol),'--output',str(output)]
        receipt.update(command=command,protocol_sha256=sha(protocol),log=str(directory/'run.log'))
        write_new(directory/'admission.json',receipt)
        with (directory/'run.log').open('xb') as log:
            child = subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,
                                     stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        receipt.update(status='launched',pid=child.pid,launched_utc=now())
    except Exception as exc:
        receipt.update(status='failed_launch_preserved',error=str(exc))
        # Admission failures also alert, without inventing a child run.
        sys.path.insert(0,str(ROOT/'scripts/phase6-live-evaluation'))
        from failure_notifications import notify_failure
        notify_failure(args.label,str(exc),directory/'failure_notification.json')
        raise
    finally:
        # A live child is never killed if saving the launch receipt fails.
        write_new(directory/'launch.json',receipt)
        print(json.dumps(receipt),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--expected-head',required=True)
    parser.add_argument('--latest-start',required=True)
    parser.add_argument('--reference-protocol',default='three_model_maintenance/protocols/live_history_audit02_20261114.json')
    launch(parser.parse_args())
