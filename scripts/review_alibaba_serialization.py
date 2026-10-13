#!/usr/bin/env python3
"""Adjudicate one observed serialization mismatch; preserve strict audit and every row."""
import argparse
import csv
from datetime import datetime,timezone
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


def review(archive,schema,strict_audit,output):
    output=Path(output)
    if output.exists(): raise ValueError('Refuse to overwrite evidence')
    strict=json.loads(Path(strict_audit).read_text())
    if digest(archive)!=strict['archive_sha256'] or digest(schema)!=strict['publisher_schema_sha256']:
        raise ValueError('Source/schema mismatch against strict audit')
    name='container_event.csv';member_record=next(m for m in strict['members'] if Path(m['name']).name==name)
    with Path(schema).open(newline='') as stream:
        fields=[{k.strip():v.strip() for k,v in row.items()} for row in csv.DictReader(stream) if row['file name'].strip()==name]
    fields.sort(key=lambda f:int(f['field number']))
    count=0;missing=[0]*len(fields);invalid=[0]*len(fields);times=[];types={};h=hashlib.sha256();read_bytes=0
    found=False
    with tarfile.open(archive,'r|gz') as tar:
        for member in tar:
            if member.name!=member_record['name']: continue
            found=True
            with tar.extractfile(member) as raw:
                def lines():
                    nonlocal read_bytes
                    for line in raw:
                        h.update(line);read_bytes+=len(line);yield line.decode('utf-8')
                for raw_row in csv.reader(lines()):
                    if len(raw_row)!=len(fields)+1 or raw_row[-1]!='':
                        raise ValueError('Extra field is not exactly one empty trailing field')
                    row=raw_row[:-1]  # Explicit adjudicated CSV terminator; never discard nonempty data.
                    count+=1
                    for i,(value,field) in enumerate(zip(row,fields)):
                        if not value:
                            missing[i]+=1;continue
                        if field['format'] in ('INTEGER','FLOAT'):
                            try: value=int(value) if field['format']=='INTEGER' else float(value)
                            except ValueError: invalid[i]+=1;continue
                            if not math.isfinite(value): invalid[i]+=1
                    if row[0]: times.append(int(row[0]))
                    types[row[1]]=types.get(row[1],0)+1
            break
    if not found or count!=member_record['rows'] or read_bytes!=member_record['bytes'] or h.hexdigest()!=member_record['sha256']:
        raise ValueError('Incomplete or altered container member')
    if digest(archive)!=strict['archive_sha256']: raise ValueError('Archive changed during review')
    violations=sum(invalid)+sum(n for n,f in zip(missing,fields) if f['mandatory']=='YES')
    result={'schema_version':'alibaba_serialization_review_v1','checked_at':datetime.now(timezone.utc).isoformat(),
            'tool_sha256':digest(__file__),'archive_sha256':strict['archive_sha256'],
            'strict_audit_sha256':digest(strict_audit),'schema_sha256':digest(schema),'member':member_record['name'],
            'member_sha256':h.hexdigest(),'rows':count,'raw_csv_fields':len(fields)+1,'semantic_fields':len(fields),
            'rule':'Every actual row has exactly one extra empty trailing field; remove only this serialization terminator, never pad/drop semantic values',
            'columns':[{'name':f['content'],'missing':m,'invalid_numeric':v,'mandatory':f['mandatory']=='YES'} for f,m,v in zip(fields,missing,invalid)],
            'timestamp_min':min(times),'timestamp_max':max(times),'negative_timestamps':sum(t<0 for t in times),
            'zero_timestamps':sum(t==0 for t in times),'positive_timestamps':sum(t>0 for t in times),
            'event_types':types,'semantic_field_violations':violations,
            'status':'accepted_serialization_only' if violations==0 else 'serialization_explained_semantic_issues_remain',
            'scope':'Supplement to strict raw audit. Does not approve replay, SQL-arrival mapping or resource imputation.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream: json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','schema','strict-audit','output'): parser.add_argument('--'+name,required=True)
    args=parser.parse_args();review(args.archive,args.schema,args.strict_audit,args.output)
