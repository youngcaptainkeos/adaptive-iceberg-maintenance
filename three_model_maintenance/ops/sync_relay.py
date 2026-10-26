"""Laptop-only git/raw transport while remote science waits between units.

No model, SQL, test or experiment runs here. No credential copy/creation, force
push, reset, deletion or merging divergent histories. Offline/conflicting client
stops relay and alerts; remote retains work and waits at its synchronization gate.
"""
import argparse,hashlib,json,os,shlex,subprocess,sys,time,traceback
from datetime import datetime,timezone
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts/phase6-live-evaluation'))
from failure_notifications import notify_failure


def run(protocol):
    cfg=json.loads(protocol.read_text());root=REPO/'results'/(cfg['label']+'_sync_relay');root.mkdir(exist_ok=False)
    remote='/mnt/nfs-storage/shashank_prafullathta/implementation';target=cfg['output_directory'];host='ccbd@10.10.3.232'
    dest=REPO/'results'/Path(target).name
    def command(args):return subprocess.check_output(args,cwd=REPO,text=True,stderr=subprocess.STDOUT)
    def ssh(script):return command(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',host,script])
    def status(value):
        p=root/'status.next.json';p.write_text(json.dumps(value,indent=2)+'\n');p.replace(root/'status.json')
    try:
        last=command(['git','rev-parse','HEAD']).strip()
        while datetime.now(timezone.utc)<datetime.fromisoformat(cfg['no_new_SQL_after_utc']):
            head=ssh('git -C '+shlex.quote(remote)+' rev-parse HEAD').strip()
            terminal=ssh('if test -f '+shlex.quote(target+'/result.json')+'; then cat '+shlex.quote(target+'/result.json')+'; fi').strip()
            ended=False
            if terminal:
                try:ended=bool(json.loads(terminal).get('ended_utc'))
                except json.JSONDecodeError:pass
            if head!=last or ended:
                command(['git','fetch',host+':'+remote,'main:refs/remotes/sf10-sync/main'])
                command(['git','merge','--ff-only','refs/remotes/sf10-sync/main'])
                dest.mkdir(parents=True,exist_ok=True)
                command(['rsync','-a',host+':'+target+'/',str(dest)+'/'])
                differences=command(['rsync','-rcni',host+':'+target+'/',str(dest)+'/'])
                if differences:raise RuntimeError('Raw checksum mirror differs: '+differences)
                names=['docs/methodology_working_doc.md','docs/updated_methodology_working_doc.md']
                remote_hash=ssh('cd '+shlex.quote(remote)+' && sha256sum '+' '.join(names))
                local_hash=''.join(hashlib.sha256((REPO/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in names)
                if remote_hash!=local_hash or command(['git','rev-parse','HEAD']).strip()!=head:raise RuntimeError('HEAD/methodology SHA differs')
                ack=dict(head=head,raw_checksum_verified=True,methodology_SHA256_verified=True,client_HEAD_verified=True,
                         client_raw_directory=str(dest),observed_utc=datetime.now(timezone.utc).isoformat())
                encoded=json.dumps(ack,indent=2)+'\n';name='client_sync_'+head+'.json'
                (dest/name).write_text(encoded)
                subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',host,
                    'cat > '+shlex.quote(target+'/'+name)],input=encoded,text=True,check=True)
                command(['git','push','origin','main'])
                last=head;status(dict(status='synced',head=head,raw_directory=str(dest),checksum_differences=False,terminal=ended,updated_utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid()))
                if ended:return
            time.sleep(cfg['sync_poll_seconds'])
        raise RuntimeError('Transport deadline reached; inspect remote terminal, do not cancel it')
    except Exception as exc:
        status(dict(status='failed_preserved_no_reset',error=str(exc),traceback=traceback.format_exc(),pid=os.getpid()))
        notify_failure(cfg['label']+'_transport_relay',str(exc)+'; remote operations preserved, dependent work waits for GitHub synchronization.',str(root/'failure_alert.json'))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True);run(parser.parse_args().protocol.resolve())
