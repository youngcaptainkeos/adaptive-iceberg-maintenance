#!/usr/bin/env python3
"""Counterbalanced durable writes of actual historical bytes; no SQL or labels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.core.common import checked, require, sha, now, write_json


def run(protocol):
    cfg = json.loads(Path(protocol).read_text())
    out = Path(cfg['output_directory'])
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'started_utc': now(), 'code_sha256': sha(__file__),
              'protocol_sha256': sha(protocol), 'new_SQL_operations': 0,
              'training_labels_created': False, 'physical_speedup_established': False}
    try:
        require(cfg['schema_version'] == 'real_byte_storage_probe_v1' and sha(__file__) == cfg['code_sha256'], 'Changed storage probe')
        raw = checked(cfg['source_events'])
        groups = {}
        for line in raw.open('rb'):
            relevant = any(('"kind": "'+k+'"').encode() in line for k in ['query_observation', 'cohort_queue_transition', 'statement_requested'])
            if not relevant:
                continue
            r = json.loads(line)
            kind = r['kind']
            selected = kind == 'query_observation' or (kind == 'cohort_queue_transition' and r['state'] == 'dispatched') or (kind == 'statement_requested' and r['role'] == 'trace_query')
            if not selected:
                continue
            mid = r['measurement_id']
            groups.setdefault(mid, []).append((kind, line))
            if kind == 'statement_requested' and len(groups) == cfg['source_group_count']:
                break
        require(len(groups) == cfg['source_group_count'], 'Insufficient real source triples')
        require(all([k for k,b in values] == ['query_observation','cohort_queue_transition','statement_requested'] for values in groups.values()), 'Wrong original submission record sequence')
        require(cfg['source_group_count'] > 0 and cfg['source_group_count'] % 2 == 0, 'Even registered source group count required')
        files, streams, mounts = {}, {}, {}
        for name, location in cfg['locations'].items():
            directory = Path(location)
            directory.mkdir(parents=True, exist_ok=False)
            mounts[name] = subprocess.check_output(['findmnt','-J','-T',str(directory),'-o','TARGET,FSTYPE,SOURCE'],text=True)
            files[name] = directory/'historical_source_bytes.replay_only'
            streams[name] = files[name].open('xb')
        require(set(files) == {'evidence_disk','system_disk'}, 'Wrong compared locations')
        require(os.stat(files['evidence_disk']).st_dev != os.stat(files['system_disk']).st_dev, 'Compared locations are not distinct devices')
        rows = []
        try:
            for index, (mid, records) in enumerate(groups.items()):
                order = ['evidence_disk','system_disk'] if index < len(groups)//2 else ['system_disk','evidence_disk']
                for location in order:
                    began = time.monotonic_ns()
                    for kind, encoded in records:
                        streams[location].write(encoded)
                        streams[location].flush()
                        os.fsync(streams[location].fileno())
                    ended = time.monotonic_ns()
                    rows.append({'source_measurement_id':mid,'source_group_index':index,'location':location,
                                 'first_in_pair':location == order[0], 'record_count':len(records),
                                 'bytes':sum(len(b) for k,b in records),'elapsed_ms':(ended-began)/1e6})
        finally:
            for stream in streams.values(): stream.close()
        expected = b''.join(encoded for values in groups.values() for kind,encoded in values)
        for name, path in files.items():
            require(path.read_bytes() == expected, 'Replayed original bytes differ after durable writes '+name)
        require(sha(raw) == cfg['source_events']['sha256'], 'Original evidence changed during diagnostic')
        summaries = {}
        for name in files:
            values = [r['elapsed_ms'] for r in rows if r['location'] == name]
            summaries[name] = {'groups':len(values),'median_three_record_ms':statistics.median(values),
                               'mean_three_record_ms':statistics.mean(values),'total_measured_seconds':sum(values)/1000}
        report.update(status='passed_real_byte_durable_storage_comparison', source_events_sha256=sha(raw),
                      output_replay_sha256=hashlib.sha256(expected).hexdigest(),replayed_original_records=len(groups)*3,
                      measured_groups=rows, summaries=summaries, actual_mounts=mounts,
                      replay_files={name:str(path) for name,path in files.items()},
                      limitations=['Actual historical bytes replayed for filesystem I/O only; copied event timestamps are not new query measurements or training data.',
                                   'Three flush+fsync operations per source group on both disks; no durability batching or gate relaxation.',
                                   'Bytes pre-encoded, so timing excludes JSON encoding, real SQL, live telemetry, publication receipts and archive traversal.',
                                   'Two counterbalanced blocks in one session, not independent server/workload replication; storage/cache contention is not isolated.',
                                   'No active experiment is relocated by this probe. Local storage retention, backup and failure recovery need a separate contract before physical use.'])
    except Exception as exc:
        report.update(status='failed_preserved',error=str(exc))
        raise
    finally:
        report['ended_utc'] = now()
        write_json(out/'result.json',report)
        print(json.dumps(report),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', required=True)
    run(parser.parse_args().protocol)
