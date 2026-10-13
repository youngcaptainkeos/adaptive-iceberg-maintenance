#!/usr/bin/env python3
"""Full-byte TPC-H source inventory; no data generation, table writes or authenticity claim."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

TABLES=('customer','lineitem','nation','orders','part','partsupp','region','supplier')
IO_CHUNK_BYTES=1024*1024  # Streaming I/O buffer, not a scientific/policy parameter.


def audit(directory,output,scale_factor,rationale):
    directory=Path(directory).resolve();output=Path(output)
    if output.exists(): raise ValueError('Refuse to overwrite evidence')
    if scale_factor<=0 or not rationale.strip(): raise ValueError('Declare positive scale and inventory rationale')
    paths=[directory/(name+'.tbl') for name in TABLES]
    if not all(p.is_file() for p in paths): raise ValueError('Missing TPC-H source table')
    output.parent.mkdir(parents=True,exist_ok=True)
    result={'schema_version':'tpch_source_inventory_v1','host':socket.gethostname(),
            'started_at':datetime.now(timezone.utc).isoformat(),'scale_factor_declared':scale_factor,
            'rationale':rationale,'scope':'Fresh full-byte hashes and newline row counts; not typed parsing or generator authenticity',
            'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'generator_manifest_present':(directory/'manifest.txt').is_file(),'tables':[]}
    start=time.monotonic()
    for path in paths:
        before=path.stat();h=hashlib.sha256();rows=0;read_bytes=0;tail=b'';table_start=time.monotonic()
        with path.open('rb') as stream:
            while chunk:=stream.read(IO_CHUNK_BYTES):
                h.update(chunk);rows+=chunk.count(b'\n');read_bytes+=len(chunk);tail=chunk[-1:]
        after=path.stat()
        if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
            raise ValueError('Source changed during read: '+str(path))
        if tail!=b'\n' or read_bytes!=after.st_size: raise ValueError('Incomplete source read or unterminated row')
        item={'table':path.stem,'path':str(path),'bytes':read_bytes,'rows':rows,'sha256':h.hexdigest(),
              'mtime_ns':after.st_mtime_ns,'elapsed_seconds':time.monotonic()-table_start}
        result['tables'].append(item);print(json.dumps(item),flush=True)
    result['ended_at']=datetime.now(timezone.utc).isoformat();result['elapsed_seconds']=time.monotonic()-start
    with output.open('x') as stream: json.dump(result,stream,indent=2);stream.write('\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--scale-factor',required=True,type=int);parser.add_argument('--rationale',required=True)
    args=parser.parse_args();audit(args.directory,args.output,args.scale_factor,args.rationale)
