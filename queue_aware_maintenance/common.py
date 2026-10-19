"""Shared explicit data contracts; unsupported evidence fails rather than fabricates."""
import csv,hashlib,json,math,sys,urllib.request
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parent/'instrumentation'))
from experiment_validation import require

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read_csv(path):
 with Path(path).open() as f:return list(csv.DictReader(f))
def write_json(path,value):
 with Path(path).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def checked(spec):
 p=Path(spec['path']);require(p.is_file() and sha(p)==spec['sha256'],'Missing/changed evidence '+str(p));return p
def now():return datetime.now(timezone.utc).isoformat()
def notify(label,message,receipt,config):
 record={'label':label,'message':message,'utc':now()}
 try:
  c=json.loads(Path(config).read_text());request=urllib.request.Request(c['topic_url'],data=(label+'\n'+message).encode(),headers={'Title':label,'Tags':'information'},method='POST')
  with urllib.request.urlopen(request,timeout=c['timeout_seconds']) as r:record.update(status='delivered',http_status=r.status,response=json.load(r))
 except Exception as e:record.update(status='notification_failed_preserved',error=str(e))
 write_json(receipt,record);return record
