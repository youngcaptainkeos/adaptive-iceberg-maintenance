#!/usr/bin/env python3
"""Create a new SF1 correctness table from verified source; never reset old tables."""
import argparse
import fcntl
import json
from pathlib import Path
import re
import shutil
import subprocess

from experiment_validation import load_json, require, verified_file, sha256
from physical_measurements import EventLog, StatementRecorder, SparkEvidence

# Physical TPC-H lineitem schema, matching existing loader and generator specification.
LINEITEM = [('L_ORDERKEY','BIGINT'),('L_PARTKEY','INT'),('L_SUPPKEY','INT'),
            ('L_LINENUMBER','INT'),('L_QUANTITY','DECIMAL(15,2)'),
            ('L_EXTENDEDPRICE','DECIMAL(15,2)'),('L_DISCOUNT','DECIMAL(15,2)'),
            ('L_TAX','DECIMAL(15,2)'),('L_RETURNFLAG','STRING'),('L_LINESTATUS','STRING'),
            ('L_SHIPDATE','DATE'),('L_COMMITDATE','DATE'),('L_RECEIPTDATE','DATE'),
            ('L_SHIPINSTRUCT','STRING'),('L_SHIPMODE','STRING'),('L_COMMENT','STRING')]


def prepare(config_path, expected_revision):
    config, base = load_json(config_path)
    require(config.get('schema_version') == 'sf1_correctness_preparation_v1', 'Unsupported preparation schema')
    require(config.get('purpose') == 'physical_correctness_only', 'Preparation cannot authorize publication evaluation')
    require(bool(config.get('configuration_rationale')), 'Rationale required')
    repo = Path(__file__).resolve().parents[2]
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    require(revision == expected_revision, 'Revision mismatch')
    dirty = subprocess.run(['git','diff','--exit-code','HEAD','--','scripts/phase6-live-evaluation/*.py'],cwd=repo,capture_output=True)
    require(dirty.returncode == 0, 'Experiment Python differs from pinned HEAD')
    # Host-local advisory lock held for entire operation. No process is killed.
    lock = (repo / 'results' / '.physical_correctness.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    source = verified_file(config['source'],base)
    provenance = verified_file(config['generator_provenance'],base)
    require(source.name == 'lineitem.tbl', 'Only the reviewed lineitem schema is supported')
    expected_rows = config['expected_rows']
    require(isinstance(expected_rows,int) and not isinstance(expected_rows,bool) and expected_rows > 0, 'Expected rows required')
    count = 0
    with source.open('rb') as stream:
        for line in stream:
            require(line.endswith(b'|\n') and line.count(b'|') == len(LINEITEM), 'Invalid TPC-H line shape')
            count += 1
    require(count == expected_rows, 'Source row count mismatch')
    table = config['destination_table']
    require(re.fullmatch(r'local\.experiment\.integrity_sf1_[a-z0-9_]+',table), 'Destination must be a new integrity table')
    engine = config['engine']
    require(engine['host']=='127.0.0.1' and engine['username']=='ccbd', 'Reviewed engine must be local worker3 Thrift')
    require(isinstance(engine['port'],int) and 0 < engine['port'] < 65536, 'Invalid port')
    require(re.fullmatch(r'\d+\.\d+\.\d+',engine['expected_version']), 'Exact engine release required')
    # Paths used as SQL strings must contain no quotes, escapes or newlines.
    require(not any(c in str(source) for c in "'\\\n\r"), 'Unsupported source path')
    run_dir = (base/config['output_directory']).resolve()
    run_dir.mkdir(parents=True,exist_ok=False)
    shutil.copy2(config_path,run_dir/'preparation_config.json')
    code = run_dir/'code'
    code.mkdir()
    for name in ('prepare_correctness_table.py','physical_measurements.py','experiment_validation.py'):
        shutil.copy2(Path(__file__).parent/name,code/name)
    log = EventLog(run_dir/'events.jsonl',config['experiment_id'])
    log.emit('preparation_protocol',config=config,code_revision=revision,source_rows=count,
             source_sha256=sha256(source),generator_provenance_sha256=sha256(provenance),
             source_code_sha256={p.name:sha256(p) for p in code.iterdir()})
    from pyhive import hive
    conn = hive.Connection(host=engine['host'],port=engine['port'],username=engine['username'])
    cursor = conn.cursor()
    rec = StatementRecorder(log)
    rest = SparkEvidence(config['spark_rest_url'],config['spark_app_id'],config['rest_timeout_seconds'],log)
    def execute(sql, role='preparation'):
        result=rec.execute(cursor,sql,role=role)
        rest.capture('jobs')
        return result['rows']
    try:
        version=execute('SELECT version()','read_only_preflight')[0][0]
        require(version.split()[0]==engine['expected_version'], 'Engine version mismatch')
        rest.capture('environment')
        tables=execute('SHOW TABLES IN local.experiment','read_only_preflight')
        require(not any(row[1]==table.split('.')[-1] for row in tables), 'Destination already exists; no overwrite allowed')
        execute('SET spark.sql.ansi.enabled=true')
        # Force validation to parse every column (CSV column pruning changes error detection).
        execute('SET spark.sql.csv.parser.columnPruning.enabled=false')
        schema=', '.join(f'{name} {kind}' for name,kind in LINEITEM)+', _trailing STRING'
        execute(f"CREATE TEMPORARY VIEW integrity_source ({schema}) USING csv OPTIONS (path '{source.as_uri()}', sep '|', header 'false', quote '', mode 'FAILFAST', dateFormat 'yyyy-MM-dd')")
        invalid=' OR '.join(f'{name} IS NULL' for name,_ in LINEITEM)
        checks=execute(f'SELECT count(*), sum(CASE WHEN {invalid} OR (_trailing IS NOT NULL AND _trailing <> \'\') THEN 1 ELSE 0 END) FROM integrity_source')
        require(tuple(checks[0])==(expected_rows,0), 'Parsed source row/null/trailing-field validation failed')
        columns=', '.join(name for name,_ in LINEITEM)
        execute(f'CREATE TABLE {table} USING iceberg AS SELECT {columns} FROM integrity_source')
        loaded=execute(f'SELECT count(*), sum(CASE WHEN {invalid} THEN 1 ELSE 0 END) FROM {table}')
        require(tuple(loaded[0])==(expected_rows,0), 'Loaded row/null validation failed')
        metadata=execute(f'SELECT sum(record_count), count(*), sum(file_size_in_bytes) FROM {table}.files')
        require(metadata[0][0]==expected_rows and metadata[0][1]>0, 'Iceberg metadata cardinality failed')
        snapshot=execute(f'SELECT snapshot_id FROM {table}.history ORDER BY made_current_at DESC LIMIT 1')[0][0]
        require(sha256(source)==config['source']['sha256'], 'Source changed during ingestion')
        properties=execute(f'SHOW TBLPROPERTIES {table}')
        rest.capture('stages')
        result=dict(status='accepted_correctness_source',table=table,snapshot_id=snapshot,
                    record_count=expected_rows,file_count=metadata[0][1],data_bytes=metadata[0][2],
                    table_properties=properties,code_revision=revision,
                    limitations=['Preparation only; no matched control/treatment or rewrite yet',
                                 'Generator version in existing manifest is recorded, not independently rebuilt'])
        log.emit('preparation_accepted',**result)
        (run_dir/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    except Exception as exc:
        log.emit('preparation_failed',error_type=type(exc).__name__,error=str(exc),table=table,
                 preservation='Retain any created table and artifacts; never delete/reset')
        raise
    finally:
        cursor.close()
        conn.close()
        log.close()
        lock.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--expected-revision',required=True)
    args=parser.parse_args()
    prepare(args.config,args.expected_revision)
