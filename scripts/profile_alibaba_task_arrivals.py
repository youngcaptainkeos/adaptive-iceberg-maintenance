#!/usr/bin/env python3
"""Preserve reported positive task-creation events; no SQL mapping or invented arrivals."""
import argparse
from collections import Counter
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import tarfile


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024): h.update(chunk)
    return h.hexdigest()


def profile(archive,audit_path,output):
    audit=json.loads(Path(audit_path).read_text());archive=Path(archive);output=Path(output)
    if digest(archive)!=audit['archive_sha256']: raise ValueError('Archive checksum mismatch')
    member_info=next(m for m in audit['members'] if m['name'].endswith('/batch_task.csv'))
    # Selected event fields must be complete and type-valid; CPU/memory are not used.
    for field in member_info['columns'][:4]:
        if field['missing'] or field['invalid_numeric'] or field['nonfinite']: raise ValueError('Invalid event identity/time field')
    output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,output/'transformation_code.py')
    events=[];excluded=Counter();keys=set();member_hash=hashlib.sha256();bytes_read=0;total=0
    with tarfile.open(archive,'r|gz') as tar:
        for member in tar:
            if member.name!=member_info['name']: continue
            with tar.extractfile(member) as raw:
                def lines():
                    nonlocal bytes_read
                    for line in raw:
                        member_hash.update(line);bytes_read+=len(line);yield line.decode('utf-8')
                for source_row,row in enumerate(csv.reader(lines()),start=1):
                    if len(row)!=8: raise ValueError('Unexpected task field count')
                    total+=1;timestamp,job,task=int(row[0]),int(row[2]),int(row[3])
                    key=(job,task)
                    if key in keys: raise ValueError('Ambiguous duplicate task identity')
                    keys.add(key)
                    if timestamp<=0:
                        excluded['negative_pretrace' if timestamp<0 else 'zero_pretrace']+=1;continue
                    events.append((timestamp,job,task,source_row))
            break
    if total!=member_info['rows'] or bytes_read!=member_info['bytes'] or member_hash.hexdigest()!=member_info['sha256']:
        raise ValueError('Incomplete task member')
    if digest(archive)!=audit['archive_sha256']: raise ValueError('Archive changed')
    events.sort();csv_path=output/'reported_task_creations.csv'
    with csv_path.open('x',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['source_timestamp_s','job_id','task_id','source_row_number']);writer.writerows(events)
    counts=Counter(e[0] for e in events);times=sorted(counts)
    gaps=[(b-a,a,b) for a,b in zip(times,times[1:])]
    report={'schema_version':'reported_task_creation_profile_v1','checked_at':datetime.now(timezone.utc).isoformat(),
            'archive_sha256':audit['archive_sha256'],'member_sha256':member_info['sha256'],
            'strict_audit_sha256':digest(audit_path),'transformation_code_sha256':digest(__file__),
            'event_csv_sha256':digest(csv_path),'source_rows':total,'positive_creation_events':len(events),
            'excluded_censored_events':dict(excluded),'first_positive_timestamp_s':times[0],
            'last_positive_timestamp_s':times[-1],'distinct_event_seconds':len(times),
            'maximum_reported_events_in_one_second':max(counts.values()),
            'largest_between_event_gaps':[{'seconds':gap,'previous_event_s':a,'next_event_s':b} for gap,a,b in sorted(gaps,reverse=True)[:10]],
            'time_mapping':'Original relative timestamps retained; sorted only, no compression, repetition, interpolation or padding',
            'scope':'Reported cluster-task creations only; candidate for reviewed mapping, not SQL arrivals or executable trace manifest',
            'limitations':['Creation times are reported in a final task table, not a complete database submission log',
                           'No claim of observation coverage after last event or inside event-free gaps',
                           'CPU/memory plans and final task status omitted; missing resources not imputed and future outcome not used',
                           'No SQL text/query mix/ingestion demand or single-server scaling established',
                           'No inferred arrivals at time zero for negative/censored timestamps']}
    with (output/'profile.json').open('x') as stream: json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','audit','output'): parser.add_argument('--'+name,required=True)
    args=parser.parse_args();profile(args.archive,args.audit,args.output)
