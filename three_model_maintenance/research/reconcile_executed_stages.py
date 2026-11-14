"""Audit executed-stage coverage using explicit job counters and actual tasks.

Absent referenced stage states remain absent. Aggregate count reconciliation is
reported separately from complete dependency-stage inventory and never changes
the original integration result. No REST or SQL is requested.
"""
import argparse,json,traceback
from pathlib import Path
from .common import read,write_new,require,integer,utc,now,sha
from .capture_retained_tasks import validate_tasks


def spark_time(value):
    require(type(value) is str and value.endswith('GMT'),'Explicit Spark GMT time required')
    return utc(value[:-3]+'+00:00')


def run(protocol,output):
    output.mkdir(parents=True,exist_ok=False);cfg=read(protocol)
    report=dict(status='running',started_utc=now(),protocol_sha256=sha(protocol),SQL_executed=False,
                REST_requested=False,original_failure_accepted=False,job_proofs=[])
    try:
        root=Path(__file__).resolve().parents[2]
        require(utc(now())<utc(cfg['latest_start_utc']),'Audit admission cutoff expired')
        for p,h in cfg['code_sha256'].items():require(sha(root/p)==h,'Source differs '+p)
        for p,h in cfg['input_sha256'].items():require(sha(p)==h,'Input differs '+p)
        archive=Path(cfg['archive']);checkpoints=sorted(archive.glob('checkpoint_*'))
        jobs={};stages={};all_tasks={}
        for cp in checkpoints:
            for receipt in sorted(cp.glob('receipt_*.json')):
                r=read(receipt);p=(archive/r['raw_path']).resolve()
                require(p.is_relative_to(archive.resolve()) and sha(p)==r['raw_sha256'],'Raw response checksum/path differs')
                require(r['response_end_monotonic_ns']>=r['request_start_monotonic_ns'],'Response clock reversed')
                payload=read(p)
                if r['resource']=='jobs':
                    for job in payload:jobs[job['jobId']]=job
                elif r['resource']=='stages':
                    for stage in payload:stages[(stage['stageId'],stage['attemptId'])]=stage
            for item in read(cp/'retained_tasks.json'):
                req=item['request'];p=archive/item['raw_path']
                require(sha(p)==item['raw_sha256'],'Task reference checksum differs')
                payload=read(p);validate_tasks(payload,req['num_tasks'])
                key=(req['stage_id'],req['attempt_id']);require(key not in all_tasks or all_tasks[key]==payload,'Task identity changed')
                all_tasks[key]=payload
        selection=read(checkpoints[-1]/'selection.json');owned=selection['plan']['directly_owned_job_ids']
        for jid in owned:
            job=jobs[jid];require(job['status']=='SUCCEEDED','Nonterminal owned job')
            for f in ['numFailedTasks','numKilledTasks','numFailedStages']:require(integer(job[f],f)==0,'Failed engine work')
            completed=integer(job['numCompletedStages'],'completed stages');skipped=integer(job['numSkippedStages'],'skipped stages')
            completed_tasks=integer(job['numCompletedTasks'],'completed tasks');skipped_tasks=integer(job['numSkippedTasks'],'skipped tasks')
            total_tasks=integer(job['numTasks'],'total tasks')
            ids=job['stageIds'];require(len(ids)==len(set(ids))==completed+skipped,'Job stage totals do not reconcile')
            lo,hi=spark_time(job['submissionTime']),spark_time(job['completionTime']);require(lo<=hi,'Invalid job interval')
            executed=[];unknown=[];other=[]
            for sid in ids:
                s=stages.get((sid,0))
                if s is None:unknown.append(sid);continue
                if s['status']=='COMPLETE' and 'submissionTime' in s and 'completionTime' in s and lo<=spark_time(s['submissionTime'])<=spark_time(s['completionTime'])<=hi:
                    for f in ['numFailedTasks','numKilledTasks']:require(integer(s[f],f)==0,'Adverse stage work')
                    payload=all_tasks[(sid,0)];validate_tasks(payload,s['numTasks'])
                    require(s['numCompleteTasks']==len(payload),'Stage complete-task count differs')
                    executed.append(dict(stage_id=sid,tasks=len(payload)))
                else:other.append(dict(stage_id=sid,observed_status=s['status']))
            require(len(executed)==completed,'Executed stages do not equal explicit job count')
            require(sum(s['tasks'] for s in executed)==completed_tasks,'Executed tasks do not equal job completed-task count')
            require(total_tasks==completed_tasks+skipped_tasks,'Completed/skipped task totals differ')
            require(len(unknown)+len(other)==skipped,'Remaining reference count differs from explicit skipped-stage count')
            report['job_proofs'].append(dict(job_id=jid,executed_stage_tasks=executed,
                   explicit_completed_stages=completed,explicit_skipped_stages=skipped,
                   unobserved_reference_ids=unknown,other_observed_references=other,
                   missing_stage_states_imputed=False))
        for p,h in cfg['input_sha256'].items():require(sha(p)==h,'Input changed '+p)
        for p,h in cfg['code_sha256'].items():require(sha(root/p)==h,'Code changed '+p)
        report.update(status='passed_executed_work_count_reconciliation_only',owned_jobs=len(owned),
                      executed_stages=sum(len(p['executed_stage_tasks']) for p in report['job_proofs']),
                      executed_tasks=sum(s['tasks'] for p in report['job_proofs'] for s in p['executed_stage_tasks']),
                      absent_reference_occurrences=sum(len(p['unobserved_reference_ids']) for p in report['job_proofs']),
                      limitations=['Direct stage membership plus interval and explicit count agreement; no per-query CPU attribution.',
                                   'Missing dependency states remain unknown. Original terminal-inventory failure remains failed.',
                                   'No maintenance/scheduler comparison; changing future acceptance requires explicit versioned contract.'])
    except Exception as exc:
        report.update(status='failed_preserved',error=str(exc),traceback=traceback.format_exc());raise
    finally:
        report['ended_utc']=now();write_new(output/'result.json',report);print(json.dumps({k:v for k,v in report.items() if k!='job_proofs'}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.protocol,a.output)
