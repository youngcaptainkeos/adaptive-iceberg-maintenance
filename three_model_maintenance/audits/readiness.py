"""Read-only existing-evidence census; never refits or reevaluates consumed test data."""
import argparse
import ast
import csv
import hashlib
import json
import math
import traceback
from itertools import product
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from three_model_maintenance.contracts import QUERY_FEATURES,require

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def csv_rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))

def audit(config):
    cfg=json.loads(config.read_text());require(cfg['schema_version']=='three_model_readiness_v1','Unknown registration')
    base=config.parent
    def verified(spec):
        path=(base/spec['path']).resolve();require(sha(path)==spec['sha256'],'Changed evidence '+str(path));return path
    out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False)
    report={'status':'running','started_utc':datetime.now(timezone.utc).isoformat(),'fit_performed':False,
            'test_reevaluated':False,'scheduler_authorized':False,'failures':[]}
    try:
        paths={name:verified(spec) for name,spec in cfg['inputs'].items()}
        manifest=json.loads(paths['export'].read_text());verification=json.loads(paths['verification'].read_text())
        require(manifest['status']=='raw_verified_candidates_only_not_accepted_training' and
                verification['status']=='verified_candidate_csv_raw_roundtrip_only' and
                verification['export_record_sha256']==sha(paths['export']),'Missing raw verification')
        d=paths['export'].parent
        for name,h in manifest['artifact_sha256'].items():require(sha(d/name)==h,'Changed candidate artifact '+name)
        episodes=csv_rows(d/'episodes.csv');queries=csv_rows(d/'queries.csv');rewrites=csv_rows(d/'rewrites.csv')
        require((len(episodes),len(queries),len(rewrites))==(manifest['episodes'],manifest['query_rows'],manifest['rewrite_rows']), 'Count differs')
        intervals=sorted({(datetime.fromisoformat(r['source_interval_start_utc']),datetime.fromisoformat(r['source_interval_end_utc'])) for r in episodes})
        families=[]
        for start,end in intervals:
            require(start<end,'Invalid source interval')
            if families and start<families[-1][1]:families[-1][1]=max(end,families[-1][1])
            else:families.append([start,end])
        assignment={}
        for r in episodes:
            start,end=map(datetime.fromisoformat,(r['source_interval_start_utc'],r['source_interval_end_utc']))
            matches=[i for i,(a,b) in enumerate(families) if a<=start and end<=b]
            require(len(matches)==1 and r['experiment_id'] not in assignment,'Ambiguous/reused episode');assignment[r['experiment_id']]=matches[0]
        require(len(families)==verification['source_family_count'],'Family census differs')
        consumed=json.loads(paths['consumed_test'].read_text())
        require(consumed['test_family_evaluated'] is True and consumed['refit_performed'] is False and
                consumed['status']=='completed_single_reserved_family_evaluation_uncalibrated','Unknown consumed-test ledger')
        consumed_ids=set(consumed['results']['query']['test_episodes'])
        require(consumed_ids<=assignment.keys(),'Consumed test has unknown episode')
        consumed_families=sorted({assignment[e] for e in consumed_ids})
        census=defaultdict(lambda:{'all':Counter(),'eligible':Counter(),'episodes':defaultdict(set),'eligible_episodes':defaultdict(set)})
        ids=set();missing_history=[]
        allowed=set(manifest['query_predictor_allowlist']);require(allowed<=QUERY_FEATURES,'Unsupported/post-decision export feature')
        for r in queries:
            eid=r['experiment_id'];mid=r['measurement_id'];require(eid in assignment and (eid,mid) not in ids,'Unknown/duplicate query');ids.add((eid,mid))
            require(r['maintenance_client_pending_at_feature_time'] in ('True','False'),'Unknown maintenance state')
            require(math.isfinite(float(r['service_target_ms'])) and float(r['service_target_ms'])>0 and int(r['client_elapsed_ns'])>0,'Invalid measured target')
            for field in allowed-{'maintenance_client_pending_at_feature_time'}:
                require(math.isfinite(float(r[field])),'Missing/nonfinite predictor '+field)
            start,end=map(datetime.fromisoformat,(r['source_interval_start_utc'],r['source_interval_end_utc']))
            a,b=families[assignment[eid]];require(a<=start<end<=b,'Query source family binding differs')
            feature=int(r['feature_monotonic_ns']);eligible=True
            for seconds in (60,300):
                require(int(r[f'last_available_sample_end_monotonic_ns_{seconds}s'])<=feature,'Future telemetry predictor')
                complete=r[f'offered_history_complete_{seconds}s'];require(complete in ('True','False'),'Unknown history completeness')
                if complete=='True':require(r[f'offered_count_{seconds}s']!='','Missing complete-history count')
                else:eligible=False
            if not eligible:missing_history.append({'experiment_id':eid,'measurement_id':mid})
            key=(r['query_id'],r['file_count'],r['maintenance_client_pending_at_feature_time'])
            item=census[assignment[eid]];item['all'][key]+=1;item['episodes'][key].add(eid)
            if eligible:item['eligible'][key]+=1;item['eligible_episodes'][key].add(eid)
        observed={key for item in census.values() for key in item['all']}
        cells=list(product(sorted({k[0] for k in observed}),sorted({k[1] for k in observed}),('False','True')))
        report['families']=[{'index':i,'source_start_utc':a.isoformat(),'source_end_utc':b.isoformat(),
            'future_role':'consumed_history_only','was_previous_test':i in consumed_families,
            'support':[{'query_id':q,'file_count':f,'client_pending':p,
                'rows':census[i]['all'][(q,f,p)],'complete_history_rows':census[i]['eligible'][(q,f,p)],
                'episodes':sorted(census[i]['episodes'][(q,f,p)]),'complete_history_episodes':sorted(census[i]['eligible_episodes'][(q,f,p)])}
                for q,f,p in cells]} for i,(a,b) in enumerate(families)]
        for i in range(len(families)):
            for r in report['families'][i]['support']:
                opposite=(r['query_id'],r['file_count'],'False' if r['client_pending']=='True' else 'True')
                r['opposite_condition_complete_history_rows']=census[i]['eligible'][opposite]
        forecast=json.loads(paths['forecast_diagnostic'].read_text())
        require(forecast['status']=='completed_diagnostic_only','Unknown forecast evidence')
        report['forecast']={'status':'historical_aggregate_diagnostic_not_deployed_C',
            'registered_horizon_bins':forecast['configuration']['horizon_bins'],
            'original_sql_mix_supported':False,'ingestion_supported':False,'future_cpu_load_supported':False,
            'no_forecast_model_loaded':True}
        for source in Path(__file__).resolve().parents[1].rglob('*.py'):ast.parse(source.read_text(),filename=str(source))
        report.update(status='completed_readiness_new_independent_data_required',query_rows=len(queries),rewrite_rows=len(rewrites),
            episode_count=len(episodes),source_family_count=len(families),consumed_test_family_indices=consumed_families,
            missing_complete_history_query_ids=missing_history,
            condition_definition='Observed client maintenance pending; not active engine overlap or causal treatment',
            eligible_A_rows=sum(v for i in census.values() for k,v in i['eligible'].items() if k[2]=='True'),
            eligible_B_rows=sum(v for i in census.values() for k,v in i['eligible'].items() if k[2]=='False'),
            rewrite_counts_by_family=dict(Counter(assignment[r['experiment_id']] for r in rewrites)),
            new_fitting_authorized=False,blockers=[
                'All existing cost families are consumed history; register fresh development/calibration/test roles before any new candidate fit.',
                'A/B support census is marginal/joint descriptive evidence, not matched causal A-minus-B labels.',
                'Export lacks planned rewrite size/progress for richer A predictors; do not invent or substitute post-action actual bytes.',
                'Raw feature availability is recorded in episode monotonic domains; export alone cannot produce a cross-process UTC predictor request.',
                'C lacks original SQL mix/ingestion and calibrated deployment evidence; count forecasts are not CPU load.',
                'Sparse independent rewrite/maintenance episodes and single client/scale limit model readiness.'],
            limitations=['Existing export/verification hashes reused; this is not a new full raw Spark audit.','No model weights loaded, fitting, scoring, physical SQL or old-test rerun.'])
    except Exception as exc:
        report.update(status='failed_preserved',error=str(exc),traceback=traceback.format_exc());raise
    finally:
        report['ended_utc']=datetime.now(timezone.utc).isoformat();report['protocol_sha256']=sha(config)
        report['code_sha256']={str(p.relative_to(Path(__file__).resolve().parents[1])):sha(p) for p in Path(__file__).resolve().parents[1].rglob('*.py')}
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ('families','missing_complete_history_query_ids','traceback')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);audit(p.parse_args().config.resolve())
