#!/usr/bin/env python3
"""Read-only full-field TPC-H parsing audit; no table writes or provenance invention."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned(spec, base):
    path = (base / spec['path']).resolve()
    if not path.is_file() or digest(path) != spec['sha256']:
        raise ValueError('Pinned small provenance artifact differs: ' + str(path))
    return path


def audit(config_path, output_directory, expected_revision):
    config_path = Path(config_path).resolve()
    cfg = json.loads(config_path.read_text())
    repo = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    if revision != expected_revision or cfg['schema_version'] != 'tpch_typed_source_audit_v1':
        raise ValueError('Full revision/protocol mismatch')
    if subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', 'scripts/audit_tpch_typed_source.py'], cwd=repo, capture_output=True).returncode:
        raise ValueError('Dirty validator')
    inventory_path = pinned(cfg['source_inventory'], config_path.parent)
    pinned(cfg['schema_origin'], config_path.parent)
    inventory = json.loads(inventory_path.read_text())
    tables = {r['table']: r for r in inventory['tables']}
    if set(cfg['table_order']) != set(tables) or len(cfg['table_order']) != len(tables) or set(cfg['schemas']) != set(tables):
        raise ValueError('Incomplete or duplicate table registration')
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(config_path, output / 'config.json')
    shutil.copy2(inventory_path, output / 'source_inventory.json')
    shutil.copy2(__file__, output / 'audit_code.py')
    import duckdb
    connection = duckdb.connect()
    connection.execute('SET threads = ' + str(int(cfg['threads'])))
    connection.execute('SET memory_limit = ' + repr(cfg['memory_limit']))
    deadline = datetime.fromisoformat(cfg['no_new_scan_after_utc'])
    record = {'schema_version': cfg['schema_version'], 'host': socket.gethostname(),
              'code_revision': revision, 'code_sha256': digest(__file__),
              'duckdb_version': duckdb.__version__, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'running', 'tables': [], 'limitations': [
                  'Prior full-byte source SHA256 is reused with exact size/mtime matching; no fresh source digest claimed.',
                  'Typed and lexical field validation only; no PK/FK relational integrity, generator authenticity or Iceberg readability certified.',
                  'Declared schema comes from the existing loader; no engine query or training data is produced.']}
    with (output / 'events.jsonl').open('x') as stream:
        def emit(kind, **values):
            stream.write(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), 'kind': kind, **values}) + '\n')
            stream.flush()
        try:
            for name in cfg['table_order']:
                if datetime.now(timezone.utc) >= deadline:
                    record['status'] = 'partial_cutoff_no_new_scan'
                    emit('cutoff', next_table=name)
                    break
                item = tables[name]
                path = Path(item['path'])
                before = path.stat()
                if (before.st_size, before.st_mtime_ns) != (item['bytes'], item['mtime_ns']):
                    raise ValueError('Source differs from prior full hash inventory: ' + name)
                fields = cfg['schemas'][name]
                columns = {f['name']: 'VARCHAR' for f in fields}
                columns['_trailing_empty'] = 'VARCHAR'
                expressions = ['count(*) AS row_count', 'count(_trailing_empty) AS nonempty_terminators']
                for field in fields:
                    column, dtype = field['name'], field['type']
                    if not re.fullmatch(r'[A-Z][A-Z0-9_]+', column) or not re.fullmatch(r'VARCHAR|INTEGER|BIGINT|DATE|DECIMAL\(15,2\)', dtype):
                        raise ValueError('Unreviewed schema')
                    bad = f'{column} IS NULL'
                    if dtype != 'VARCHAR':
                        pattern = r'[+-]?[0-9]+' if dtype in ('INTEGER', 'BIGINT') else (r'[0-9]{4}-[0-9]{2}-[0-9]{2}' if dtype == 'DATE' else r'[+-]?[0-9]+(\.[0-9]{1,2})?')
                        pattern_sql = "'" + pattern.replace("'", "''") + "'"
                        bad += f' OR NOT regexp_full_match({column}, {pattern_sql}) OR TRY_CAST({column} AS {dtype}) IS NULL'
                    expressions.append(f'count(*) FILTER (WHERE {bad}) AS invalid_{column}')
                # Single parameter is the actual file. All columns participate in
                # aggregates, preventing pruning of an unvalidated field.
                sql = 'SELECT ' + ', '.join(expressions) + ' FROM read_csv(?, delim=\'|\', header=false, auto_detect=false, columns=' + repr(columns) + ', quote=\'\', escape=\'\', strict_mode=true, ignore_errors=false)'
                emit('scan_started', table=name, source=str(path), prior_sha256=item['sha256'], sql=sql)
                if datetime.now(timezone.utc) >= deadline:
                    record['status'] = 'partial_cutoff_no_new_scan'
                    emit('cutoff', next_table=name)
                    break
                started = time.monotonic()
                values = connection.execute(sql, [str(path)]).fetchone()
                after = path.stat()
                if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                    raise ValueError('Source changed during typed scan: ' + name)
                outcome = dict(zip([d[0] for d in connection.description], values))
                actual = {'table': name, 'prior_sha256': item['sha256'], 'size': after.st_size,
                          'mtime_ns': after.st_mtime_ns, 'elapsed_seconds': time.monotonic() - started, **outcome}
                record['tables'].append(actual)
                emit('scan_completed', **actual)
                if outcome['row_count'] != item['rows'] or any(v != 0 for k, v in outcome.items() if k != 'row_count'):
                    raise ValueError('Actual typed/lexical/cardinality gate failed: ' + name)
            else:
                record['status'] = 'passed_all_registered_typed_fields_only'
        except Exception as exc:
            record['status'] = 'failed_preserved'
            record['error'] = str(exc)
            emit('audit_failed', error_type=type(exc).__name__, error=str(exc))
            raise
        finally:
            record['ended_utc'] = datetime.now(timezone.utc).isoformat()
            with (output / 'result.json').open('x') as result:
                json.dump(record, result, indent=2)
                result.write('\n')
            connection.close()
    print(json.dumps(record))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-directory', required=True)
    parser.add_argument('--expected-revision', required=True)
    args = parser.parse_args()
    audit(args.config, args.output_directory, args.expected_revision)
