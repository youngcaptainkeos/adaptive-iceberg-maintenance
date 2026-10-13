#!/usr/bin/env python3
"""Audited recovery of source range files; no invented bytes or lost-header reconstruction."""
import argparse
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import shutil,time,urllib.request


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024): h.update(chunk)
    return h.hexdigest()


def durable_json(path,value):
    with Path(path).open('x') as stream:
        json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())


def recover(config_path):
    config_path=Path(config_path).resolve();cfg=json.loads(config_path.read_text());base=config_path.parent
    if cfg['schema_version']!='https_range_recovery_v1': raise ValueError('Unsupported recovery protocol')
    prior=(base/cfg['prior_directory']).resolve();prior_record=prior/'acquisition_record.json'
    if digest(prior_record)!=cfg['prior_record_sha256']: raise ValueError('Prior evidence changed')
    old=json.loads(prior_record.read_text());source_cfg=old['configuration']
    if old['status']!='failed_preserved_ranges' or digest(prior/'acquisition_code.py')!=old['tool_sha256']: raise ValueError('Prior producer/custody not verified')
    url=source_cfg['source_url'];expected=source_cfg['expected_bytes'];quantum=source_cfg['range_bytes'];modified=source_cfg['expected_last_modified']
    if not url.startswith('https://'): raise ValueError('HTTPS source required')
    for field in ('concurrency','attempts_per_leaf','minimum_leaf_bytes','socket_timeout_seconds','progress_interval_seconds'):
        if not isinstance(cfg[field],int) or isinstance(cfg[field],bool) or cfg[field]<=0: raise ValueError('Positive '+field+' required')
    if cfg['minimum_leaf_bytes']>quantum or cfg['retry_delay_seconds']<0: raise ValueError('Invalid leaf/retry settings')
    root=(base/cfg['output_directory']).resolve();root.mkdir(parents=True,exist_ok=False)
    parts=root/'parts';parts.mkdir();leaves=root/'leaves';leaves.mkdir()
    for src,name in [(config_path,'recovery_config.json'),(Path(__file__),'recovery_code.py'),(prior_record,'prior_acquisition_record.json'),(prior/'acquisition_code.py','prior_acquisition_code.py')]: shutil.copy2(src,root/name)
    if shutil.disk_usage(root).free<2*expected: raise ValueError('Insufficient retained/assembled storage')
    manifest={};started=time.monotonic();progress=(root/'progress.jsonl').open('x')
    record={'schema_version':'range_recovery_record_v1','configuration':cfg,'source_configuration':source_cfg,'status':'in_progress','started_at':datetime.now(timezone.utc).isoformat(),'tool_sha256':digest(__file__)}
    def save():
        temp=root/'recovery_record.tmp';temp.write_text(json.dumps(record,indent=2)+'\n');temp.replace(root/'recovery_record.json')
    def emit(kind,**values):
        row=dict(kind=kind,recorded_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started,**values);progress.write(json.dumps(row)+'\n');progress.flush();print(json.dumps(row),flush=True)
    def leaf(begin,end):
        failures=[]
        for attempt in range(1,cfg['attempts_per_leaf']+1):
            path=leaves/f'{begin}_{end}_attempt{attempt}.partial';count=0;h=hashlib.sha256()
            try:
                req=urllib.request.Request(url,headers={'Range':f'bytes={begin}-{end}','Accept-Encoding':'identity','If-Unmodified-Since':modified})
                with urllib.request.urlopen(req,timeout=cfg['socket_timeout_seconds']) as r:
                    headers=dict(r.headers)
                    if r.status!=206 or r.headers.get('Content-Range')!=f'bytes {begin}-{end}/{expected}' or int(r.headers['Content-Length'])!=end-begin+1 or r.headers.get('Last-Modified')!=modified or not r.url.startswith('https://'): raise RuntimeError('Source/version/offset mismatch')
                    with path.open('xb') as stream:
                        while chunk:=r.read(16384):
                            count+=len(chunk)
                            if count>end-begin+1: raise RuntimeError('Excess bytes')
                            stream.write(chunk);h.update(chunk)
                        stream.flush();os.fsync(stream.fileno())
                if count!=end-begin+1: raise IOError('Short source response')
                final=path.with_suffix('.complete');path.rename(final)
                info={'begin':begin,'end':end,'bytes':count,'sha256':h.hexdigest(),'path':str(final.relative_to(root)),'headers':headers,'failed_attempts':failures}
                durable_json(final.with_suffix('.receipt.json'),info)
                return [info]
            except RuntimeError: raise
            except Exception as exc:
                failures.append({'attempt':attempt,'error':str(exc),'bytes':count,'retained_partial':str(path.relative_to(root)) if path.exists() else None})
                if attempt<cfg['attempts_per_leaf']: time.sleep(cfg['retry_delay_seconds'])
        path.with_suffix('.failure.json').write_text(json.dumps(failures,indent=2)+'\n')
        if end-begin+1<=cfg['minimum_leaf_bytes']: raise IOError('Source transfer failed at minimum leaf size')
        middle=(begin+end)//2
        return leaf(begin,middle)+leaf(middle+1,end)
    def fetch(index):
        begin=index*quantum;end=min(expected-1,begin+quantum-1);receipts=leaf(begin,end)
        part=parts/f'{index:08d}.part';h=hashlib.sha256();position=begin
        with part.open('xb') as out:
            for receipt in receipts:
                if receipt['begin']!=position or digest(root/receipt['path'])!=receipt['sha256']: raise ValueError('Leaf continuity/hash failure')
                data=(root/receipt['path']).read_bytes();out.write(data);h.update(data);position=receipt['end']+1
            out.flush();os.fsync(out.fileno())
        if position!=end+1: raise ValueError('Incomplete main range')
        info={'index':index,'begin':begin,'end':end,'bytes':end-begin+1,'sha256':h.hexdigest(),'path':str(part.relative_to(root)),'verification':'fresh_exact_https_ranges','leaf_receipts':receipts}
        durable_json(part.with_suffix('.receipt.json'),info);return info
    try:
        with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=cfg['socket_timeout_seconds']) as r:
            if int(r.headers['Content-Length'])!=expected or r.headers.get('Last-Modified')!=modified: raise ValueError('Source changed')
        count=(expected+quantum-1)//quantum
        for old_part in sorted((prior/'parts').glob('*.part')):
            index=int(old_part.stem);begin=index*quantum;end=min(expected-1,begin+quantum-1)
            if not 0<=index<count or old_part.stat().st_size!=end-begin+1: raise ValueError('Invalid recovered part')
            if old_part.stat().st_mtime_ns>prior_record.stat().st_mtime_ns: raise ValueError('Prior part changed after failure record')
            target=parts/old_part.name;shutil.copy2(old_part,target)
            info={'index':index,'begin':begin,'end':end,'bytes':target.stat().st_size,'sha256':digest(target),'path':str(target.relative_to(root)),
                  'verification':'recovered_from_exclusive_verified_producer','limitation':'Original per-range response/hash receipt was not persisted. Hash measured at recovery, not compared with lost historical hash; require final gzip/tar integrity and dataset inspection.'}
            durable_json(target.with_suffix('.receipt.json'),info);manifest[index]=info
        record['recovered_ranges']=len(manifest);save();emit('recovery_started',recovered_ranges=len(manifest),expected_bytes=expected)
        missing=iter(i for i in range(count) if i not in manifest);last=time.monotonic()
        with ThreadPoolExecutor(max_workers=cfg['concurrency']) as pool:
            active={pool.submit(fetch,i) for i in [next(missing,None) for _ in range(cfg['concurrency'])] if i is not None}
            while active:
                done,active=wait(active,return_when=FIRST_COMPLETED)
                for future in done:
                    info=future.result();manifest[info['index']]=info
                    i=next(missing,None)
                    if i is not None: active.add(pool.submit(fetch,i))
                if time.monotonic()-last>=cfg['progress_interval_seconds']:
                    record.update(completed_ranges=len(manifest),verified_bytes=sum(i['bytes'] for i in manifest.values()));save();emit('progress',completed_ranges=len(manifest),verified_bytes=record['verified_bytes']);last=time.monotonic()
        if len(manifest)!=count: raise ValueError('Missing main ranges')
        (root/'range_manifest.json').write_text(json.dumps([manifest[i] for i in range(count)],indent=2)+'\n')
        target=root/(source_cfg['filename']+'.partial');h=hashlib.sha256();total=0
        with target.open('xb') as out:
            for index in range(count):
                info=manifest[index];p=root/info['path']
                if digest(p)!=info['sha256']: raise ValueError('Stored part changed')
                with p.open('rb') as stream:
                    while chunk:=stream.read(1024*1024): out.write(chunk);h.update(chunk);total+=len(chunk)
            out.flush();os.fsync(out.fileno())
        if total!=expected: raise ValueError('Assembled object size mismatch')
        target.rename(root/source_cfg['filename']);record.update(status='downloaded_bytes_only',verified_bytes=total,completed_ranges=count,sha256=h.hexdigest(),ended_at=datetime.now(timezone.utc).isoformat(),scope='Archive/schema validation still required; recovered-header provenance limitation retained.')
        emit('complete_bytes',sha256=h.hexdigest(),bytes=total)
    except Exception as exc:
        record.update(status='failed_preserved_artifacts',error=str(exc),completed_ranges=len(manifest),verified_bytes=sum(i['bytes'] for i in manifest.values()));emit('failed',error=str(exc));raise
    finally: save();progress.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True);args=parser.parse_args();recover(args.config)
