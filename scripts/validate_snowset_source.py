#!/usr/bin/env python3
"""Validate a complete recovered Snowset object; never accept partial arrivals."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import time


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def identity(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def quote_identifier(value):
    return '"' + value.replace('"', '""') + '"'


def validate(config_path, record_hash):
    cfg_path = Path(config_path).resolve()
    cfg = json.loads(cfg_path.read_text())
    if not isinstance(cfg['duckdb_threads'], int) or isinstance(cfg['duckdb_threads'], bool) or cfg['duckdb_threads'] <= 0:
        raise ValueError('Explicit positive thread limit required')
    if not isinstance(cfg['disk_reserve_bytes'], int) or isinstance(cfg['disk_reserve_bytes'], bool) or cfg['disk_reserve_bytes'] < 0:
        raise ValueError('Explicit nonnegative disk reserve required')
    if cfg['schema_version'] != 'snowset_full_source_validation_v1':
        raise ValueError('Unsupported source-validation protocol')
    source = (cfg_path.parent / cfg['source_directory']).resolve()
    acquisition = source / 'recovery_record.json'
    if sha256(acquisition) != record_hash:
        raise ValueError('Acquisition record changed or was not pinned')
    receipt = json.loads(acquisition.read_text())
    if receipt['status'] != 'downloaded_bytes_only':
        raise ValueError('Complete acquisition required before any dataset access')
    if sha256(source / 'recovery_code.py') != receipt['tool_sha256']:
        raise ValueError('Recovery producer source changed')
    source_cfg = receipt['source_configuration']
    filename = source_cfg['filename']
    if Path(filename).name != filename:
        raise ValueError('Unsafe object filename')
    archive = source / filename
    before = identity(archive)
    if before[2] != source_cfg['expected_bytes'] or receipt['verified_bytes'] != before[2]:
        raise ValueError('Full source length not verified')
    if sha256(archive) != receipt['sha256'] or identity(archive) != before:
        raise ValueError('Full source hash/custody mismatch')
    output = (cfg_path.parent / cfg['output_directory']).resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(cfg_path, output / 'validation_config.json')
    shutil.copy2(__file__, output / 'validation_code.py')
    shutil.copy2(acquisition, output / 'source_recovery_record.json')
    unpacked = output / 'extracted'
    unpacked.mkdir()
    started = time.monotonic()
    record = {'schema_version': 'snowset_source_validation_record_v1',
              'status': 'in_progress', 'started_at': datetime.now(timezone.utc).isoformat(),
              'archive_sha256': receipt['sha256'], 'acquisition_record_sha256': record_hash,
              'tool_sha256': sha256(__file__), 'configuration': cfg,
              'provenance_limitation': receipt.get('scope'), 'members': []}

    def save(stage):
        record['stage'] = stage
        record['elapsed_seconds'] = time.monotonic() - started
        write_json(output / 'validation_record.json', record)
        print(json.dumps({'stage': stage, 'elapsed_seconds': record['elapsed_seconds']}), flush=True)

    save('complete_object_hash_verified')
    connection = None
    try:
        # Manual exclusive extraction: no tar extraction API, links, special files,
        # absolute paths, parent traversal, or overwrite of existing artifacts.
        seen = set()
        with gzip.open(archive, 'rb') as compressed:
            with tarfile.open(fileobj=compressed, mode='r|') as tar:
                for member in tar:
                    relative = PurePosixPath(member.name)
                    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
                        raise ValueError('Unsafe archive member path')
                    if str(relative) in seen:
                        raise ValueError('Duplicate archive member')
                    seen.add(str(relative))
                    target = unpacked.joinpath(*relative.parts)
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    if not member.isfile():
                        raise ValueError('Links/special archive members are forbidden')
                    if shutil.disk_usage(output).free < member.size + cfg['disk_reserve_bytes']:
                        raise ValueError('Insufficient disk for complete extraction')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    count = 0
                    h = hashlib.sha256()
                    with tar.extractfile(member) as incoming, target.open('xb') as outgoing:
                        while chunk := incoming.read(1024 * 1024):
                            outgoing.write(chunk)
                            h.update(chunk)
                            count += len(chunk)
                        outgoing.flush()
                        os.fsync(outgoing.fileno())
                    if count != member.size:
                        raise ValueError('Truncated tar member')
                    record['members'].append({'path': str(relative), 'bytes': count, 'sha256': h.hexdigest()})
                    save('extracting_members')
            # tar ends at its trailer; drain gzip separately to force its CRC/length
            # check, including any trailing compressed stream. Keep bytes unchanged.
            while compressed.read(1024 * 1024):
                pass
        if identity(archive) != before or sha256(acquisition) != record_hash:
            raise ValueError('Source custody changed during extraction')
        record['gzip_crc_and_tar_read_passed'] = True
        save('archive_integrity_verified')
        parquet = sorted(unpacked.rglob('*.parquet'))
        if not parquet:
            raise ValueError('No Parquet members found; inspect actual archive')
        import duckdb
        connection = duckdb.connect()
        connection.execute('SET memory_limit = ?', [cfg['duckdb_memory_limit']])
        connection.execute('SET threads = ?', [cfg['duckdb_threads']])
        scratch = output / 'duckdb_scratch'
        scratch.mkdir()
        connection.execute('SET temp_directory = ?', [str(scratch)])
        record['duckdb_version'] = duckdb.__version__
        schemas = []
        for p in parquet:
            schema = connection.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(p)]).fetchall()
            schemas.append([(row[0], row[1]) for row in schema])
        if any(s != schemas[0] for s in schemas):
            raise ValueError('Inconsistent member schemas; no union-by-name fallback')
        schema = schemas[0]
        record['parquet_schema'] = schema
        types = dict(schema)
        for name in ('queryId', 'warehouseId'):
            if types.get(name) != 'BIGINT':
                raise ValueError('Required integer identity field missing/wrong type: ' + name)
        if not types.get('createdTime', '').startswith('TIMESTAMP'):
            raise ValueError('Required native arrival timestamp missing/wrong type')
        connection.read_parquet([str(p) for p in parquet]).create_view('source')
        save('parquet_schema_verified')
        columns = [quote_identifier(name) for name, _ in schema]
        # hash(all columns) requires actual value decoding across the complete corpus,
        # rather than treating a footer row count as successful full Parquet reading.
        expressions = ['count(*)', 'sum(hash(' + ','.join(columns) + '))::VARCHAR']
        expressions += ['count(*) - count(' + col + ')' for col in columns]
        values = connection.execute('SELECT ' + ','.join(expressions) + ' FROM source').fetchone()
        record['rows'] = values[0]
        record['decoded_value_hash_sum_diagnostic'] = values[1]
        record['null_counts'] = dict(zip([name for name, _ in schema], values[2:]))
        if not values[0] or any(record['null_counts'][n] for n in ('queryId', 'warehouseId', 'createdTime')):
            raise ValueError('Empty corpus or missing required identity/arrival values; no imputation')
        save('all_parquet_values_decoded')
        unique, low, high, warehouses = connection.execute('SELECT count(DISTINCT "queryId"), min("createdTime"), max("createdTime"), count(DISTINCT "warehouseId") FROM source').fetchone()
        record.update(unique_query_ids=unique, arrival_min_utc=low, arrival_max_utc=high, warehouses=warehouses)
        if unique != record['rows'] or low >= high:
            raise ValueError('Duplicate query IDs or unusable arrival-time coverage')
        # Observed full-corpus inventory only: this does not select a warehouse,
        # tune a forecast, normalize demand, assign SQL, or define test windows.
        connection.execute('COPY (SELECT "warehouseId", count(*) AS queries, min("createdTime") AS first_arrival_utc, max("createdTime") AS last_arrival_utc FROM source GROUP BY "warehouseId" ORDER BY "warehouseId") TO ? (HEADER, DELIMITER ",")', [str(output / 'warehouse_inventory.csv')])
        record['warehouse_inventory_sha256'] = sha256(output / 'warehouse_inventory.csv')
        record['extracted_files_unchanged'] = all(sha256(unpacked / m['path']) == m['sha256'] for m in record['members'])
        if not record['extracted_files_unchanged'] or identity(archive) != before:
            raise ValueError('Source/extracted contents changed during full inspection')
        record.update(status='validated_arrival_source_only', ended_at=datetime.now(timezone.utc).isoformat(),
                      scope='Complete archive, full Parquet decoding, arrival/identity inventory. No SQL text or query mapping; no replay/forecast/model/publication acceptance. Publisher cryptographic authenticity is not independently established; recovered original-range receipt limitation retained.')
        save('validated_arrival_source_only')
    except Exception as exc:
        record.update(status='failed_preserved_artifacts', error=str(exc), ended_at=datetime.now(timezone.utc).isoformat())
        save('failed')
        raise
    finally:
        if connection is not None:
            connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--acquisition-record-sha256', required=True)
    args = parser.parse_args()
    validate(args.config, args.acquisition_record_sha256)
