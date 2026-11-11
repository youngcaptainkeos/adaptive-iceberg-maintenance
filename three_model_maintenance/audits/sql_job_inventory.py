"""Capture actual retained SQL execution metadata; no SQL is executed.

Post-hoc inventory, not a replacement for original frozen evidence or acceptance.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import urllib.request


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--page-length',type=int,required=True);p.add_argument('--max-pages',type=int,required=True);a=p.parse_args()
    if a.page_length<=0 or a.max_pages<=0:raise ValueError('Register positive pagination/resource limits')
    cfg=json.loads(a.protocol.read_text());a.output.mkdir(parents=True,exist_ok=False)
    base=cfg['spark_jobs_url'].split('/jobs?',1)[0]+'/sql?details=true&planDescription=true'
    started=datetime.now(timezone.utc).isoformat();payload=[];receipts=[];seen=set()
    for page in range(a.max_pages):
        url=base+'&offset='+str(page*a.page_length)+'&length='+str(a.page_length)
        before=datetime.now(timezone.utc).isoformat()
        with urllib.request.urlopen(url,timeout=cfg['rest_timeout_seconds']) as response:raw=response.read()
        values=json.loads(raw)
        if not isinstance(values,list):raise ValueError('Actual SQL inventory must be a list')
        name='page_'+str(page)+'.json';(a.output/name).write_bytes(raw)
        receipts.append(dict(url=url,request_started_utc=before,response_ended_utc=datetime.now(timezone.utc).isoformat(),file=name,sha256=hashlib.sha256(raw).hexdigest(),count=len(values)))
        for row in values:
            if row['id'] in seen:raise ValueError('Duplicate SQL ID across pages; inventory changed or pagination failed')
            seen.add(row['id']);payload.append(row)
        if len(values)<a.page_length:break
    else:raise ValueError('Registered pagination bound exhausted; inventory incomplete')
    ended=datetime.now(timezone.utc).isoformat();raw=(json.dumps(payload,indent=2)+'\n').encode()
    (a.output/'raw_sql_inventory.json').write_bytes(raw)
    result=dict(status='captured_actual_retained_SQL_metadata_only',url=url,request_started_utc=started,
        response_ended_utc=ended,sql_execution_count=len(payload),raw_sha256=hashlib.sha256(raw).hexdigest(),
        observed_keys=sorted({k for row in payload for k in row}),pages=receipts,SQL_executed=False,
        original_campaign_accepted=False,limitation='Retained post-hoc metadata may be incomplete; absent execution or job links remain missing.')
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
