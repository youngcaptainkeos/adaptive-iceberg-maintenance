#!/usr/bin/env python3
"""Read actual archive members against supplied publisher schema; no replay generation."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import tarfile


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024): h.update(chunk)
    return h.hexdigest()


def audit(archive_path,schema_path,expected_archive_sha256,output_path):
    archive=Path(archive_path);schema=Path(schema_path);output=Path(output_path)
    if output.exists(): raise ValueError('Refuse to overwrite evidence')
    if digest(archive)!=expected_archive_sha256: raise ValueError('Archive checksum mismatch')
    schemas={}
    with schema.open(newline='') as stream:
        for row in csv.DictReader(stream):
            record={k.strip():v.strip() for k,v in row.items()}
            schemas.setdefault(record['file name'],[]).append(record)
    result={'schema_version':'alibaba_member_audit_v1','archive_path':str(archive),
            'archive_sha256':expected_archive_sha256,'publisher_schema_path':str(schema),
            'publisher_schema_sha256':digest(schema),'members':[],
            'scope':'Full member schema, numeric/missing-value and timestamp audit; does not authorize SQL replay'}
    seen=set()
    with tarfile.open(archive,'r|gz') as tar:
        for member in tar:
            if not member.isfile(): continue
            name=Path(member.name).name
            if name not in schemas: raise ValueError('Unknown archive member '+member.name)
            if name in seen: raise ValueError('Duplicate archive member '+name)
            seen.add(name);fields=schemas[name]
            fields.sort(key=lambda f:int(f['field number']))
            if [int(f['field number']) for f in fields]!=list(range(1,len(fields)+1)):
                raise ValueError('Non-contiguous publisher schema')
            summary={'name':member.name,'bytes':member.size,'rows':0,'wrong_column_rows':0,
                     'column_counts':Counter(),'columns':[{'name':f['content'],'type':f['format'],
                       'mandatory':f['mandatory']=='YES','missing':0,'invalid_numeric':0,'nonfinite':0,
                       'minimum':None,'maximum':None} for f in fields],
                     'first_time_negative':0,'first_time_zero':0,'first_time_positive':0,
                     'global_time_decreases':0,'task_duplicate_keys':0,'task_identical_duplicate_rows':0,
                     'status_counts':Counter()}
            h=hashlib.sha256();read_bytes=0;last_time=None;task_keys=set();task_rows=set()
            with tar.extractfile(member) as raw:
                def lines():
                    nonlocal read_bytes
                    for line in raw:
                        h.update(line);read_bytes+=len(line);yield line.decode('utf-8')
                for row in csv.reader(lines()):
                    summary['rows']+=1;summary['column_counts'][len(row)]+=1
                    if len(row)!=len(fields):
                        summary['wrong_column_rows']+=1;continue
                    first_time=None
                    for index,(value,f,col) in enumerate(zip(row,fields,summary['columns'])):
                        if value=='': col['missing']+=1;continue
                        if f['format'] not in ('INTEGER','FLOAT'): continue
                        try: number=int(value) if f['format']=='INTEGER' else float(value)
                        except ValueError: col['invalid_numeric']+=1;continue
                        if not math.isfinite(number): col['nonfinite']+=1;continue
                        col['minimum']=number if col['minimum'] is None else min(col['minimum'],number)
                        col['maximum']=number if col['maximum'] is None else max(col['maximum'],number)
                        if index==0: first_time=number
                    if first_time is not None:
                        key='first_time_negative' if first_time<0 else 'first_time_zero' if first_time==0 else 'first_time_positive'
                        summary[key]+=1
                        if last_time is not None and first_time<last_time: summary['global_time_decreases']+=1
                        last_time=first_time
                    if name=='batch_task.csv':
                        key=tuple(row[2:4]);values=tuple(row)
                        if key in task_keys: summary['task_duplicate_keys']+=1
                        task_keys.add(key)
                        if values in task_rows: summary['task_identical_duplicate_rows']+=1
                        task_rows.add(values)
                    if name in ('batch_task.csv','batch_instance.csv'):
                        summary['status_counts'][row[5]]+=1
            if read_bytes!=member.size: raise ValueError('Incomplete member read '+name)
            summary['sha256']=h.hexdigest()
            summary['schema_violations']=summary['wrong_column_rows']+sum(c['invalid_numeric']+c['nonfinite']+(c['missing'] if c['mandatory'] else 0) for c in summary['columns'])
            result['members'].append(summary)
            print(name,'rows',summary['rows'],'schema violations',summary['schema_violations'],flush=True)
    if seen!=set(schemas): raise ValueError('Missing publisher schema members')
    if digest(archive)!=expected_archive_sha256: raise ValueError('Archive changed during audit')
    result['interpretation']='Report every issue; known source omissions are not imputed or silently dropped. Timestamp zero/negative are censored pre-trace events per publisher.'
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream: json.dump(result,stream,indent=2);stream.write('\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True);parser.add_argument('--schema',required=True)
    parser.add_argument('--expected-sha256',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();audit(args.archive,args.schema,args.expected_sha256,args.output)
