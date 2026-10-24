"""Prepare genuine SF10 and validate real multi-table plan/query execution.

Capability pilot only: no arrival trace, pending-state labels, cost training or
relaxation of the existing live collector's host/history/freshness requirements.
"""
import argparse
import ast
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import traceback
import urllib.request
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from three_model_maintenance.contracts import require
from three_model_maintenance.training.data import sha,read,save
from three_model_maintenance.preparation.query_plan import parse

REPO=Path(__file__).resolve().parents[2]
LEGACY=REPO/'scripts/phase6-live-evaluation'
sys.path.insert(0,str(LEGACY))
from physical_measurements import EventLog,StatementRecorder,SparkEvidence,stamp


def canonical(rows):
    def value(v):
        if isinstance(v,(Decimal,int)) and not isinstance(v,bool):return format(Decimal(v).normalize(),'f')
        require(not isinstance(v,float),'Unregistered approximate result comparison')
        return None if v is None else str(v)
    return sorted(json.dumps([value(v) for v in row],ensure_ascii=False) for row in rows)


def guard(cfg):require(datetime.now(timezone.utc)<datetime.fromisoformat(cfg['no_new_operation_after_utc']),'Registered cutoff; active work finishes naturally')


def checked(cfg):
    for spec in cfg['sources']:
        path=REPO/spec['path'];require(sha(path)==spec['sha256'],'Frozen source changed '+spec['path'])
        if path.suffix=='.py':ast.parse(path.read_text(),filename=str(path))
    origin=REPO/cfg['schema_origin']['path']
    require(sha(origin)==cfg['schema_origin']['sha256'] and read(origin)['schemas']==cfg['schemas'],'Registered schema provenance changed')
    for spec in (cfg['generator'],cfg['distributions']):require(sha(Path(spec['path']))==spec['sha256'],'Benchmark generator input changed')


