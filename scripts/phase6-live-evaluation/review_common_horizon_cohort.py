#!/usr/bin/env python3
"""Re-audit actual cohort and describe outcomes without inventing causal cost labels."""
import argparse,json,statistics
from pathlib import Path
from experiment_validation import require,sha256
from run_trace_queue_diagnostic import audit


def review(directory,output):
    directory=Path(directory).resolve();cfg=json.loads((directory/'config.json').read_text());result=json.loads((directory/'result.json').read_text())
    require(result['status'] in ('completed_common_horizon_diagnostic_only','stopped_failed_gate_preserve_all'),'Active/unknown cohort')
    require(cfg['schema_version']==result['schema_version']=='common_horizon_cohort_pilot_v1','Unbound cohort schema')
    for name,digest in result['code_sha256'].items():require(sha256(directory/'code'/name)==digest,'Frozen cohort code changed')
    summaries=[];failures=[];prefixes={}
    for i,attempt in enumerate(result['attempts'],start=1):
        require(attempt['index']==i and attempt['action_arm']==cfg['registered_order'][i-1] and attempt['protocol_sha256']==cfg['episodes'][i-1]['sha256'],'Attempt order/config changed')
        raw=directory.parent/attempt['experiment_id']
        if attempt['status']!='passed_physical_and_raw_audit_only':failures.append(attempt);continue
        require(sha256(raw/'config.json')==attempt['protocol_sha256'] and sha256(raw/'result.json')==attempt['raw_result_sha256'] and sha256(directory/f'episode_{i:02d}_audit.json')==attempt['audit_sha256'],'Executed evidence hashes changed')
        report=audit(raw);require(report['events_sha256']==attempt['events_sha256'],'Raw source changed')
        recorded=json.loads((directory/f'episode_{i:02d}_audit.json').read_text());require(report==recorded,'Reconstructed audit differs')
        ids=[r['source_query_id'] for r in report['queries'] if r['completed_within_horizon']]
        group=attempt.get('comparison_group','single_window');prefix=prefixes.get(group)
        prefix=ids if prefix is None else prefix[:min(len(prefix),len(ids))];prefixes[group]=prefix
        require(ids[:len(prefix)]==prefix,'Arrival-aligned completion prefix differs within window')
        qstats={}
        for q in range(4):
            rows=[r for r in report['queries'] if r['query_id']==q]
            qstats[str(q)]={'observed_queries':len(rows),'mean_actual_service_ms':statistics.mean(r['service_ms'] for r in rows) if rows else None,'mean_queue_to_dispatch_ms':statistics.mean(r['queue_to_dispatch_ms'] for r in rows) if rows else None}
        arm=report['common_horizon_arm']
        summaries.append({'index':i,'experiment_id':attempt['experiment_id'],'arm':attempt['action_arm'],'comparison_group':group,'offered':report['offered'],'horizon_counts':report['horizon_actual_transition_counts'],'final_counts':report['final_states'],'initial_file_state':arm['initial_file_state'],'final_file_state':arm['final_file_state'],'maintenance':arm['maintenance'],'overlapped_query_count':sum(r['verified_task_lifetime_overlap'] for r in arm['query_task_exposures']),'per_query_descriptive_metrics':qstats,'boundary_observation_lateness_ms':report['boundary_observation_lateness_ms'],'events_sha256':report['events_sha256']})
    require(result['status']!='completed_common_horizon_diagnostic_only' or len(summaries)==len(cfg['episodes']) and not failures,'Incomplete successful cohort')
    reviewed={'status':'audited_common_horizon_diagnostic_review','planned':len(cfg['episodes']),'audited':len(summaries),'failures_preserved':failures,'unattempted':len(cfg['episodes'])-len(result['attempts']),'episodes':summaries,'common_completed_prefix_counts_by_window':{k:len(v) for k,v in prefixes.items()},'cost_training_accepted':False,'automatic_winner_selected':False,'cohort_result_sha256':sha256(directory/'result.json'),'review_code_sha256':sha256(Path(__file__)),'limitations':cfg['limitations']+['Service/queue summaries condition on dispatched work; unfinished arrivals retained separately, not omitted from offered denominator.','Completed-prefix matching is descriptive; shared time/cache and changing layouts do not identify individual counterfactual costs.']}
    with Path(output).open('x') as f:json.dump(reviewed,f,indent=2);f.write('\n')
    print(json.dumps({'status':reviewed['status'],'audited':len(summaries),'failed':len(failures),'common_completed_prefix_counts_by_window':reviewed['common_completed_prefix_counts_by_window']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cohort-directory',required=True);p.add_argument('--output',required=True);a=p.parse_args();review(a.cohort_directory,a.output)
