"""Rebuild real plan/UUID/snapshot/availability features and matched-state support."""
import csv
import json
from collections import Counter
from pathlib import Path
from queue_aware_maintenance.core.common import require,sha,write_json
from queue_aware_maintenance.observability.complexity_adapter import original,sql_hash
from three_model_maintenance.preparation.query_plan import parse


def plan_records(events):
    statements={r['measurement_id']:r for r in events if r['kind']=='statement_completed'}
    requests={r['measurement_id']:r for r in events if r['kind']=='statement_requested'}
    receipts={};publications={}
    for r in events:
        if r['kind']=='complexity_plan_receipt':
            require(r['plan_id'] not in receipts,'Duplicate plan receipt')
            ids=r['explain_measurement_ids'];require(len(ids)==2 and len(set(ids))==2,'Ambiguous actual EXPLAIN identity')
            raw=[]
            for mode,mid in zip(('FORMATTED','COST'),ids):
                req,end=requests[mid],statements[mid]
                require(req['role']==end['role']=='complexity_plan' and req['query_id']==r['query_id'] and req['sql']=='EXPLAIN '+mode+' '+r['sql'],'Plan is not bound to actual SQL')
                require(end['fetch_end']['monotonic_ns']<=r['recorded']['monotonic_ns'],'Plan receipt precedes actual output')
                require(end['rows'] and all(len(x)==1 and isinstance(x[0],str) for x in end['rows']),'Missing real plan text')
                raw.append('\n'.join(row[0] for row in end['rows']))
            require(parse(*raw)==r['parsed'] and sql_hash(r['sql'])==r['sql_sha256'],'Plan feature/raw reconstruction differs')
            require(r['parsed']['estimated_rows'] is None and r['parsed']['estimated_bytes'] is None,'Unvalidated optimizer statistics became predictors')
            receipts[r['plan_id']]=r
        elif r['kind']=='complexity_plan_publication':
            require(r['plan_id'] in receipts and r['plan_id'] not in publications,'Ambiguous/out-of-order plan publication')
            require(receipts[r['plan_id']]['recorded']['monotonic_ns']<=r['receipt_persisted_by']['monotonic_ns']<=r['recorded']['monotonic_ns'],'Invalid durable publication chronology')
            publications[r['plan_id']]=r
    require(receipts and set(receipts)==set(publications),'Missing actual plans/publications')
    return statements,requests,receipts,publications


