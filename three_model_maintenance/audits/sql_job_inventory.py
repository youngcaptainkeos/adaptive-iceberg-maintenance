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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    cfg=json.loads(a.protocol.read_text());a.output.mkdir(parents=True,exist_ok=False)
    url=cfg['spark_jobs_url'].split('/jobs?',1)[0]+'/sql?details=true&planDescription=true'
    started=datetime.now(timezone.utc).isoformat()
    with urllib.request.urlopen(url,timeout=cfg['rest_timeout_seconds']) as response:raw=response.read()
    ended=datetime.now(timezone.utc).isoformat();payload=json.loads(raw)
    if not isinstance(payload,list):raise ValueError('Actual SQL inventory must be a list')
    (a.output/'raw_sql_inventory.json').write_bytes(raw)
    result=dict(status='captured_actual_retained_SQL_metadata_only',url=url,request_started_utc=started,
        response_ended_utc=ended,sql_execution_count=len(payload),raw_sha256=hashlib.sha256(raw).hexdigest(),
        observed_keys=sorted({k for row in payload for k in row}),SQL_executed=False,
        original_campaign_accepted=False,limitation='Retained post-hoc metadata may be incomplete; absent execution or job links remain missing.')
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
