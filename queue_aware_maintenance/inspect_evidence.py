#!/usr/bin/env python3
"""Audit actual prior physical labels and prospective source capacity, no SQL."""
import argparse,json,csv,statistics,collections
from pathlib import Path
from datetime import datetime,timedelta
from common import checked,sha,write_json,require,now

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'running','started_utc':now(),'new_physical_execution':False,'model_accepted':False}
 try:
  export=checked(cfg['candidate_export']);receipt=json.loads(export.read_text());verification=json.loads(checked(cfg['candidate_verification']).read_text());require(verification['status']=='verified_candidate_csv_raw_roundtrip_only' and verification['export_record_sha256']==sha(export),'Missing independent source verification')
  for name,h in receipt['artifact_sha256'].items():require(sha(export.parent/name)==h,'Changed physical CSV')
  cells=collections.defaultdict(list);episodes=collections.defaultdict(set)
  with (export.parent/'queries.csv').open() as f:
   for r in csv.DictReader(f):
    v=float(r['service_target_ms']);require(v>0,'Nonpositive real duration');key=(int(r['query_id']),int(r['file_count']),r['maintenance_client_pending_at_feature_time']);require(key[2] in ('True','False'),'Unknown pending state');cells[key].append(v);episodes[key].add(r['experiment_id'])
  report['query_cells']=[{'query_id':k[0],'file_count':k[1],'maintenance_client_pending':k[2]=='True','rows':len(v),'episode_count':len(episodes[k]),'episode_ids':sorted(episodes[k]),'median_service_ms':statistics.median(v),'minimum_ms':min(v),'maximum_ms':max(v)} for k,v in sorted(cells.items())]
  with (export.parent/'rewrites.csv').open() as f:rewrites=list(csv.DictReader(f))
  report['rewrites']=[{'experiment_id':r['experiment_id'],'initial_files':int(r['file_count']),'added_files':int(r['actual_added_files_target']),'duration_ms':float(r['rewrite_service_target_ms'])} for r in rewrites]
  ep=list(csv.DictReader((export.parent/'episodes.csv').open()));report['previous_episode_intervals']=sorted({(r['source_interval_start_utc'],r['source_interval_end_utc']) for r in ep})
  cohort=json.loads(checked(cfg['cohort']).read_text());arrivals=checked(cfg['arrivals']);origin=datetime.fromisoformat(cohort['observation_origin_utc']);start=origin+timedelta(days=cfg['prospective_day_index']);end=start+timedelta(seconds=cfg['prospective_window_seconds']*cfg['prospective_windows'])
  require(end<=datetime.fromisoformat(cohort['training_end_utc']),'Prospective physical windows cross existing forecast training partition');require(all(not(start<datetime.fromisoformat(b) and datetime.fromisoformat(a)<end) for a,b in report['previous_episode_intervals']),'Reuses known cost windows')
  counts=[0]*cfg['prospective_windows'];total=0;previous=None;selected=[]
  with arrivals.open() as f:
   for r in csv.DictReader(f):
    t=datetime.fromisoformat(r['arrival_utc']);require(previous is None or t>=previous,'Unsorted real arrivals');previous=t;total+=1
    if start<=t<end:
     i=int((t-start).total_seconds())//cfg['prospective_window_seconds'];counts[i]+=1
  require(total==cohort['selected_total_arrivals'] and all(counts),'Incomplete/no actual arrival source')
  report.update(status='audited_actual_cost_support_and_new_source_capacity',prospective_intervals=[{'start':(start+timedelta(seconds=i*cfg['prospective_window_seconds'])).isoformat(),'end':(start+timedelta(seconds=(i+1)*cfg['prospective_window_seconds'])).isoformat(),'arrivals':counts[i]} for i in range(cfg['prospective_windows'])],limitations=['Previously used test cost family now explicitly development evidence; new day6cost outcomes untouched.','Two contiguous windows share one source day; not independent-day calibration.','Client-pending conditional duration is observational, not causal interference identification.','No model fit, SQL or physical table operation in this audit.'])
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:
  report.update(ended_utc=now(),protocol_sha256=sha(protocol),code_sha256=sha(__file__));write_json(out/'result.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
