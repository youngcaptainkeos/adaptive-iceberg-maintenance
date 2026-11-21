"""Fail on unexplained work in observed inventories; no unseen-job guarantee."""
from pathlib import Path
from three_model_maintenance.research.common import integer,read,require


def audit_observed_scope(directory,rows,engine,table):
    baselines=[r for r in rows if r['kind']=='full_drain_engine_baseline']
    require(len(baselines)==1,'Missing unique pre-SQL engine baseline')
    baseline=baselines[0];position=rows.index(baseline)
    require(not any(r['kind']=='statement_requested' for r in rows[:position]),'Engine baseline after SQL')
    raw=[r for r in rows[:position] if r['kind']=='spark_rest' and r['resource']=='jobs']
    require(len(raw)==1 and not any(j['status']=='RUNNING' for j in raw[0]['payload']),'Non-idle/absent raw baseline')
    existing=set(baseline['job_ids'])
    require(existing=={j['jobId'] for j in raw[0]['payload']},'Baseline summary/raw differs')
    query_jobs={j for b in engine['bindings'].values() for j in b['success_job_ids']}
    metadata=[r for r in rows if r['kind']=='statement_requested' and r['role'] not in ('trace_query','maintenance')]
    frames=[r['payload'] for r in rows[position+1:] if r['kind']=='spark_rest' and r['resource']=='jobs']
    for receipt_path in sorted((Path(directory)/'direct_archive').glob('checkpoint_*/receipt_*.json')):
        receipt=read(receipt_path)
        if receipt['resource']=='jobs':
            frames.append(read(Path(directory)/'direct_archive'/receipt['raw_path']))
    require(frames,'No post-baseline observed engine inventory')
    final={};roles={}
    for frame in frames:
        require(type(frame) is list,'Invalid observed jobs frame')
        require(len({j['jobId'] for j in frame})==len(frame),'Duplicate observed jobs')
        for job in frame:
            jid=integer(job['jobId'],'observed job')
            if jid in existing:continue
            description=job.get('description')
            require(type(description) is str,'Missing observed job description')
            if jid in query_jobs:role='exact_query_SQL_link'
            elif description.startswith('Rewriting ') and description.endswith(' in '+table):role='rewrite_description'
            elif any(r['marker'] in description for r in metadata):role='marked_metadata'
            else:raise ValueError('Unexplained observed engine job: '+str(jid))
            require(jid not in roles or roles[jid]==role,'Observed job ownership changed')
            require(job['status'] in ('RUNNING','SUCCEEDED'),'Adverse observed work')
            for field in ('numFailedTasks','numKilledTasks','numFailedStages'):
                require(integer(job[field],field)==0,'Missing/adverse observed job counters')
            if jid in final and final[jid]['status']=='SUCCEEDED':
                require(job['status']=='SUCCEEDED','Terminal observed job regressed')
            roles[jid]=role;final[jid]=job
    require(query_jobs<=set(final),'Query-owned job absent from observed census')
    require(all(j['status']=='SUCCEEDED' for j in final.values()),'Observed work remained active')
    return dict(status='explained_observed_jobs_only',baseline_job_ids=sorted(existing),
                observed_job_roles={str(k):v for k,v in sorted(roles.items())},
                unknown_observed_jobs=0,exhaustive_unobserved_job_inventory_certified=False,
                limitation='Idle admission plus recorded inventories; work absent from every REST response cannot be certified.')
