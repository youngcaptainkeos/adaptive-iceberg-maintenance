#!/usr/bin/env python3
"""Acquire complete verified HTTPS byte ranges; preserve errors/partials and exact source bytes."""
import argparse
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024): h.update(chunk)
    return h.hexdigest()


def acquire(config_path):
    config_path=Path(config_path).resolve();cfg=json.loads(config_path.read_text())
    if cfg.get('schema_version')!='https_range_acquisition_v1' or not cfg['source_url'].startswith('https://'):
        raise ValueError('Declared HTTPS range protocol required')
    for name in ('expected_bytes','range_bytes','concurrency','max_attempts_per_range','socket_timeout_seconds','progress_interval_seconds'):
        if not isinstance(cfg[name],int) or isinstance(cfg[name],bool) or cfg[name]<=0: raise ValueError('Positive integer '+name+' required')
    if Path(cfg['filename']).name!=cfg['filename'] or not cfg['rationale']: raise ValueError('Leaf filename and rationale required')
    expected=cfg['expected_bytes'];root=(config_path.parent/cfg['output_directory']).resolve()
    root.mkdir(parents=True,exist_ok=False);parts=root/'parts';parts.mkdir()
    shutil.copy2(config_path,root/'acquisition_config.json');shutil.copy2(__file__,root/'acquisition_code.py')
    if shutil.disk_usage(root).free<2*expected: raise ValueError('Need storage for retained parts plus assembled object')
    progress=(root/'progress.jsonl').open('x');start=time.monotonic();manifest={}
    record={'schema_version':'https_range_acquisition_record_v1','configuration':cfg,'started_at':datetime.now(timezone.utc).isoformat(),
            'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'tool_sha256':digest(__file__),'status':'in_progress'}
    def save():
        temp=root/'acquisition_record.tmp';temp.write_text(json.dumps(record,indent=2)+'\n');temp.replace(root/'acquisition_record.json')
    def emit(status,**values):
        row=dict(status=status,recorded_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,**values)
        progress.write(json.dumps(row)+'\n');progress.flush();print(json.dumps(row),flush=True)
    def fetch(index,begin,end):
        expected_range=f'bytes {begin}-{end}/{expected}';failures=[]
        for attempt in range(1,cfg['max_attempts_per_range']+1):
            path=parts/f'{index:08d}.attempt{attempt}.partial';count=0;h=hashlib.sha256()
            try:
                request=urllib.request.Request(cfg['source_url'],headers={'Range':f'bytes={begin}-{end}','Accept-Encoding':'identity','If-Unmodified-Since':cfg['expected_last_modified']})
                with urllib.request.urlopen(request,timeout=cfg['socket_timeout_seconds']) as response:
                    # Source-version/offset mismatches are fatal, never retried as short transfers.
                    if response.status!=206 or response.headers.get('Content-Range')!=expected_range or int(response.headers['Content-Length'])!=end-begin+1 or response.headers.get('Last-Modified')!=cfg['expected_last_modified'] or not response.url.startswith('https://'):
                        raise RuntimeError('Source version or range response mismatch')
                    with path.open('xb') as stream:
                        while chunk:=response.read(65536):
                            count+=len(chunk)
                            if count>end-begin+1: raise RuntimeError('Excess range bytes')
                            stream.write(chunk);h.update(chunk)
                        stream.flush();os.fsync(stream.fileno())
                if count!=end-begin+1: raise IOError('Short verified-range response')
                final=parts/f'{index:08d}.part';path.rename(final)
                return {'index':index,'begin':begin,'end':end,'bytes':count,'sha256':h.hexdigest(),'path':str(final.relative_to(root))},failures
            except RuntimeError: raise
            except Exception as exc:
                failures.append({'attempt':attempt,'error_type':type(exc).__name__,'error':str(exc),'received_bytes':count,'retained_partial':str(path.relative_to(root)) if path.exists() else None})
        raise IOError(json.dumps({'range_index':index,'exhausted_attempts':failures}))
    try:
        request=urllib.request.Request(cfg['source_url'],headers={'Accept-Encoding':'identity'},method='HEAD')
        with urllib.request.urlopen(request,timeout=cfg['socket_timeout_seconds']) as response:
            record['head_headers']=dict(response.headers)
            if int(response.headers['Content-Length'])!=expected or response.headers.get('Last-Modified')!=cfg['expected_last_modified']:
                raise ValueError('Publisher source changed')
        save();emit('range_download_started',expected_bytes=expected,range_bytes=cfg['range_bytes'],concurrency=cfg['concurrency'])
        ranges=iter((index,begin,min(expected-1,begin+cfg['range_bytes']-1)) for index,begin in enumerate(range(0,expected,cfg['range_bytes'])))
        last_progress=time.monotonic()
        with ThreadPoolExecutor(max_workers=cfg['concurrency']) as pool:
            active={pool.submit(fetch,*item) for item in [next(ranges,None) for _ in range(cfg['concurrency'])] if item is not None}
            while active:
                completed,active=wait(active,return_when=FIRST_COMPLETED)
                for future in completed:
                    info,failures=future.result();info['failed_attempts']=failures;manifest[info['index']]=info
                    item=next(ranges,None)
                    if item is not None: active.add(pool.submit(fetch,*item))
                if time.monotonic()-last_progress>=cfg['progress_interval_seconds']:
                    record.update(completed_ranges=len(manifest),verified_bytes=sum(p['bytes'] for p in manifest.values()))
                    save();emit('range_download_progress',completed_ranges=len(manifest),verified_bytes=record['verified_bytes']);last_progress=time.monotonic()
        expected_parts=(expected+cfg['range_bytes']-1)//cfg['range_bytes']
        if len(manifest)!=expected_parts: raise ValueError('Missing verified ranges')
        with (root/'range_manifest.json').open('x') as stream: json.dump([manifest[i] for i in range(expected_parts)],stream,indent=2)
        assembled=root/(cfg['filename']+'.partial');h=hashlib.sha256();count=0
        with assembled.open('xb') as stream:
            for index in range(expected_parts):
                info=manifest[index];part=root/info['path']
                if digest(part)!=info['sha256']: raise ValueError('Stored range checksum changed')
                with part.open('rb') as source:
                    while chunk:=source.read(1024*1024): stream.write(chunk);h.update(chunk);count+=len(chunk)
            stream.flush();os.fsync(stream.fileno())
        if count!=expected: raise ValueError('Assembled size mismatch')
        assembled.rename(root/cfg['filename'])
        record.update(status='downloaded_bytes_only',sha256=h.hexdigest(),verified_bytes=count,completed_ranges=len(manifest),ended_at=datetime.now(timezone.utc).isoformat(),scope='Complete HTTPS object bytes only; gzip/tar/schema/row validation still required. No publisher cryptographic checksum available.')
        emit('range_download_complete',verified_bytes=count,sha256=h.hexdigest())
    except Exception as exc:
        record.update(status='failed_preserved_ranges',error_type=type(exc).__name__,error=str(exc),completed_ranges=len(manifest),verified_bytes=sum(p['bytes'] for p in manifest.values()))
        emit('range_download_failed',error_type=type(exc).__name__,error=str(exc));raise
    finally:
        save();progress.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True)
    args=parser.parse_args();acquire(args.config)
