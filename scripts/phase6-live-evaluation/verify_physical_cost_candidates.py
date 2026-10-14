#!/usr/bin/env python3
"""Read-only candidate CSV round-trip checks against actual raw episode events."""
import argparse,csv,json
from pathlib import Path
from experiment_validation import load_json,verified_file,require,sha256
from statement_timing import completed_statements


def verify(config,directory,output):
    cfg,base=load_json(config);directory=Path(directory);manifest=json.loads((directory/'export_record.json').read_text())
    require(manifest['schema_version']==cfg['schema_version']=='physical_cost_candidate_export_v1' and manifest['calibrated_training_accepted'] is False and manifest['scheduler_authorized'] is False,'Unsupported/promoted candidate export')
    require(json.loads((directory/'config.json').read_text())==cfg,'Executed export registration differs')
    for name,digest in manifest['artifact_sha256'].items():require(sha256(directory/name)==digest,'Candidate artifact changed')
    raw={};source_intervals=[]
    for spec in cfg['successful_arm_results']:
        receipt=verified_file(spec,base);episode=receipt.parent;ecfg=json.loads((episode/'config.json').read_text());eid=ecfg['experiment_id'];rows=[json.loads(line) for line in (episode/'events.jsonl').open()]
        require(sha256(episode/'events.jsonl')==manifest['source_evidence'][eid]['events_sha256'],'Raw episode changed')
        raw[eid]=(rows,completed_statements([episode/'events.jsonl']))
        mapping=json.loads((episode/'mapping_record.json').read_text());source_intervals.append((mapping['source_interval_start_utc'],mapping['source_interval_end_utc']))
    queries=list(csv.DictReader((directory/'queries.csv').open()));rewrites=list(csv.DictReader((directory/'rewrites.csv').open()));episodes=list(csv.DictReader((directory/'episodes.csv').open()));seen=set()
    for row in queries:
        eid=row['experiment_id'];mid=row['measurement_id'];require((eid,mid) not in seen,'Duplicate exported query');seen.add((eid,mid));rows,completed=raw[eid]
        observations=[r for r in rows if r['kind']=='query_observation' and r['measurement_id']==mid];require(len(observations)==1,'Missing raw query observation');observation=observations[0];statement=completed[(eid,mid)]
        ns=int(row['feature_monotonic_ns']);require(ns==observation['recorded']['monotonic_ns']<=statement['client_execute_start']['monotonic_ns'],'Feature clock leakage')
        require(float(row['service_target_ms'])==statement['client_elapsed_ns']/1e6 and int(row['client_elapsed_ns'])==statement['client_elapsed_ns'],'Query target differs from actual clock')
        require(int(row['query_id'])==statement['query_id'] and all(int(row[k])==observation['file_state'][k] for k in ('file_count','record_count','total_bytes')),'Measured query/state changed')
        offers=[r for r in rows if r['kind']=='queue_transition' and r['state']=='offered' and r['measurement_id']==mid];require(len(offers)==1 and offers[0]['source']['source_query_id']==row['source_query_id'],'Source identity changed')
        clock=[r for r in rows if r['kind']=='replay_clock'][0]
        for w in observation['windows']:
            seconds=w['window_seconds']
            for field in ('cpu_busy_fraction','memory_used_fraction','read_bytes_per_second','write_bytes_per_second'):require(float(row[f'{field}_{seconds}s'])==w[field],'Window values changed')
            full=ns-clock['start_monotonic_ns']>=seconds*1000000000;require(row[f'offered_history_complete_{seconds}s']==str(full),'History coverage flag changed')
            count=row[f'offered_count_{seconds}s']
            if not full:require(count=='','Incomplete demand history imputed')
            else:
                actual=sum(r['kind']=='queue_transition' and r['state']=='offered' and ns-seconds*1000000000<r['recorded']['monotonic_ns']<=ns for r in rows)
                require(int(count)==actual,'Observed demand count changed')
    for row in rewrites:
        rows,completed=raw[row['experiment_id']];statement=completed[(row['experiment_id'],row['measurement_id'])];values=dict(zip(statement['columns'],statement['rows'][0]))
        require(float(row['rewrite_service_target_ms'])==statement['client_elapsed_ns']/1e6,'Rewrite target clock changed')
        for name,column in (('rewritten_data_files_count','actual_rewritten_files_target'),('added_data_files_count','actual_added_files_target'),('rewritten_bytes_count','actual_rewritten_bytes_target')):require(int(row[column])==values[name],'Rewrite work target changed')
    require(len(queries)==manifest['query_rows'] and len(rewrites)==manifest['rewrite_rows'] and len(episodes)==manifest['episodes']==len(raw),'Candidate coverage differs')
    require(not any('target' in col or 'diagnostic' in col or col in ('source_query_id','experiment_id','measurement_id') for col in manifest['query_predictor_allowlist']),'Outcome/identity leakage in predictor allowlist')
    # Connected source-interval families, not the number of rows, determine split diversity.
    families=[]
    for start,end in sorted(set(source_intervals)):
        if families and start<families[-1][1]:families[-1][1]=max(families[-1][1],end)
        else:families.append([start,end])
    inventory=json.loads((directory/'attempt_inventory.json').read_text())
    report={'status':'verified_candidate_csv_raw_roundtrip_only','query_rows':len(queries),'rewrite_rows':len(rewrites),'episodes':len(episodes),'overlapping_source_interval_families':families,'source_family_count':len(families),'fully_observed_300s_demand_rows':sum(r['offered_history_complete_300s']=='True' for r in queries),'failed_attempts_retained':[r for r in inventory if r.get('included_in_candidate_rows') is False],'calibrated_training_accepted':False,'export_record_sha256':sha256(directory/'export_record.json'),'verification_code_sha256':sha256(Path(__file__))}
    with Path(output).open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--export-directory',required=True);p.add_argument('--output',required=True);a=p.parse_args();verify(a.config,a.export_directory,a.output)
