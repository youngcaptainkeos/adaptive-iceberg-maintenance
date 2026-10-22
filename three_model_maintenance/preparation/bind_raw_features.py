"""Bind existing query candidates to raw capture/call evidence, without training."""
import argparse,csv,hashlib,json,math,traceback
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from three_model_maintenance.contracts import require,timestamp

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def run(config):
    cfg=json.loads(config.read_text());require(cfg['schema_version']=='three_model_raw_feature_binding_v1','Unknown protocol')
    base=config.parent;out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False)
    report={'status':'running','fit_performed':False,'test_scored':False,'runtime_adapter_accepted':False,
            'started_utc':datetime.now(timezone.utc).isoformat(),'episodes':[],'ambiguous_candidate_ids':[]}
    try:
        def verified(spec):
            p=(base/spec['path']).resolve();require(sha(p)==spec['sha256'],'Changed registered input '+str(p));return p
        manifest_path=verified(cfg['export']);manifest=json.loads(manifest_path.read_text());d=manifest_path.parent
        verify=verified(cfg['independent_export_verification']);v=json.loads(verify.read_text())
        require(v['status']=='verified_candidate_csv_raw_roundtrip_only' and v['export_record_sha256']==sha(manifest_path),'Missing export verification')
        for n,h in manifest['artifact_sha256'].items():require(sha(d/n)==h,'Changed export artifact '+n)
        with (d/'queries.csv').open() as f:rows=list(csv.DictReader(f))
        byepisode=defaultdict(dict)
        for row in rows:
            eid,mid=row['experiment_id'],row['measurement_id'];require(mid not in byepisode[eid],'Duplicate candidate');byepisode[eid][mid]=row
        require(set(byepisode)==set(manifest['source_evidence']),'Missing/extra episode source binding')
        count=0
        with (out/'bound_features.jsonl').open('x') as stream:
            for eid,expected in sorted(byepisode.items()):
                spec=manifest['source_evidence'][eid];result=(base/Path(spec['registered_result_spec']['path'])).resolve()
                require(sha(result)==spec['result_sha256']==spec['registered_result_spec']['sha256'],'Changed physical receipt')
                raw=result.parent/'events.jsonl';require(sha(raw)==spec['events_sha256'],'Changed raw events')
                requests={};completed={};observations={};state={};offers=[];seen_queries=set();checks=[];clock=None;anomalies=0
                with raw.open() as source:
                    for line_no,line in enumerate(source,1):
                        event=json.loads(line);require(event['experiment_id']==eid,'Raw experiment identity differs');kind=event['kind'];mid=event.get('measurement_id')
                        if kind=='replay_clock':require(clock is None,'Duplicate clock');clock=event
                        if kind=='queue_transition':
                            state[event['source']['source_query_id']]=event['state']
                            if event['state']=='offered':offers.append(event['recorded']['monotonic_ns'])
                        if kind=='query_observation' and mid in expected:
                            require(mid not in observations,'Duplicate observation');require(clock is not None,'Missing replay clock')
                            row=expected[mid];feature=event['recorded'];require(int(row['feature_monotonic_ns'])==feature['monotonic_ns'],'Capture stamp differs')
                            require(event['query_id']==int(row['query_id']) and event['table']==row['table'] and str(event['snapshot_id'])==row['snapshot_id'],'Query/table/snapshot differs')
                            for field in ('file_count','record_count','total_bytes'):require(event['file_state'][field]==int(row[field]),'Layout differs '+field)
                            for ref in ('snapshot_measurement_id','file_inventory_measurement_id'):
                                require(event[ref] in completed,'Metadata evidence was not completed in prior log prefix')
                                require(completed[event[ref]]['fetch_end']['monotonic_ns']<=feature['monotonic_ns'],'Future metadata')
                            pending=[m for m,e in requests.items() if e['role']=='maintenance' and m not in completed]
                            mismatch=[]
                            if (row['maintenance_client_pending_at_feature_time']=='True')!=bool(pending):mismatch.append('timestamp_derived_pending_differs_from_prior_log_prefix')
                            if int(row['queue_depth_at_feature_time'])!=sum(s=='queued' for s in state.values()):mismatch.append('timestamp_derived_queue_differs_from_prior_log_prefix')
                            require(len(event['windows'])==2 and {w['window_seconds'] for w in event['windows']}=={60,300},'Missing/duplicate host windows')
                            window_evidence=[]
                            for w in event['windows']:
                                seconds=w['window_seconds'];require(w['last_available_sample_end_monotonic_ns']<=w['measured_at']['monotonic_ns']<=feature['monotonic_ns'],'Future host sample/calculation')
                                require(timestamp(w['measured_at']['utc'])<=timestamp(feature['utc']),'Host wall clock inversion')
                                for field in ('cpu_busy_fraction','memory_used_fraction','read_bytes_per_second','write_bytes_per_second','covered_seconds'):
                                    value=float(row[f'{field}_{seconds}s']);require(math.isfinite(value) and value==w[field],'Host value differs '+field)
                                require(int(row[f'last_available_sample_end_monotonic_ns_{seconds}s'])==w['last_available_sample_end_monotonic_ns'],'Host sample frontier differs')
                                complete=feature['monotonic_ns']-clock['start_monotonic_ns']>=seconds*1000000000
                                require((row[f'offered_history_complete_{seconds}s']=='True')==complete,'History completeness differs')
                                if complete:
                                    observed=sum(feature['monotonic_ns']-seconds*1000000000<t<=feature['monotonic_ns'] for t in offers)
                                    if int(row[f'offered_count_{seconds}s'])!=observed:mismatch.append(f'offered_count_{seconds}s_differs_from_prior_log_prefix')
                                else:require(row[f'offered_count_{seconds}s']=='','Incomplete count history must remain absent')
                                window_evidence.append({'seconds':seconds,'calculated_at':w['measured_at'],'last_sample_ns':w['last_available_sample_end_monotonic_ns']})
                            observations[mid]={'observation':event,'line':line_no,'pending_ids':pending,'issues':mismatch,'windows':window_evidence}
                        if kind=='statement_requested':
                            require(mid not in requests,'Duplicate raw request');requests[mid]=event
                        if kind=='statement_completed':
                            require(mid not in completed,'Duplicate raw completion');completed[mid]=event
                            if mid in expected:
                                require(mid in observations and mid in requests and event['role']=='trace_query','Missing prior feature/intent')
                                info=observations[mid];row=expected[mid];obs=info['observation'];feature=obs['recorded'];start=event['client_execute_start']
                                require(feature['monotonic_ns']<=requests[mid]['request_start']['monotonic_ns']<=start['monotonic_ns']<=event['fetch_end']['monotonic_ns'],'Feature/intent/call order differs')
                                require(timestamp(feature['utc'])<=timestamp(start['utc']),'Capture/call wall clock inversion')
                                require(start['utc']==row['query_start_utc'] and event['client_elapsed_ns']==int(row['client_elapsed_ns']),'Actual call identity/target differs')
                                require(event['client_elapsed_ns']==event['fetch_end']['monotonic_ns']-start['monotonic_ns'],'Actual duration differs')
                                require(float(row['service_target_ms'])==event['client_elapsed_ns']/1e6,'Measured target differs')
                                issues=info['issues'];anomalies+=bool(issues)
                                if issues:report['ambiguous_candidate_ids'].append({'experiment_id':eid,'measurement_id':mid,'reasons':issues})
                                bound={'schema_version':'three_model_historical_feature_evidence_v1','experiment_id':eid,'measurement_id':mid,
                                    'source_events_sha256':spec['events_sha256'],'source_result_sha256':spec['result_sha256'],
                                    'observation_line':info['line'],'intent':requests[mid]['recorded'],'observation_capture':feature,
                                    'host_calculation_evidence':info['windows'],'query_client_call_start':start,
                                    'feature_availability_exact_utc':None,'feature_availability_upper_bound':start,
                                    'availability_semantics':'Capture timestamps precede log fsync completion; actual call start is a recorded later bound, not invented exact availability.',
                                    'prior_log_pending_ids':info['pending_ids'],'candidate_binding_issues':issues,
                                    'historical_binding_consistent':not issues,'fresh_training_eligible':False,'runtime_adapter_accepted':False}
                                stream.write(json.dumps(bound,allow_nan=False)+'\n');seen_queries.add(mid);count+=1
                require(seen_queries==set(expected),'Missing candidate completions');require(sha(raw)==spec['events_sha256'],'Raw changed during binding')
                report['episodes'].append({'experiment_id':eid,'bound_queries':len(seen_queries),'prefix_ambiguities':anomalies,'events_sha256':sha(raw)})
        require(count==manifest['query_rows'],'Bound row total differs')
        report.update(status='completed_historical_feature_binding_no_runtime_acceptance',bound_queries=count,
            ambiguity_count=len(report['ambiguous_candidate_ids']),bound_features_sha256=sha(out/'bound_features.jsonl'),
            limitations=['Existing consumed history only; no new independent training or test.','Monotonic chronology and timezone-aware recorded UTC checked; no external wall-clock calibration proof.','EventLog recorded stamps are capture points, not exact fsync publication times.','Prior-log-prefix agreement cannot alone prove application-thread state visibility or causal intervention.','Old CSVs unchanged; mismatches retained explicitly, never filled or silently relabeled.'])
    except Exception as exc:report.update(status='failed_preserved',error=str(exc),traceback=traceback.format_exc());raise
    finally:
        report['ended_utc']=datetime.now(timezone.utc).isoformat();report['protocol_sha256']=sha(config);report['source_sha256']=sha(Path(__file__))
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('episodes','ambiguous_candidate_ids','traceback')}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);run(p.parse_args().config.resolve())
