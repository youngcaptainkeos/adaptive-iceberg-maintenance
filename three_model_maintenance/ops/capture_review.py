"""Transport/display only: automatically screenshot actual remote evidence pages.

No fitting, query execution, evidence validation or fabricated terminal images.
Requires an existing SSH tunnel and installed Chrome. Raw status and manifest
accompany captures. Historical experiment data stays labelled historical.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request


def run(protocol,once=False):
    cfg=json.loads(protocol.read_text());out=Path(cfg['local_screenshot_directory']);out.mkdir(parents=True,exist_ok=True)
    manifest=out/'capture_manifest.jsonl'
    last_signature=None
    while datetime.now(timezone.utc)<datetime.fromisoformat(cfg['display_until_utc']):
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        try:
            with urllib.request.urlopen(cfg['local_dashboard_url']+'/api/status',timeout=cfg['rest_timeout_seconds']) as response:raw=response.read()
            data=json.loads(raw)
            signature=json.dumps(dict(campaign=data['campaign'],counts=data['measured']['event_counts'],
                active_jobs=data['live_spark_running_jobs'],error=data['live_spark_error']),sort_keys=True)
            if signature==last_signature and not once:
                time.sleep(cfg['screenshot_interval_seconds']);continue
            sidecar=out/(stamp+'__'+cfg['campaign_id']+'__source.json');sidecar.write_bytes(raw)
            pages=[('LIVE_processes',cfg['local_dashboard_url']+'/processes'),
                   ('MIXED_live_service_historical_results',cfg['local_dashboard_url']+'/'),
                   ('HISTORICAL_failed_audit',cfg['local_dashboard_url']+'/audit'),
                   ('LIVE_Spark_UI_historical_jobs',cfg['local_spark_url']+'/jobs/')]
            for label,url in pages:
                image=out/(stamp+'__'+cfg['campaign_id']+'__'+label+'.png')
                command=[cfg['chrome_executable'],'--headless','--disable-gpu','--disable-dev-shm-usage',
                    '--no-first-run','--no-default-browser-check','--hide-scrollbars','--window-size=1700,1800',
                    '--user-data-dir='+cfg['chrome_profile_directory'],'--screenshot='+str(image),url]
                log=out/(stamp+'__'+label+'.browser.log')
                with log.open('xb') as stream:rc=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT).returncode
                record=dict(captured_utc=stamp,label=label,source_url=url,source_observed_utc=data['observed_utc'],
                    campaign_id=cfg['campaign_id'],source_snapshot=str(sidecar),returncode=rc,
                    image=str(image),sha256=hashlib.sha256(image.read_bytes()).hexdigest() if image.exists() else None,
                    scope='Browser screenshot of actual remote page; not scientific acceptance')
                with manifest.open('a') as stream:stream.write(json.dumps(record)+'\n')
                if rc!=0 or not image.exists():raise RuntimeError('Screenshot failed; browser log retained: '+str(log))
            last_signature=signature
        except Exception as exc:
            with manifest.open('a') as stream:stream.write(json.dumps(dict(captured_utc=stamp,error=str(exc),status='capture_failed_preserved'))+'\n')
            raise
        if once:return
        time.sleep(cfg['screenshot_interval_seconds'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--once',action='store_true');a=p.parse_args();run(a.protocol,a.once)
