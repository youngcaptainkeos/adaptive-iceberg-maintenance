#!/usr/bin/env python3
"""Acquire declared HTTPS public source bytes with exclusive artifacts and provenance."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request


def acquire(config_path):
    config_path=Path(config_path).resolve();cfg=json.loads(config_path.read_text())
    if cfg.get('schema_version')!='https_dataset_acquisition_v1': raise ValueError('Unsupported acquisition config')
    if not cfg.get('rationale') or not cfg['source_url'].startswith('https://'): raise ValueError('Source/rationale required')
    expected=cfg['expected_bytes']
    if not isinstance(expected,int) or isinstance(expected,bool) or expected<=0: raise ValueError('Expected source bytes required')
    if Path(cfg['filename']).name!=cfg['filename']: raise ValueError('Use a leaf filename')
    timeout=cfg['socket_timeout_seconds'];progress_interval=cfg['progress_interval_seconds']
    if timeout<=0 or progress_interval<=0: raise ValueError('Declare positive operational timeouts')
    root=(config_path.parent/cfg['output_directory']).resolve()
    root.mkdir(parents=True,exist_ok=False)
    shutil.copy2(config_path,root/'acquisition_config.json');shutil.copy2(__file__,root/'acquisition_code.py')
    metadata={'schema_version':'https_dataset_acquisition_record_v1','source_url':cfg['source_url'],
              'started_at':datetime.now(timezone.utc).isoformat(),'configuration':cfg,
              'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'status':'in_progress','downloaded_bytes':0}
    progress=(root/'progress.jsonl').open('x')
    def emit(status,**extra):
        record=dict(status=status,recorded_at=datetime.now(timezone.utc).isoformat(),**extra)
        progress.write(json.dumps(record)+'\n');progress.flush();print(json.dumps(record),flush=True)
    try:
        headers={'Accept-Encoding':'identity'}
        head=urllib.request.Request(cfg['source_url'],headers=headers,method='HEAD')
        with urllib.request.urlopen(head,timeout=timeout) as response:
            metadata['head_headers']=dict(response.headers);metadata['resolved_url']=response.url
            if int(response.headers['Content-Length'])!=expected: raise ValueError('Publisher source size changed')
            if response.headers.get('Last-Modified')!=cfg['expected_last_modified']: raise ValueError('Publisher modification time changed')
        if shutil.disk_usage(root).free<expected: raise ValueError('Insufficient storage for declared object')
        partial=root/(cfg['filename']+'.partial');h=hashlib.sha256();read_bytes=0;start=time.monotonic();last_progress=start
        emit('download_started',expected_bytes=expected)
        request=urllib.request.Request(cfg['source_url'],headers=headers)
        with urllib.request.urlopen(request,timeout=timeout) as response,partial.open('xb') as stream:
            if response.status!=200 or int(response.headers['Content-Length'])!=expected: raise ValueError('Unexpected GET response/size')
            if response.headers.get('Last-Modified')!=cfg['expected_last_modified']: raise ValueError('Source changed between HEAD/GET')
            if not response.url.startswith('https://'): raise ValueError('Source redirected away from HTTPS')
            metadata['get_headers']=dict(response.headers)
            while chunk:=response.read(1024*1024):
                read_bytes+=len(chunk)
                if read_bytes>expected: raise ValueError('Response larger than declared object')
                stream.write(chunk);h.update(chunk)
                if time.monotonic()-last_progress>=progress_interval:
                    emit('download_progress',downloaded_bytes=read_bytes,elapsed_seconds=time.monotonic()-start)
                    last_progress=time.monotonic()
        metadata['downloaded_bytes']=read_bytes
        if read_bytes!=expected: raise ValueError('Incomplete source object')
        metadata.update(status='downloaded_bytes_only',sha256=h.hexdigest(),ended_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,
                        scope='HTTPS source bytes acquired; archive/schema/row validation still required. No publisher cryptographic checksum supplied.')
        partial.rename(root/cfg['filename'])
        emit('download_complete',downloaded_bytes=read_bytes,sha256=h.hexdigest())
    except Exception as exc:
        partial=root/(cfg['filename']+'.partial')
        metadata.update(status='failed_preserved_partial',error_type=type(exc).__name__,error=str(exc),downloaded_bytes=partial.stat().st_size if partial.exists() else 0)
        emit('download_failed',error_type=type(exc).__name__,error=str(exc),downloaded_bytes=metadata['downloaded_bytes'])
        raise
    finally:
        (root/'acquisition_record.json').write_text(json.dumps(metadata,indent=2)+'\n');progress.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True)
    args=parser.parse_args();acquire(args.config)
