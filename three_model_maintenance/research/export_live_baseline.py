"""Descriptive real-query baseline; failed campaign never becomes training data."""
import argparse,json,traceback,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/phase6-live-evaluation'))
from .common import read,sha,require,write_new,now,utc
from .ownership import exact_bindings
from three_model_maintenance.runtime.sf10_contract import canonical_result,references


def run(protocol,output):
 output.mkdir(parents=True,exist_ok=False);cfg=read(protocol)
 report=dict(status='running',started_utc=now(),training_eligible=False,physical_campaign_accepted=False,SQL_executed=False)
 try:
  require(utc(now())<utc(cfg['latest_start_utc']),'Export admission expired')
  for p,h in cfg['inputs'].items():require(sha(p)==h,'Input changed '+p)
  for p,h in cfg['code'].items():require(sha(ROOT/p)==h,'Code changed '+p)
  episode=Path(cfg['episode']);archive=episode/'direct_archive';cps=sorted(archive.glob('checkpoint_*'));last=cps[-1]
  events=[json.loads(s) for s in (episode/'events.jsonl').read_text().splitlines()]
  requests=[e for e in events if e['kind']=='statement_requested'];calls=[e for e in events if e['kind']=='statement_completed']
  source=read(cfg['source_config']);refs=references(source)
  inventory=[]
  for p in sorted(last.glob('receipt_*.json')):
   r=read(p)
   if r['resource'].startswith('sql?'):
    raw=archive/r['raw_path'];require(sha(raw)==r['raw_sha256'],'Raw SQL hash differs');inventory.extend(read(raw))
  binding=exact_bindings(requests,calls,inventory)['bindings']
  audit=read(cfg['reconciliation']);require(audit['status']=='passed_executed_work_count_reconciliation_only','Execution count proof missing')
  jobs={p['job_id']:p for p in audit['job_proofs']};tasks={}
  for cp in cps:
   for item in read(cp/'retained_tasks.json'):
    p=archive/item['raw_path'];require(sha(p)==item['raw_sha256'],'Task hash differs');tasks[item['request']['stage_id']]=read(p)
  rows=[];seen=set()
  for call in calls:
   qid=call['query_id'];mid=call['measurement_id'];require(canonical_result(call['rows'],qid,source)==refs[str(qid)],'Reference result mismatch')
   stage_ids={s['stage_id'] for jid in binding[mid]['success_job_ids'] for s in jobs[jid]['executed_stage_tasks']}
   actual=[t for sid in stage_ids for t in tasks[sid]];ids={t['taskId'] for t in actual}
   require(len(ids)==len(actual) and not ids & seen,'Shared/duplicate tasks across query baseline');seen|=ids
   metrics={}
   for field in ['executorCpuTime','executorRunTime']:
    values=[t['taskMetrics'][field] for t in actual if isinstance(t.get('taskMetrics'),dict) and field in t['taskMetrics']]
    require(all(type(v) is int and v>=0 for v in values),'Invalid explicit task metric')
    metrics[field]=dict(value=sum(values) if len(values)==len(actual) else None,observed_tasks=len(values),total_tasks=len(actual),unit='ns' if field=='executorCpuTime' else 'ms')
   rows.append(dict(query_id=qid,name=source['query_suite'][qid]['name'],client_service_seconds=call['client_elapsed_ns']/1e9,
                    directly_owned_jobs=len(binding[mid]['success_job_ids']),executed_stages=len(stage_ids),executed_tasks=len(actual),
                    task_metrics=metrics,correctness='matches_pinned_reference',replicates=1))
  require(len(rows)==6,'Six baseline rows required')
  checkpoints=[]
  for cp in cps:
   r=read(cp/'result.json');checkpoints.append(dict(checkpoint=cp.name,status=r['status'],requests=r['requests'],body_wall_seconds=(utc(r['ended_utc'])-utc(r['started_utc'])).total_seconds()))
  report.update(status='exported_descriptive_engineering_baseline_only',queries=rows,capture_checkpoints=checkpoints,
      metric_scope='Sequential single-client service time; summed owned-task CPU is not whole-server CPU or full controller cost.',
      limitations=['One observation per query, shared persistent server/cache, no uncertainty estimate.',
                   'No compaction, no arrival replay, no matched alternative, no improvement claim.',
                   'Original integration outcome stays 5 passed/1 failed/0 unattempted; query result correctness is separate.',
                   'Capture body timing excludes final result receipt persistence; not whole-controller overhead.'])
  for p,h in cfg['inputs'].items():require(sha(p)==h,'Input changed during export '+p)
 except Exception as exc:report.update(status='failed_preserved',error=str(exc),traceback=traceback.format_exc());raise
 finally:
  report['ended_utc']=now();write_new(output/'result.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.protocol,a.output)
