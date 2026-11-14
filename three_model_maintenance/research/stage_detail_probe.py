"""One read of each genuine absent stage reference; no SQL or old-run acceptance."""
import argparse,json,hashlib,urllib.request,urllib.error,datetime,traceback
from pathlib import Path

def main(protocol,output):
 c=json.loads(protocol.read_text());output.mkdir(parents=True,exist_ok=False)
 r=dict(status='running',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),SQL_executed=False,old_run_accepted=False,stages=[])
 try:
  source=Path(c['selection_path']);assert hashlib.sha256(source.read_bytes()).hexdigest()==c['selection_sha256']
  selection=json.loads(source.read_text());ids=selection['plan']['missing_referenced_stage_ids'];assert len(ids)==2
  for sid in ids:
   assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(c['deadline'])
   url=c['base']+'/stages/'+str(sid);rec=dict(stage_id=sid,url=url,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
   try:
    with urllib.request.urlopen(url,timeout=15) as response:raw=response.read();rec['http_status']=response.status
   except urllib.error.HTTPError as exc:
    raw=exc.read();rec['http_status']=exc.code
   (output/f'{sid}.raw.json').write_bytes(raw);rec['raw_sha256']=hashlib.sha256(raw).hexdigest();rec['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
   r['stages'].append(rec)
   assert rec['http_status']==200,'Missing stage detail HTTP'+str(rec['http_status'])
   values=json.loads(raw);assert isinstance(values,list) and values,'Empty stage detail'
   rec['observed_states']=[dict(stageId=s['stageId'],attemptId=s['attemptId'],status=s['status']) for s in values]
   assert all(s['stageId']==sid and type(s['attemptId']) is int and s['attemptId']==0 and s['status'] in ['COMPLETE','SKIPPED'] for s in values),'Nonterminal/adverse detail'
  r['status']='passed_actual_stage_detail_capability_only'
 except Exception as exc:r.update(status='failed_preserved',error=str(exc),traceback=traceback.format_exc());raise
 finally:
  r['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(output/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.protocol,a.output)
