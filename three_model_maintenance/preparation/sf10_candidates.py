"""Independent SF10 raw/publication/plan export; no fitting or promotion."""
import hashlib,json
from pathlib import Path
from three_model_maintenance.runtime.sf10_collect import audit
from three_model_maintenance.runtime.collector_bridge import audit_publications
from three_model_maintenance.preparation.query_plan import parse
from three_model_maintenance.training.data import read,save,sha
from three_model_maintenance.contracts import require


def export(directory,out,family,role):
    directory=Path(directory);out=Path(out);cfg=read(directory/'config.json')
    source_family=read(directory/'mapping_record.json')['source_family']
    require(source_family['id']==family and source_family['role']==role,'Candidate role differs from physical source registration')
    raw=audit(directory);pub=audit_publications(directory)
    terminal=read(directory/'result.json')
    require(raw['events_sha256']==terminal['events_sha256'] and pub==terminal['three_model_publication_audit'],'Raw/publication audit differs')
    events=[json.loads(s) for s in (directory/'events.jsonl').open()]
    calls={r['measurement_id']:r for r in events if r['kind']=='statement_completed'}
    requested={r['measurement_id']:r for r in events if r['kind']=='statement_requested'}
    plans={r['sql_sha256']:r for r in events if r['kind']=='sf10_plan_receipt'}
    for digest,p in plans.items():
        texts={m:'\n'.join(str(row[0]) for row in calls[mid]['rows']) for m,mid in p['explain_measurement_ids'].items()}
        require(parse(texts['FORMATTED'],texts['COST'])==p['parsed'] and hashlib.sha256(p['sql'].encode()).hexdigest()==digest,'Plan reconstruction differs')
        require(all(requested[mid]['sql']=='EXPLAIN '+m+' '+p['sql'] and calls[mid]['fetch_end']['monotonic_ns']<=p['recorded']['monotonic_ns'] for m,mid in p['explain_measurement_ids'].items()),'Plan call/availability differs')
    bindings={}
    for r in events:
        if r['kind']=='sf10_query_plan_binding':bindings[r['measurement_id']]=r
    clock=next(r['start_monotonic_ns'] for r in events if r['kind']=='replay_clock')
    offered=[r['actual_transition']['monotonic_ns'] for r in events if r['kind']=='queue_transition' and r['state']=='offered']
    rows=[]
    for event in events:
        if event['kind']!='three_model_feature_publication':continue
        p=event['publication'];mid=p['measurement_id']
        if mid not in calls:continue
        c=calls[mid];b=bindings[mid];plan=plans[b['sql_sha256']]
        require(requested[mid]['sql']==plan['sql'] and b['features']==plan['parsed']['features'] and plan['recorded']['monotonic_ns']<=b['available_at']['monotonic_ns']<=p['capture_at']['monotonic_ns']<=c['client_execute_start']['monotonic_ns'],'Plan/feature publication or actual SQL differs')
        captured=p['capture_at']['monotonic_ns'];complete=captured-clock>=300*10**9
        counts={str(w):sum(captured-w*10**9<t<=captured for t in offered) if captured-clock>=w*10**9 else None for w in (60,300)}
        rows.append(dict(experiment_id=cfg['experiment_id'],measurement_id=mid,family=family,role=role,
            features=dict(p['feature_values'],**b['features']),target_ms=c['client_elapsed_ns']/1e6,
            offered_history_complete=complete,offered_counts=counts,plan_sql_sha256=b['sql_sha256']))
    require(len(rows)==pub['completed_queries'] and len({r['measurement_id'] for r in rows})==len(rows),'Missing/duplicate candidate rows')
    out.mkdir(parents=True,exist_ok=False)
    save(out/'rows.json',rows)
    counts={s:sum(r['offered_history_complete'] and r['features']['maintenance_client_pending_at_feature_time']==(s=='A') for r in rows) for s in ('A','B')}
    save(out/'result.json',dict(status='audited_sf10_plan_candidates_only',rows=len(rows),eligible_counts=counts,
        family=family,role=role,rows_sha256=sha(out/'rows.json'),events_sha256=sha(directory/'events.jsonl'),
        physical_result_sha256=sha(directory/'result.json'),fit_authorized=False,calibration_accepted=False))
    return read(out/'result.json')