def generate(cfg,out):
    guard(cfg);source=Path(cfg['dataset_directory'])
    require(not source.exists(),'Never overwrite generated dataset');source.mkdir(parents=True,exist_ok=False)
    require(shutil.disk_usage(source).free>=cfg['required_free_bytes'],'Insufficient registered source/spill/warehouse budget')
    env=dict(os.environ,DSS_PATH=str(source),DSS_CONFIG=str(Path(cfg['distributions']['path']).parent),DSS_DIST=Path(cfg['distributions']['path']).name)
    with (out/'dbgen.log').open('x') as stream:
        command=[cfg['generator']['path'],'-s',str(cfg['scale_factor'])]
        result=subprocess.run(command,cwd=source,env=env,stdout=stream,stderr=subprocess.STDOUT)
    require(result.returncode==0,'Real dbgen failed; preserve all partial data')
    manifest=[]
    for name in cfg['table_order']:
        path=source/(name+'.tbl');require(path.is_file() and path.stat().st_size>0,'Missing generated table')
        manifest.append({'table':name,'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)})
    save(out/'result.json',{'status':'generated_benchmark_files_not_ingestion_acceptance','command':command,'scale_factor':cfg['scale_factor'],
        'generator_sha256':cfg['generator']['sha256'],'distributions_sha256':cfg['distributions']['sha256'],'tables':manifest,
        'limitations':['Existing binary and distribution digests frozen; toolchain was not independently rebuilt/certified.']})


def source_reference(cfg,out):
    import duckdb
    generated=read(Path(cfg['output_directory'])/'generate/result.json')
    require(generated['status']=='generated_benchmark_files_not_ingestion_acceptance','Missing real generation')
    db=duckdb.connect(str(out/'reference.duckdb'))
    db.execute('SET memory_limit='+repr(cfg['duckdb_memory_limit']));db.execute('SET threads='+str(cfg['duckdb_threads']))
    db.execute('SET temp_directory='+repr(str(out/'spill')))
    tables=[]
    try:
        for item in generated['tables']:
            guard(cfg);name=item['table'];path=Path(item['path']);require(sha(path)==item['sha256'],'Changed generated source')
            fields=cfg['schemas'][name];columns={f['name']:'VARCHAR' for f in fields};columns['_trailing']='VARCHAR'
            raw="read_csv(?, delim='|', header=false, auto_detect=false, columns="+repr(columns)+", quote='', escape='', strict_mode=true, ignore_errors=false)"
            bad=['_trailing IS NOT NULL']
            for field in fields:
                column,dtype=field['name'],field['type'];bad.append(column+' IS NULL')
                if dtype!='VARCHAR':
                    pattern=(r'[+-]?[0-9]+' if dtype in ('INTEGER','BIGINT') else r'[0-9]{4}-[0-9]{2}-[0-9]{2}' if dtype=='DATE' else r'[+-]?[0-9]+(\.[0-9]{1,2})?')
                    pattern_sql="'"+pattern.replace("'","''")+"'"
                    bad.append('NOT regexp_full_match('+column+','+pattern_sql+') OR TRY_CAST('+column+' AS '+dtype+') IS NULL')
            counts=db.execute('SELECT count(*),count(*) FILTER (WHERE '+' OR '.join(bad)+') FROM '+raw,[str(path)]).fetchone()
            require(counts[0]>0 and counts[1]==0,'Invalid typed/lexical/trailing source field '+name)
            if name in cfg['expected_rows']:require(counts[0]==cfg['expected_rows'][name],'Scale cardinality differs '+name)
            projected=', '.join('CAST('+f['name']+' AS '+f['type']+') AS '+f['name'] for f in fields)
            guard(cfg);db.execute('CREATE TABLE '+name+' AS SELECT '+projected+' FROM '+raw,[str(path)])
            keys=cfg['primary_keys'][name];key=', '.join(keys)
            require(db.execute('SELECT count(*) FROM (SELECT '+key+' FROM '+name+' GROUP BY '+key+' HAVING count(*)<>1)').fetchone()[0]==0,'Duplicate primary key '+name)
            tables.append(dict(item,rows=counts[0]));save(out/(name+'_validated.json'),tables[-1])
        for fk in cfg['foreign_keys']:
            guard(cfg);conditions=' AND '.join('c.'+c+'=p.'+p for c,p in zip(fk['columns'],fk['parent_columns']))
            missing=db.execute('SELECT count(*) FROM '+fk['table']+' c ANTI JOIN '+fk['parent']+' p ON '+conditions).fetchone()[0]
            require(missing==0,'Missing FK '+str(fk))
        references=[]
        for query in cfg['queries']:
            guard(cfg);sql=query['sql'].format(**{name:name for name in cfg['table_order']})
            before=stamp();rows=db.execute(sql).fetchall();after=stamp()
            references.append({'query_id':query['query_id'],'sql':sql,'canonical_rows':canonical(rows),'start':before,'end':after})
        save(out/'query_references.json',references)
        save(out/'result.json',{'status':'verified_typed_relational_source_and_reference_queries','tables':tables,
             'reference_sha256':sha(out/'query_references.json'),'duckdb_version':duckdb.__version__,
             'foreign_keys_checked':len(cfg['foreign_keys']),'scale_factor':cfg['scale_factor']})
    finally:db.close()


def connection(cfg):
    from pyhive import hive
    return hive.Connection(**{k:cfg['engine'][k] for k in ('host','port','username')})


def table_name(cfg,name):
    table='local.experiment.'+cfg['table_prefix']+'_'+name
    require(re.fullmatch(r'local\.experiment\.integrity_sf10_[a-z0-9_]+',table),'Fresh isolated SF10 table required');return table


def prepare(cfg,out):
    source=read(Path(cfg['output_directory'])/'source_reference/result.json')
    require(source['status']=='verified_typed_relational_source_and_reference_queries','Unaccepted source')
    log=EventLog(out/'events.jsonl',cfg['experiment_id']+'_prepare');rec=StatementRecorder(log)
    conn=connection(cfg);cursor=conn.cursor();rest=SparkEvidence(cfg['rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log)
    def execute(sql):guard(cfg);return rec.execute(cursor,sql,role='sf10_preparation')
    results=[]
    try:
        require(not rest._capture('jobs?status=running'),'Other active Spark jobs')
        require(execute('SELECT version()')['rows'][0][0].split()[0]==cfg['engine']['expected_version'],'Spark version differs')
        rest.capture('environment');execute('SET spark.sql.ansi.enabled=true');execute('SET spark.sql.csv.parser.columnPruning.enabled=false')
        names={r[1] for r in execute('SHOW TABLES IN local.experiment')['rows']}
        require(all(table_name(cfg,n).split('.')[-1] not in names for n in cfg['table_order']),'Occupied table identity; never overwrite')
        for item in source['tables']:
            name=item['table'];path=Path(item['path']);require(sha(path)==item['sha256'],'Changed ingestion source')
            fields=cfg['schemas'][name];mapping={'INTEGER':'INT','VARCHAR':'STRING'}
            schema=', '.join(f['name']+' '+mapping.get(f['type'],f['type']) for f in fields)+', _trailing STRING'
            view='sf10_source_'+name
            execute('CREATE TEMPORARY VIEW '+view+' ('+schema+") USING csv OPTIONS (path '"+path.as_uri()+"', sep '|', header 'false', quote '', mode 'FAILFAST', dateFormat 'yyyy-MM-dd')")
            invalid=' OR '.join(f['name']+' IS NULL' for f in fields)+" OR (_trailing IS NOT NULL AND _trailing<>'')"
            require(tuple(execute('SELECT count(*),sum(CASE WHEN '+invalid+' THEN 1 ELSE 0 END) FROM '+view)['rows'][0])==(item['rows'],0),'Spark full typed source validation failed')
            cols=', '.join(f['name'] for f in fields);table=table_name(cfg,name)
            hint='/*+ REPARTITION('+str(cfg['lineitem_file_count'])+') */ ' if name=='lineitem' else ''
            execute('CREATE TABLE '+table+' USING iceberg AS SELECT '+hint+cols+' FROM '+view)
            require(execute('SELECT count(*) FROM '+table)['rows'][0][0]==item['rows'],'Loaded row count differs')
            # Exact full-row bidirectional multiset gate, not sampled checksums.
            diff='SELECT count(*) FROM ((SELECT '+cols+' FROM '+table+' EXCEPT ALL SELECT '+cols+' FROM '+view+') UNION ALL (SELECT '+cols+' FROM '+view+' EXCEPT ALL SELECT '+cols+' FROM '+table+')) d'
            require(execute(diff)['rows'][0][0]==0,'Loaded full-row multiset differs')
            meta=execute('SELECT sum(record_count),count(*),sum(file_size_in_bytes) FROM '+table+'.files')['rows'][0]
            require(meta[0]==item['rows'] and meta[1]>0,'Metadata cardinality differs')
            if name=='lineitem':require(meta[1]==cfg['lineitem_file_count'],'Registered fragmented layout not obtained')
            snapshot=execute('SELECT snapshot_id FROM '+table+'.history ORDER BY made_current_at DESC LIMIT 1')['rows'][0][0]
            results.append({'table':name,'iceberg_table':table,'snapshot_id':snapshot,'rows':item['rows'],'file_count':meta[1],'data_bytes':meta[2]})
            save(out/(name+'_loaded.json'),results[-1])
        save(out/'result.json',{'status':'verified_sf10_eight_table_ingestion_only','tables':results,'events_sha256':sha(out/'events.jsonl'),
                              'cost_training_accepted':False,'sf100_ready':False})
    finally:cursor.close();conn.close();log.close()


def plan_query(cfg,out):
    prepared=read(Path(cfg['output_directory'])/'prepare/result.json')
    refs=read(Path(cfg['output_directory'])/'source_reference/query_references.json')
    references={r['query_id']:r for r in refs}
    state={r['table']:dict(r) for r in prepared['tables']}
    log=EventLog(out/'events.jsonl',cfg['experiment_id']+'_plans');rec=StatementRecorder(log);conn=connection(cfg);cursor=conn.cursor()
    rest=SparkEvidence(cfg['rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log)
    observed=[]
    def execute(sql,role,qid=None):guard(cfg);return rec.execute(cursor,sql,role=role,query_id=qid)
    try:
        require(not rest._capture('jobs?status=running'),'Other Spark work before capability query pilot')
        for phase in ('fragmented','compacted'):
            for query in cfg['queries']:
                qid=query['query_id'];context={n:r['iceberg_table']+' VERSION AS OF '+str(r['snapshot_id']) for n,r in state.items()}
                sql=query['sql'].format(**context);plans={};records={}
                for mode in ('FORMATTED','COST'):
                    record=execute('EXPLAIN '+mode+' '+sql,'preexecution_plan',qid);records[mode]=record
                    text='\n'.join(str(row[0]) for row in record['rows']);plans[mode]=text
                    with (out/(phase+'_'+str(qid)+'_'+mode+'.txt')).open('x') as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
                plan=parse(plans['FORMATTED'],plans['COST'])
                # Serialize and fsync raw plan plus feature receipt before actual query.
                receipt={'query_id':qid,'phase':phase,'sql':sql,'sql_sha256':hashlib.sha256(sql.encode()).hexdigest(),
                         'snapshots':{n:r['snapshot_id'] for n,r in state.items()},
                         'layouts':{n:{k:r[k] for k in ('rows','file_count','data_bytes')} for n,r in state.items()},'plan':plan,
                         'plan_call_ids':{mode:r['measurement_id'] for mode,r in records.items()},'captured_at':stamp()}
                receipt_path=out/(phase+'_'+str(qid)+'_receipt.json')
                with receipt_path.open('x') as stream:json.dump(receipt,stream,indent=2);stream.flush();os.fsync(stream.fileno())
                available=stamp();result=execute(sql,'sf10_capability_query',qid)
                require(available['monotonic_ns']<=result['client_execute_start']['monotonic_ns'],'Plan unavailable before actual query')
                require(canonical(result['rows'])==references[qid]['canonical_rows'],'Cross-engine query result differs')
                observed.append({'phase':phase,'query_id':qid,'measurement_id':result['measurement_id'],
                     'receipt':receipt_path.name,'receipt_sha256':sha(receipt_path),'plan_available_observed_at':available,
                     'client_execute_start':result['client_execute_start'],'fetch_end':result['fetch_end'],
                     'service_ms':(result['fetch_end']['monotonic_ns']-result['client_execute_start']['monotonic_ns'])/1e6,
                     'features':plan['features'],'rows_verified':True})
            if phase=='fragmented':
                line=state['lineitem'];before=line['snapshot_id']
                action=execute("CALL local.system.rewrite_data_files(table => '"+line['iceberg_table'].removeprefix('local.')+"', strategy => 'binpack', options => map('partial-progress.enabled','false'))",'sf10_maintenance')
                execute('REFRESH TABLE '+line['iceberg_table'],'sf10_metadata')
                line['snapshot_id']=execute('SELECT snapshot_id FROM '+line['iceberg_table']+'.history ORDER BY made_current_at DESC LIMIT 1','sf10_metadata')['rows'][0][0]
                require(line['snapshot_id']!=before,'SF10 rewrite made no new snapshot')
                metadata=execute('SELECT sum(record_count),count(*),sum(file_size_in_bytes) FROM '+line['iceberg_table']+'.files','sf10_metadata')['rows'][0]
                require(metadata[0]==line['rows'] and 0<metadata[1]<line['file_count'],'SF10 rewrite did not reduce layout/preserve rows')
                diff='SELECT count(*) FROM ((SELECT * FROM '+line['iceberg_table']+' VERSION AS OF '+str(before)+' EXCEPT ALL SELECT * FROM '+line['iceberg_table']+') UNION ALL (SELECT * FROM '+line['iceberg_table']+' EXCEPT ALL SELECT * FROM '+line['iceberg_table']+' VERSION AS OF '+str(before)+')) d'
                require(execute(diff,'sf10_multiset')['rows'][0][0]==0,'Rewrite changed full-row multiset')
                save(out/'maintenance.json',{'statement':action,'before_snapshot':before,'after_snapshot':line['snapshot_id'],
                     'before_files':line['file_count'],'after_files':metadata[1],'after_bytes':metadata[2]})
                line.update(file_count=metadata[1],data_bytes=metadata[2])
        save(out/'observations.json',observed)
        save(out/'result.json',{'status':'completed_sf10_plan_and_query_capability_pending_audit','queries':len(observed),
             'cost_training_accepted':False,'matched_pending_state_corpus':False,'arrival_trace_replayed':False,
             'limitations':['Closed-loop capability queries, not a Snowset replay or A/B experiment.',
                            'No maintenance-concurrent query or complete offered-demand history collected.',
                            'Six declared custom benchmark queries, not official22-query TPC-H score.']})
    finally:cursor.close();conn.close();log.close()


def audit(cfg,out):
    root=Path(cfg['output_directory']);observed=read(root/'plan_query/observations.json')
    rows=[json.loads(line) for line in (root/'plan_query/events.jsonl').open()]
    completed={r['measurement_id']:r for r in rows if r['kind']=='statement_completed'}
    refs={r['query_id']:r for r in read(root/'source_reference/query_references.json')}
    requested={r['measurement_id']:r for r in rows if r['kind']=='statement_requested'}
    counts=[]
    for record in observed:
        folder=root/'plan_query';receipt=read(folder/record['receipt']);require(sha(folder/record['receipt'])==record['receipt_sha256'],'Changed plan receipt')
        prefix=record['phase']+'_'+str(record['query_id'])
        extracted=parse((folder/(prefix+'_FORMATTED.txt')).read_text(),(folder/(prefix+'_COST.txt')).read_text())
        require(extracted==receipt['plan'] and extracted['features']==record['features'],'Plan reconstruction differs')
        for mode,mid in receipt['plan_call_ids'].items():
            require(requested[mid]['sql']=='EXPLAIN '+mode+' '+receipt['sql'] and
                    '\n'.join(str(r[0]) for r in completed[mid]['rows'])==(folder/(prefix+'_'+mode+'.txt')).read_text() and
                    completed[mid]['fetch_end']['monotonic_ns']<=record['plan_available_observed_at']['monotonic_ns'],
                    'Raw plan call/persistence binding differs')
        call=completed[record['measurement_id']]
        require(canonical(call['rows'])==refs[record['query_id']]['canonical_rows'] and
                record['service_ms']==(call['fetch_end']['monotonic_ns']-call['client_execute_start']['monotonic_ns'])/1e6,
                'Actual query result/timing differs')
        require(record['plan_available_observed_at']['monotonic_ns']<=call['client_execute_start']['monotonic_ns'] and
                hashlib.sha256(next(r['sql'] for r in rows if r['kind']=='statement_requested' and r['measurement_id']==record['measurement_id']).encode()).hexdigest()==receipt['sql_sha256'],'Feature/SQL availability binding differs')
        counts.append(extracted['features'])
    require(len(observed)==2*len(cfg['queries']) and any(c['plan_join_count']>0 for c in counts) and
            any(c['plan_sort_count']>0 for c in counts),'Missing registered query structural variety')
    save(out/'result.json',{'status':'passed_sf10_source_query_plan_rewrite_capability_only','observations':len(observed),
         'plan_features':counts,'cost_training_accepted':False,'matched_pending_state_corpus':False,'sf100_ready':False,
         'limitations':['Full source/multiset/reference/plan checks only, not temporal scheduling benefit or heldout accuracy.',
                        'SF10 may fit host cache; measured scale is not proof of disk-bound workloads.',
                        'Matched source-family A/B histories, independent splits, calibrated uncertainty and C remain outstanding.']})


def admission(cfg,out):
    memory={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
    free=shutil.disk_usage(REPO).free
    require(memory['MemAvailable']>=cfg['minimum_available_memory_bytes'] and free>=cfg['required_free_bytes'],'Insufficient admitted capacity')
    log=EventLog(out/'events.jsonl',cfg['experiment_id']+'_admission')
    try:
        rest=SparkEvidence(cfg['rest_url'],cfg['spark_app_id'],cfg['rest_timeout_seconds'],log)
        require(not rest._capture('jobs?status=running'),'Competing active Spark work')
        environment=rest.capture('environment')
        require(dict(environment['sparkProperties']).get('spark.master')==cfg['expected_spark_master'],'Spark resource environment changed')
        save(out/'result.json',{'status':'admitted_current_resources_only','memory':memory,'free_bytes':free,
             'spark_app_id':cfg['spark_app_id'],'environment_captured':True,'sf100_ready':False,
             'limitations':['Observed free capacity is not a guaranteed future allocation or SF100 admission.']})
    finally:log.close()


STAGES={'admission':admission,'generate':generate,'source_reference':source_reference,'prepare':prepare,'plan_query':plan_query,'audit':audit}


def run(protocol,stage=None):
    cfg=read(protocol);checked(cfg)
    require(cfg['schema_version']=='sf10_query_plan_capability_v1' and cfg['scale_factor']==10,'Explicit SF10 pilot only')
    root=Path(cfg['output_directory'])
    if stage:
        out=root/stage;out.mkdir(parents=True,exist_ok=False)
        try:STAGES[stage](cfg,out)
        except Exception as exc:save(out/'failure.json',{'error':str(exc),'traceback':traceback.format_exc()});raise
        return
    require(subprocess.check_output(['git','show','HEAD:'+str(protocol.relative_to(REPO))],cwd=REPO)==protocol.read_bytes(),'Protocol must be committed unchanged')
    root.mkdir(parents=True,exist_ok=False);save(root/'registration.json',cfg)
    handles=[];report={'status':'running','pid':os.getpid(),'protocol_sha256':sha(protocol),'started_utc':stamp()['utc'],'stages':[],
                      'cost_training_accepted':False,'matched_pending_state_corpus':False,'sf100_ready':False}
    def progress():(root/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        for name in ('.three_model_collection.lock','.queue_aware_study.lock','.common_horizon_cohort.lock','.physical_correctness.lock'):
            handle=(REPO/'results'/name).open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(handle)
        progress()
        for name in STAGES:
            guard(cfg);checked(cfg);record={'stage':name,'started_utc':stamp()['utc']};report['stages'].append(record);progress()
            with (root/(name+'.log')).open('x') as log:
                result=subprocess.run([sys.executable,'-B',str(LEGACY/'run_with_failure_alert.py'),'--label',cfg['experiment_id']+'_'+name,
                    '--receipt',str(root/(name+'_failure_alert.json')),'--',sys.executable,'-B','-m','three_model_maintenance.experiments.scale_query',
                    '--protocol',str(protocol),'--stage',name],cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
            record.update(returncode=result.returncode,ended_utc=stamp()['utc']);progress()
            require(result.returncode==0,'Failed '+name+'; preserve failure and unattempted stages')
            record['result_sha256']=sha(root/name/'result.json')
        report['status']='completed_sf10_capability_only'
    except Exception as exc:report.update(status='failed_preserved_no_retry',error=str(exc));raise
    finally:
        report['ended_utc']=stamp()['utc'];progress();save(root/'result.json',report)
        for handle in handles:handle.close()
    notice={'delivered':False}
    try:
        request=urllib.request.Request(cfg['notification_topic'],data=(cfg['experiment_id']+': all SF10 source/plan/query/rewrite capability stages passed. Not accepted cost training, matched A/B, SF100 or scheduler.').encode(),headers={'Title':'Capstone SF10 capability completed'},method='POST')
        with urllib.request.urlopen(request,timeout=10) as response:notice.update(delivered=True,http_status=response.status)
    except Exception as exc:notice['error']=str(exc)
    save(root/'completion_notification.json',notice)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--stage',choices=STAGES)
    args=parser.parse_args();run(args.protocol.resolve(),args.stage)
