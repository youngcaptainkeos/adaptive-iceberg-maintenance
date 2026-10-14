#!/usr/bin/env python3
"""Describe audited real episode contrasts, retaining failed attempts and uncertainty limits."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import statistics
from experiment_validation import require, sha256
from statement_timing import completed_statements


def review(directory, output):
    directory=Path(directory).resolve()
    cfg=json.loads((directory/'config.json').read_text())
    result=json.loads((directory/'result.json').read_text())
    require(result['schema_version']==cfg['schema_version']=='action_order_repeatability_pilot_v1','Unknown cohort')
    require(result['status'] in ('completed_registered_diagnostic_episodes_only','stopped_after_failed_gate_preserve_all'),'Active/unrecognized cohort')
    for name,digest in result['code_sha256'].items():require(sha256(directory/'code'/name)==digest,'Frozen cohort code changed')
    attempts=result['attempts'];require(len(attempts)<=len(cfg['registered_order']),'Extra unregistered attempts')
    observations=[];failures=[];input_hashes={'cohort_result':sha256(directory/'result.json'),'cohort_config':sha256(directory/'config.json')}
    for index,attempt in enumerate(attempts,start=1):
        require(attempt['index']==index and attempt['action_order']==cfg['registered_order'][index-1]
                and attempt['protocol_sha256']==cfg['episode_configs'][index-1]['sha256'],'Attempt registration differs')
        if attempt['status']!='passed_measurement_and_raw_export_only':
            failures.append({'index':index,'experiment_id':attempt['experiment_id'],'status':attempt['status'],
                             'returncode':attempt.get('returncode'),'raw_directory':attempt['raw_directory']})
            continue
        # Resolve mirrored artifacts by experiment ID, not worker3 absolute paths.
        raw=directory.parent/attempt['experiment_id'];export=directory/f'episode_{index:02d}_export'
        require(sha256(raw/'result.json')==attempt['result_sha256']
                and sha256(raw/'config.json')==attempt['protocol_sha256'],'Raw executed episode differs')
        manifest=json.loads((export/'export_record.json').read_text())
        require(sha256(export/'export_record.json')==attempt['export_record_sha256']
                and sha256(export/'query_observations.csv')==manifest['observations_sha256']
                and sha256(raw/'events.jsonl')==manifest['source_events_sha256'],'Export/raw digests differ')
        require(manifest['action_order_check']['action_order']==attempt['action_order'],'Export action order differs')
        measured=completed_statements([raw/'events.jsonl'])
        physical=json.loads((raw/'result.json').read_text());rows=list(csv.DictReader((export/'query_observations.csv').open()))
        require(len(rows)==4 and {r['role'] for r in rows}=={'control_before','during_rewrite','control_after_original_snapshot','compacted_layout'},'Missing/duplicate roles')
        by_role={r['role']:r for r in rows};latencies={}
        for role,row in by_role.items():
            record=measured[(attempt['experiment_id'],row['measurement_id'])]
            require(record['query_id']==cfg['query_id'] and int(row['client_elapsed_ns'])==record['client_elapsed_ns'],'Measured query identity/timing differs')
            latencies[role]=record['client_elapsed_ns']/1e6
            require(math.isfinite(latencies[role]) and latencies[role]>0,'Invalid observed duration')
        action=manifest['action_order_check']['maintenance_measurement_id'];rewrite=measured[(attempt['experiment_id'],action)]
        baseline=(latencies['control_before']+latencies['control_after_original_snapshot'])/2
        observation={'index':index,'experiment_id':attempt['experiment_id'],'action_order':attempt['action_order'],
                     'actual_query_latencies_ms':latencies,'bracketed_original_mean_ms':baseline,
                     'during_minus_bracketed_original_ms':latencies['during_rewrite']-baseline,
                     'relative_bracketed_contrast':(latencies['during_rewrite']-baseline)/baseline,
                     'compacted_minus_after_original_ms':latencies['compacted_layout']-latencies['control_after_original_snapshot'],
                     'rewrite_client_elapsed_ms':rewrite['client_elapsed_ns']/1e6,
                     'task_overlap_seconds':float(by_role['during_rewrite']['task_overlap_seconds']),
                     'original_state':physical['original']['file_state'],'compacted_state':physical['compacted']['file_state'],
                     'source_result_sha256':attempt['result_sha256']}
        observations.append(observation)
        input_hashes[attempt['experiment_id']]=dict(events=manifest['source_events_sha256'],result=attempt['result_sha256'],export=attempt['export_record_sha256'])
    cells={}
    for order in sorted(set(cfg['registered_order'])):
        values=[r['during_minus_bracketed_original_ms'] for r in observations if r['action_order']==order]
        cells[order]={'planned_episodes':Counter(cfg['registered_order'])[order],'passed_episodes':len(values),
                      'individual_signed_contrasts_ms':values,'mean_signed_contrast_ms':statistics.mean(values) if values else None,
                      'sample_standard_deviation_ms':statistics.stdev(values) if len(values)>1 else None,
                      'confidence_interval':None}
    complete=result['status']=='completed_registered_diagnostic_episodes_only'
    require(not complete or len(observations)==len(cfg['registered_order']) and not failures,'Incomplete claimed cohort')
    report={'schema_version':'action_order_repeatability_review_v1','status':'completed_diagnostic_only' if complete else 'partial_diagnostic_no_order_conclusion',
            'planned_episodes':len(cfg['registered_order']),'attempted_episodes':len(attempts),'passed_episodes':len(observations),
            'failures_preserved':failures,'not_attempted_count':len(cfg['registered_order'])-len(attempts),
            'cells':cells,'observations':observations,'input_sha256':input_hashes,'review_code_sha256':sha256(Path(__file__)),
            'cost_training_accepted':False,'limitations':cfg['analysis_limitations']}
    with Path(output).open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({'status':report['status'],'attempted':len(attempts),'passed':len(observations),'cells':cells}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cohort-directory',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();review(a.cohort_directory,a.output)
