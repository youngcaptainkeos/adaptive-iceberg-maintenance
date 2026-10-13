#!/usr/bin/env python3
"""Extract actual arrivals with training-only cohort selection, no SQL mapping."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import shutil
import time


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def extract(config_path, validation_hash):
    path = Path(config_path).resolve()
    cfg = json.loads(path.read_text())
    if cfg['schema_version'] != 'snowset_training_only_arrival_cohort_v1':
        raise ValueError('Unsupported cohort protocol')
    for name in ('training_seconds', 'calibration_seconds', 'bin_seconds', 'duckdb_threads'):
        if not isinstance(cfg[name], int) or isinstance(cfg[name], bool) or cfg[name] <= 0:
            raise ValueError('Explicit positive integer required: ' + name)
    if cfg['selection_rule'] != 'maximum_training_arrivals_then_numeric_warehouse_id':
        raise ValueError('No full-corpus or outcome-based warehouse selection')
    source = (path.parent / cfg['source_validation_directory']).resolve()
    receipt = source / 'validation_record.json'
    if digest(receipt) != validation_hash:
        raise ValueError('Source validation record changed')
    record = json.loads(receipt.read_text())
    if record['status'] != 'validated_arrival_source_only' or not record['gzip_crc_and_tar_read_passed'] or not record['extracted_files_unchanged']:
        raise ValueError('Complete validated arrival source required')
    if digest(source / 'validation_code.py') != record['tool_sha256']:
        raise ValueError('Source validation producer changed')
    files, identities = [], {}
    for member in record['members']:
        p = (source / 'extracted' / member['path']).resolve()
        if not p.is_relative_to((source / 'extracted').resolve()) or not p.is_file():
            raise ValueError('Unsafe or missing actual source member')
        if p.stat().st_size != member['bytes'] or digest(p) != member['sha256']:
            raise ValueError('Validated source member changed')
        s = p.stat()
        identities[p] = (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        if p.suffix == '.parquet':
            files.append(str(p))
    if len(files) != record['parquet_regular_file_count']:
        raise ValueError('Regular-file inventory differs from accepted source')
    origin = datetime.fromisoformat(record['arrival_min_utc']).replace(tzinfo=timezone.utc)
    last = datetime.fromisoformat(record['arrival_max_utc']).replace(tzinfo=timezone.utc)
    train_end = origin + timedelta(seconds=cfg['training_seconds'])
    calibration_end = train_end + timedelta(seconds=cfg['calibration_seconds'])
    complete_bins = (last - origin) // timedelta(seconds=cfg['bin_seconds'])
    end = origin + timedelta(seconds=complete_bins * cfg['bin_seconds'])
    if calibration_end >= end or cfg['training_seconds'] % cfg['bin_seconds'] or cfg['calibration_seconds'] % cfg['bin_seconds']:
        raise ValueError('Source does not support three nonempty chronological complete-bin segments')
    output = (path.parent / cfg['output_directory']).resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(path, output / 'cohort_config.json')
    shutil.copy2(__file__, output / 'cohort_code.py')
    shutil.copy2(receipt, output / 'source_validation_record.json')
    result = {'schema_version': 'snowset_arrival_cohort_record_v1', 'status': 'in_progress',
              'started_at': datetime.now(timezone.utc).isoformat(), 'configuration': cfg,
              'source_validation_sha256': validation_hash, 'tool_sha256': digest(Path(__file__)),
              'observation_origin_utc': origin.isoformat(), 'training_end_utc': train_end.isoformat(),
              'calibration_end_utc': calibration_end.isoformat(), 'complete_bin_end_utc': end.isoformat(),
              'source_last_arrival_utc': last.isoformat(), 'complete_bins': complete_bins}
    def save():
        temporary = output / 'cohort_record.tmp'
        temporary.write_text(json.dumps(result, indent=2, default=str) + '\n')
        temporary.replace(output / 'cohort_record.json')
    save()
    import duckdb
    c = duckdb.connect()
    try:
        c.execute('SET memory_limit = ?', [cfg['duckdb_memory_limit']])
        c.execute('SET threads = ?', [cfg['duckdb_threads']])
        c.execute("SET TimeZone = 'UTC'")
        scratch = output / 'duckdb_scratch'
        scratch.mkdir()
        c.execute('SET temp_directory = ?', [str(scratch)])
        c.read_parquet(files).create_view('source')
        # Selection reads only training arrivals; no global warehouse inventory,
        # completed-query metrics, calibration/test volume or outcomes are used.
        chosen = c.execute('SELECT "warehouseId", count(*) AS n FROM source WHERE "createdTime" >= ? AND "createdTime" < ? GROUP BY "warehouseId" ORDER BY n DESC, "warehouseId" ASC LIMIT 1', [origin.replace(tzinfo=None), train_end.replace(tzinfo=None)]).fetchone()
        if chosen is None:
            raise ValueError('No training arrivals')
        warehouse, count = chosen
        result.update(selected_warehouse_id=warehouse, selected_training_arrivals=count, duckdb_version=duckdb.__version__)
        save()
        c.execute('CREATE TABLE selected AS SELECT "queryId", "warehouseId", "createdTime" FROM source WHERE "warehouseId" = ?', [warehouse])
        queries, unique = c.execute('SELECT count(*), count(DISTINCT "queryId") FROM selected').fetchone()
        if queries != unique:
            raise ValueError('Selected identities not unique')
        c.execute('COPY (SELECT "queryId", "warehouseId", strftime("createdTime", \'%Y-%m-%dT%H:%M:%S.%fZ\') AS arrival_utc FROM selected ORDER BY "createdTime", "queryId") TO ? (HEADER, DELIMITER ",")', [str(output / 'observed_arrivals.csv')])
        # Empty bins count absence of reported arrivals inside the complete source
        # interval; they are not invented events or a claim that the server was idle.
        c.execute('CREATE TABLE counted AS SELECT ((epoch_us("createdTime") - epoch_us(?::TIMESTAMP)) // (? * 1000000))::BIGINT AS bin_id, count(*) AS arrivals FROM selected WHERE "createdTime" >= ? AND "createdTime" < ? GROUP BY bin_id', [origin.replace(tzinfo=None), cfg['bin_seconds'], origin.replace(tzinfo=None), end.replace(tzinfo=None)])
        c.execute('CREATE TABLE bins AS SELECT b.range AS bin_id, b.range * ? AS elapsed_seconds, coalesce(n.arrivals,0) AS observed_arrivals FROM range(?) b LEFT JOIN counted n ON b.range=n.bin_id', [cfg['bin_seconds'], complete_bins])
        c.execute('COPY (SELECT * FROM bins ORDER BY bin_id) TO ? (HEADER, DELIMITER ",")', [str(output / 'observed_bin_counts.csv')])
        binned = c.execute('SELECT coalesce(sum(arrivals),0) FROM counted').fetchone()[0]
        tails = c.execute('SELECT count(*) FROM selected WHERE "createdTime" >= ?', [end.replace(tzinfo=None)]).fetchone()[0]
        if binned + tails != queries or digest(receipt) != validation_hash:
            raise ValueError('Arrival conservation/source custody failed')
        for p, before in identities.items():
            s = p.stat()
            if (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns) != before:
                raise ValueError('Source member identity changed during extraction')
        result.update(status='extracted_arrival_cohort_only', selected_total_arrivals=queries,
                      complete_bin_arrivals=binned, excluded_partial_tail_arrivals=tails,
                      observed_arrivals_sha256=digest(output / 'observed_arrivals.csv'),
                      observed_bin_counts_sha256=digest(output / 'observed_bin_counts.csv'),
                      ended_at=datetime.now(timezone.utc).isoformat(),
                      scope='Original timestamps/identities preserved, one training-selected warehouse and complete-window counts. No SQL mapping, load scaling, normalization, forecasting, physical replay or model promotion. Empty bins mean no reported queries in the provided corpus, not verified idle time.')
        print(json.dumps(result, default=str))
    except Exception as exc:
        result.update(status='failed_preserved_artifacts', error=str(exc))
        raise
    finally:
        save()
        c.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--source-validation-sha256', required=True)
    args = parser.parse_args()
    extract(args.config, args.source_validation_sha256)
