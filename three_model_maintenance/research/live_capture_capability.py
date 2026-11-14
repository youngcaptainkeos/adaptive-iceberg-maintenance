"""One registered real SF10 query suite; immediate direct task retention, no rewrite.

Engineering integration evidence only. Snapshot reuse and sequential query order
are explicit; these timings cannot establish scheduling or model benefit.
"""
import argparse
import json
import shutil
import sys
import traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/phase6-live-evaluation'))
from physical_measurements import EventLog,StatementRecorder
from three_model_maintenance.runtime.sf10_contract import canonical_result,references
from three_model_maintenance.runtime.direct_task_retention import DirectTaskRetention
from three_model_maintenance.research.common import now,read,require,sha,utc,write_new
import urllib.request


def run(protocol,output):
    output.mkdir(parents=True,exist_ok=False)
    cfg=read(protocol)
    result=dict(status='running',started_utc=now(),protocol_sha256=sha(protocol),passed_queries=0,
                failed_queries=0,unattempted_queries=6,query_results=[],physical_campaign_accepted=False,
                model_fit_performed=False,maintenance_executed=False,independent_performance_evidence=False)
    log=None;conn=None;current=None
    try:
        require(cfg['schema']=='live_direct_capture_capability_v1','Unknown protocol')
        require(utc(now())<utc(cfg['no_new_SQL_after_utc']),'SQL start cutoff expired')
        for name,digest in cfg['code_sha256'].items():require(sha(ROOT/name)==digest,'Changed code '+name)
        for name,spec in cfg['inputs'].items():require(sha(spec['path'])==spec['sha256'],'Changed input '+name)
        old=read(cfg['inputs']['source_config']['path'])
        require(len(old['query_suite'])==6,'Expected real six-query suite')
        require(shutil.disk_usage(output).free>=cfg['minimum_free_bytes'],'Evidence capacity too low')
        with urllib.request.urlopen(cfg['idle_jobs_url'],timeout=15) as response:active=json.load(response)
        write_new(output/'admission.json',dict(observed_utc=now(),running_jobs=active))
        require(active==[],'Spark has active work; no competing test')
        expected=references(old)
        context={name:r['iceberg_table']+' VERSION AS OF '+str(r['snapshot_id']) for name,r in old['sf10_tables'].items()}
        write_new(output/'registration.json',dict(protocol=cfg,source_tables=old['sf10_tables'],query_suite=old['query_suite'],scope='existing pinned source snapshots, real read-only integration, no workload replay'))
        from pyhive import hive
        conn=hive.Connection(**{k:old['engine'][k] for k in ('host','port','username')})
        cursor=conn.cursor();log=EventLog(output/'events.jsonl',cfg['label']);rec=StatementRecorder(log)
        archive=DirectTaskRetention(output/'direct_archive',**cfg['archive'])
        for index,q in enumerate(old['query_suite']):
            require(utc(now())<utc(cfg['no_new_SQL_after_utc']),'SQL cutoff reached; remaining queries unattempted')
            current=q['query_id'];result['unattempted_queries']-=1
            row=rec.execute(cursor,q['sql'].format(**context),role='trace_query',query_id=current)
            actual=canonical_result(row['rows'],current,old)
            require(actual==expected[str(current)],'Query result differs from pinned independent reference')
            events=[json.loads(s) for s in (output/'events.jsonl').read_text().splitlines()]
            requested=[e for e in events if e['kind']=='statement_requested']
            completed=[e for e in events if e['kind']=='statement_completed']
            checkpoint=archive.capture(requested,completed,terminal=index==5)
            record=dict(query_id=current,name=q['name'],measurement_id=row['measurement_id'],
                        client_elapsed_ns=row['fetch_end']['monotonic_ns']-row['client_execute_start']['monotonic_ns'],
                        correctness='matches_pinned_reference',archive_status=checkpoint['status'])
            result['query_results'].append(record);result['passed_queries']+=1;current=None
            write_new(output/f'query_{index}_result.json',record)
            print(json.dumps(record),flush=True)
        for name,digest in cfg['code_sha256'].items():require(sha(ROOT/name)==digest,'Code changed during run '+name)
        for name,spec in cfg['inputs'].items():require(sha(spec['path'])==spec['sha256'],'Input changed '+name)
        require(sha(protocol)==result['protocol_sha256'],'Protocol changed during run')
        result.update(status='passed_six_query_direct_capture_capability_only',
                      limitations=['Read-only source snapshot reuse, no independent performance estimate.',
                                   'No maintenance, arrival replay, telemetry or Gate A acceptance.',
                                   'Per-job executed/skipped reconciliation and full-drain integration still required.'])
    except Exception as exc:
        if current is not None:result['failed_queries']+=1
        result.update(status='failed_preserved',error=str(exc),traceback=traceback.format_exc(),failed_query_id=current)
        raise
    finally:
        if log is not None:log.close()
        if conn is not None:conn.close()
        result['ended_utc']=now();write_new(output/'result.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.protocol,a.output)
