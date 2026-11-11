"""Direct recorded SQL-to-job ownership analysis, never acceptance by coincidence."""
import argparse
import json
from pathlib import Path
from three_model_maintenance.audits.telemetry_gap_diagnostic import sha


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--episode',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--foreign-diagnostic',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    inputs=[a.episode/'events.jsonl',a.inventory/'raw_sql_inventory.json',a.inventory/'result.json',a.foreign_diagnostic]
    before={str(path):sha(path) for path in inputs}
    inventory=json.loads(inputs[1].read_text());receipt=json.loads(inputs[2].read_text());foreign=json.loads(inputs[3].read_text())
    if receipt['raw_sha256']!=before[str(inputs[1])] or foreign['events_sha256']!=before[str(inputs[0])]:raise ValueError('Different registered diagnostic evidence')
    events=[json.loads(line) for line in inputs[0].open()]
    requests={r['measurement_id']:r for r in events if r['kind']=='statement_requested'}
    calls=[r for r in events if r['kind']=='statement_completed' and r['role']=='trace_query']
    matches={};unresolved=[]
    for call in calls:
        mid=call['measurement_id'];request=requests[mid]
        exact='/* '+request['marker']+' */\n'+request['sql']
        found=[row for row in inventory if row['description']==exact]
        if len(found)!=1:
            unresolved.append(dict(measurement_id=mid,reason='missing_or_nonunique_exact_marked_SQL',matches=len(found)));continue
        row=found[0]
        if row['status']!='COMPLETED' or row['failedJobIds'] or row['runningJobIds']:
            unresolved.append(dict(measurement_id=mid,reason='nonterminal_or_adverse_SQL_jobs'));continue
        matches[mid]=dict(sql_execution_id=row['id'],success_job_ids=row['successJobIds'])
    rejected_links=[];unknown=[]
    for failure in foreign['failures']:
        for jid in failure['rejected_job_ids']:
            mid=failure['measurement_id'];proof=matches.get(mid)
            target=rejected_links if proof and jid in proof['success_job_ids'] else unknown
            target.append(dict(measurement_id=mid,job_id=jid,sql_execution_id=proof['sql_execution_id'] if proof else None))
    if any(sha(path)!=before[str(path)] for path in inputs):raise ValueError('Evidence changed during diagnostic')
    result=dict(status='completed_direct_posthoc_SQL_job_ownership_diagnostic',input_sha256=before,
        completed_queries=len(calls),exact_SQL_matches=len(matches),unresolved_queries=unresolved,
        rejected_job_links_with_direct_ownership=len(rejected_links),unresolved_rejected_job_links=unknown,
        direct_links=rejected_links,query_execution_bindings=matches,
        original_failed_episode_accepted=False,
        limitation='Posthoc ownership does not certify all task evidence, counterfactual costs, model training or a passed physical episode. Future collection must freeze SQL execution/job mappings prospectively.')
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('direct_links','query_execution_bindings','input_sha256')},indent=2))