def audit(directory,output):
    d=Path(directory);out=Path(output);out.mkdir(parents=True,exist_ok=False)
    cfg=json.loads((d/'config.json').read_text());base=original(cfg)
    # Preserve the original full-cohort SQL/result/task/telemetry/FIFO/area gate.
    sysroot=Path(cfg['physical_runtime'])/'queue_aware_maintenance'
    import sys
    sys.path.insert(0,str(sysroot))
    from audit_episode import audit as original_audit
    from compare_study import reconstruct_decisions
    actual=original_audit(d);actual['revision']=cfg['physical_revision']
    require(actual==json.loads((d/'result.json').read_text()),'Original full raw result differs')
    replay=reconstruct_decisions(d)
    events=[json.loads(line) for line in (d/'events.jsonl').open()]
    protocol=[r for r in events if r['kind']=='complexity_adapter_protocol'];require(len(protocol)==1,'Missing unique complexity adapter registration')
    require(protocol[0]['source_sha256']==cfg['complexity_source_sha256'] and protocol[0]['runtime_predictions_changed'] is False,'Changed feature source/claims')
    for n,h in cfg['complexity_source_sha256'].items():require(sha(d/'complexity_code'/n)==h,'Changed archived complexity source')
    statements,requests,receipts,publications=plan_records(events)
    positions={id(r):i for i,r in enumerate(events)}
    bindings={r['measurement_id']:r for r in events if r['kind']=='complexity_query_binding'}
    require(len(bindings)==sum(r['kind']=='complexity_query_binding' for r in events),'Duplicate query binding')
    observations={r['measurement_id']:r for r in events if r['kind']=='query_observation'}
    queries={r['measurement_id']:r for r in actual['queries']};require(set(bindings)==set(observations)==set(queries),'Missing/extra actual feature bindings')
    clocks=[r for r in events if r['kind']=='cohort_clock'];require(len(clocks)==1,'Missing cohort clock');lo=clocks[0]['start_monotonic_ns']
    offered=[r for r in events if r['kind']=='cohort_queue_transition' and r['state']=='offered']
    maintenance_requests=[r for r in events if r['kind']=='statement_requested' and r['role']=='maintenance']
    maintenance_finished=[r for r in events if r['kind']=='statement_completed' and r['role']=='maintenance']
    counts=Counter();complete=Counter();rows=[]
    for mid,q in queries.items():
        b,o=bindings[mid],observations[mid];p=receipts[b['plan_id']];published=publications[b['plan_id']];req=requests[mid];ended=statements[mid]
        require(p['query_id']==b['query_id']==o['query_id']==q['query_id'],'Feature/query identity differs')
        require(p['snapshot_id']==b['snapshot_id']==o['snapshot_id'] and p['sql']==req['sql'] and p['sql_sha256']==b['sql_sha256']==sql_hash(req['sql']),'Wrong exact SQL/snapshot feature binding')
        require(b['features']==p['parsed']['features'],'Changed plan features')
        require(published['recorded']['monotonic_ns']<=b['available_at']['monotonic_ns']<=b['recorded']['monotonic_ns']<=o['recorded']['monotonic_ns']<=req['request_start']['monotonic_ns'],'Post-query or unavailable plan feature')
        require(positions[id(published)]<positions[id(b)]<positions[id(o)],'Plan was not durably recorded before observation')
        t=o['recorded']['monotonic_ns'];oi=positions[id(o)];pending=any(r['recorded']['monotonic_ns']<=t and positions[id(r)]<oi and not any(e['measurement_id']==r['measurement_id'] and e['recorded']['monotonic_ns']<=t and positions[id(e)]<oi for e in maintenance_finished) for r in maintenance_requests)
        row={'experiment_id':cfg['experiment_id'],'source_family':cfg['source_overlap_family'],'source_query_id':q['source_query_id'],'measurement_id':mid,'query_id':q['query_id'],'snapshot_id':o['snapshot_id'],**o['file_state'],'maintenance_client_pending_at_feature_time':pending,'service_target_ms':q['service_ns']/1e6,'response_target_ms':q['response_ns']/1e6,'plan_id':b['plan_id'],'plan_available_monotonic_ns':b['available_at']['monotonic_ns'],'feature_monotonic_ns':t,**b['features']}
        history=True
        for w in (60,300):
            present=t-lo>=w*10**9;row[f'offered_history_complete_{w}s']=present
            row[f'offered_count_{w}s']=sum(t-w*10**9<=x['actual_transition']['monotonic_ns']<t and x['recorded']['monotonic_ns']<=t and positions[id(x)]<oi for x in offered) if present else None
            history &= present
        for w in o['windows']:
            n=w['window_seconds']
            for key in ('cpu_busy_fraction','memory_used_fraction','read_bytes_per_second','write_bytes_per_second'):
                require(key in w,'Missing measured host window '+key);row[f'{key}_{n}s']=w[key]
        key=(str(row['file_count']),str(pending),str(row['query_id']));counts[key]+=1
        if history:complete[key]+=1
        rows.append(row)
    with (out/'queries.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    support=[{'file_count':int(k[0]),'client_pending':k[1]=='True','query_id':int(k[2]),'observations':n,'complete_offered_histories':complete[k]} for k,n in sorted(counts.items())]
    fragmented=cfg['initial_file_count'];pending_n=sum(x['observations'] for x in support if x['file_count']==fragmented and x['client_pending']);nonpending_n=sum(x['observations'] for x in support if x['file_count']==fragmented and not x['client_pending'])
    result={'status':'passed_raw_plan_binding_and_candidate_export_only','completed':len(rows),'actual_plan_receipts':len(receipts),'support':support,'fragmented_pending_observations':pending_n,'fragmented_nonpending_observations':nonpending_n,'observed_same_fragmented_layout_both_states':pending_n>0 and nonpending_n>0,'source_family':cfg['source_overlap_family'],'plan_features_used_by_runtime_predictor':False,'training_accepted':False,'calibration_accepted':False,'original_result_sha256':sha(d/'result.json'),'events_sha256':sha(d/'events.jsonl'),'queries_sha256':sha(out/'queries.csv'),'decision_replay':replay,'limitations':cfg['complexity_limitations']}
    write_json(out/'result.json',result)
    return result
