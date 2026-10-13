#!/usr/bin/env python3
"""Independently reconstruct bins from complete original UTC arrival exports."""
import argparse
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024*1024):
            h.update(chunk)
    return h.hexdigest()


def audit(directory, expected_record_hash):
    root = Path(directory).resolve()
    receipt = root/'cohort_record.json'
    if digest(receipt) != expected_record_hash:
        raise ValueError('Cohort record not pinned/changed')
    r = json.loads(receipt.read_text())
    if r['status'] != 'extracted_arrival_cohort_only':
        raise ValueError('Complete cohort required')
    cfg = r['configuration']
    if cfg['selection_rule'] != 'maximum_training_arrivals_then_numeric_warehouse_id':
        raise ValueError('Unreviewed cohort selection')
    if json.loads((root/'cohort_config.json').read_text()) != cfg or digest(root/'cohort_code.py') != r['tool_sha256']:
        raise ValueError('Frozen producer/config changed')
    source = root/'source_validation_record.json'
    if digest(source) != r['source_validation_sha256'] or json.loads(source.read_text())['status'] != 'validated_arrival_source_only':
        raise ValueError('Validated-source provenance missing/changed')
    arrivals, bins = root/'observed_arrivals.csv', root/'observed_bin_counts.csv'
    if digest(arrivals) != r['observed_arrivals_sha256'] or digest(bins) != r['observed_bin_counts_sha256']:
        raise ValueError('Export bytes differ from complete cohort')
    def utc(value):
        dt = datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.utcoffset() != timedelta(0):
            raise ValueError('Original UTC timestamp required')
        return dt
    origin, end, last, train_end = (utc(r[k]) for k in ('observation_origin_utc','complete_bin_end_utc','source_last_arrival_utc','training_end_utc'))
    expected_bins = (last-origin)//timedelta(seconds=cfg['bin_seconds'])
    if expected_bins != r['complete_bins'] or end != origin+timedelta(seconds=expected_bins*cfg['bin_seconds']):
        raise ValueError('Invented/partial time extent')
    if train_end != origin+timedelta(seconds=cfg['training_seconds']) or utc(r['calibration_end_utc']) != train_end+timedelta(seconds=cfg['calibration_seconds']):
        raise ValueError('Changed chronology')
    counts = [0]*expected_bins
    identities = set()
    total = training = tail = 0
    previous = None
    with arrivals.open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['queryId','warehouseId','arrival_utc']:
            raise ValueError('Unexpected original-arrival schema')
        for row in reader:
            query, warehouse = int(row['queryId']), int(row['warehouseId'])
            when = utc(row['arrival_utc'])
            if warehouse != r['selected_warehouse_id'] or query in identities or not origin <= when <= last:
                raise ValueError('Identity/source-time conservation failed')
            key = (when,query)
            if previous is not None and key < previous:
                raise ValueError('Original timestamp/ID order broken')
            previous = key
            identities.add(query)
            total += 1
            training += when < train_end
            if when >= end:
                tail += 1
            else:
                delta = when-origin
                # Exact integer microseconds: no float clock/rounding/clipping.
                offset_us = delta.days*86400*1000000+delta.seconds*1000000+delta.microseconds
                counts[offset_us//(cfg['bin_seconds']*1000000)] += 1
    with bins.open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['bin_id','elapsed_seconds','observed_arrivals']:
            raise ValueError('Unexpected count-bin schema')
        rows = 0
        for rows, row in enumerate(reader,1):
            index = rows-1
            if index >= expected_bins or int(row['bin_id']) != index or int(row['elapsed_seconds']) != index*cfg['bin_seconds'] or int(row['observed_arrivals']) != counts[index]:
                raise ValueError('Count bin differs from original UTC arrivals')
        if rows != expected_bins:
            raise ValueError('Missing/extra bins')
    if total != r['selected_total_arrivals'] or training != r['selected_training_arrivals'] or tail != r['excluded_partial_tail_arrivals'] or sum(counts) != r['complete_bin_arrivals'] or sum(counts)+tail != total:
        raise ValueError('Published counts differ from independent reconstruction')
    if digest(receipt) != expected_record_hash or digest(arrivals) != r['observed_arrivals_sha256'] or digest(bins) != r['observed_bin_counts_sha256']:
        raise ValueError('Artifacts changed during audit')
    return {'schema_version':'independent_original_arrival_bin_audit_v1','status':'passed_arrival_export_integrity',
            'cohort_record_sha256':expected_record_hash,'observed_arrivals_sha256':r['observed_arrivals_sha256'],
            'observed_bin_counts_sha256':r['observed_bin_counts_sha256'],'unique_arrivals':total,
            'training_arrivals':training,'complete_bins':expected_bins,'complete_bin_arrivals':sum(counts),
            'partial_tail_arrivals':tail,'zero_reported_arrival_bins':sum(x==0 for x in counts),
            'scope':'Python CSV/datetime/integer reconstruction independent of DuckDB binning. Exact identities/order/bins/counts/chronology/provenance verified; not proof of server idle/logging completeness, SQL mapping, forecasting or physical scheduling.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True)
    parser.add_argument('--cohort-record-sha256',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=audit(args.directory,args.cohort_record_sha256)
    with Path(args.output).open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result))
