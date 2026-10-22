#!/usr/bin/env python3
"""Read actual failed probe evidence; validate timing repair without any SQL."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,ast,inspect,json
from pathlib import Path
from collections import Counter
from queue_aware_maintenance.core.common import require,sha,write_json,now
from physical_measurements import StatementRecorder
from queue_aware_maintenance.analysis.probe_submission_overhead import actual_call_ns
from run_correctness_pilot import canonical,query_templates
from statement_timing import completed_statements

def run(directory,output):
 d=Path(directory);out=Path(output);out.mkdir(parents=True,exist_ok=False)
 result={'status':'running','started_utc':now(),'new_SQL_executed':False,'physical_restart_performed':False,'audit_source_sha256':sha(__file__),'repaired_probe_source_sha256':sha(source_file('probe_submission_overhead.py'))}
 try:
  failure=json.loads((d/'failure_result.json').read_text());require(failure['status']=='failed_preserved' and failure['error']=="'client_elapsed_ns'",'Unexpected failure; no generic retry')
  events=[json.loads(line) for line in (d/'events.jsonl').open()];registration=[r for r in events if r['kind']=='observer_probe_registration'];require(len(registration)==1,'Missing unique actual registration');cfg=registration[0]['configuration']
  successful_contracts=[]
  tree=ast.parse(inspect.getsource(StatementRecorder))
  for node in ast.walk(tree):
   if isinstance(node,ast.Return) and isinstance(node.value,ast.Dict):
    keys=[key.value for key in node.value.keys if isinstance(key,ast.Constant)]
    if 'fetch_end' in keys:successful_contracts.append(keys)
  require(len(successful_contracts)==1,'Changed or ambiguous helper return contract');keys=successful_contracts[0];require('client_elapsed_ns' not in keys,'Root cause contract changed')
  calls=[r for r in events if r['kind']=='statement_completed' and r['role'].startswith('observer_probe_')];require(len(calls)==1 and calls[0]['role']=='observer_probe_warmup','Unexpected physical attempt inventory')
  requests={r['measurement_id']:r for r in events if r['kind']=='statement_requested'};references={}
  for i in range(len(cfg['expected_query_ledgers'])):
   path=d/f'expected_ledger_{i}.jsonl';require(sha(path)==cfg['expected_query_ledgers'][i]['sha256'],'Changed expected reference');rows=[r for r in completed_statements([path]).values() if r['role']=='control_before'];require(len(rows)==1,'Ambiguous correctness reference');references[int(rows[0]['query_id'])]=canonical(rows[0]['rows'])
  repairs=[]
  for event in calls:
   require(canonical(event['rows'])==references[event['query_id']],'Completed warmup result differs')
   snapshot_requests=[r for r in events if r['kind']=='statement_completed' and requests[r['measurement_id']]['sql']==f"SELECT snapshot_id FROM {cfg['destination_table']}.history ORDER BY made_current_at DESC LIMIT 1"]
   require(len(snapshot_requests)==1,'Ambiguous table snapshot');snapshot=snapshot_requests[0]['rows'][0][0]
   expected_sql=query_templates(cfg['destination_table'])[event['query_id']].replace(f"FROM {cfg['destination_table']}",f"FROM {cfg['destination_table']} VERSION AS OF {snapshot}")
   require(requests[event['measurement_id']]['sql']==expected_sql,'Query/snapshot changed')
   # Every field below is taken from the actual completed statement, restricted
   # to the statically inspected successful return contract; no dummy clocks.
   actual_return={k:event[k] for k in keys};duration=actual_call_ns(actual_return);require(duration==event['client_elapsed_ns'],'Repaired duration disagrees with actual raw timing')
   repairs.append({'measurement_id':event['measurement_id'],'query_id':event['query_id'],'actual_call_ns':duration,'matches_raw_duration_exactly':True})
  require(not any(r['kind']=='observer_probe_query_complete' for r in events),'Unexpected completed accounting rows')
  result.update(status='passed_real_failed_record_timing_interface_audit_only',failure_result_sha256=sha(d/'failure_result.json'),events_sha256=sha(d/'events.jsonl'),original_failure_preserved=True,completed_warmup_calls=1,completed_measured_calls=0,unattempted_warmup_calls=3,unattempted_measured_calls=64,repairs=repairs,limitations=['One actual completed warmup validates corrected helper timing extraction, not the unexecuted full/minimal phases.','No full telemetry/task comparison audit completed before failure. No overhead estimate, cost-training row or policy result accepted.','Any future recovery requires fresh table/output/protocol/time cutoffs. Original failed frozen source remains unchanged.'])
 except Exception as e:result.update(status='failed_preserved',error=str(e));raise
 finally:result['ended_utc']=now();write_json(out/'result.json',result)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.directory,a.output)
