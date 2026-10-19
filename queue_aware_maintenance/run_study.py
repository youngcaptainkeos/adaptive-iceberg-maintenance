#!/usr/bin/env python3
"""Bounded detached serial physical study; preserve every failed/unattempted arm."""
import argparse,json,subprocess,sys,os,shutil,fcntl,traceback
from pathlib import Path
from datetime import datetime,timezone
from common import checked,sha,write_json,require,now,notify,utc

def run(protocol,revision):
 cfg=json.loads(Path(protocol).read_text());root=Path(__file__).resolve().parent;repo=root.parent;require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==revision,'Frozen study HEAD mismatch');require(datetime.now(timezone.utc)<utc(cfg['no_new_episode_after_utc']),'New episode cutoff passed')
 preflight=json.loads(checked(cfg['runtime_preflight']).read_text());require(preflight['status']=='passed_actual_source_controller_runtime_preflight','Physical preflight not passed');prepared=json.loads(checked(cfg['core_preparation']).read_text());require(prepared['status']=='passed_real_evidence_core_preparation_and_reconstruction','Core evidence gate failed')
 if 'repair_validation' in cfg:
  repair=json.loads(checked(cfg['repair_validation']).read_text());require(repair['status']=='passed_real_readonly_multiset_container_repair' and repair['runner_sha256']==sha(root/'run_episode.py'),'Recovery requires actual-table repair proof for this runner');prior=json.loads(checked(cfg['preserved_failed_cohort']).read_text());require((prior['passed'],prior['failed'],prior['unattempted'])==(0,1,7),'Original failed inventory changed')
 version=cfg.get('policy_model_version','fluid_v1');require(prepared.get('policy_model_version','fluid_v1')==preflight.get('policy_model_version','fluid_v1')==cfg['episode_template'].get('policy_model_version','fluid_v1')==version,'Study/preparation/preflight/episode model versions differ')
 if 'resource_admission' in cfg:
  from resource_admission import evaluate
  admission=evaluate(cfg,prepared,repo);write_json(cfg['resource_admission']['receipt_path'],admission);require(admission['admitted_at_check'],'Resource/time admission rejected before any SQL or table creation')
 model=prepared['model'];checked(model);out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False);shutil.copyfile(protocol,out/'registration.json');protocols=out/'protocols';protocols.mkdir();lock=(repo/'results'/'.queue_aware_study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);code_hashes={str(p.relative_to(root)):sha(p) for p in root.rglob('*.py')};report={'status':'running','started_utc':now(),'pid':os.getpid(),'revision':revision,'protocol_sha256':sha(protocol),'planned_episodes':sum(len(x) for x in cfg['registered_orders']),'attempts':[],'unattempted':sum(len(x) for x in cfg['registered_orders']),'code_sha256':code_hashes,'model_accepted':False,'scheduler_research_claim_accepted':False};signatures={}
 def save():
  temp=out/'progress.tmp';temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(out/'progress.json')
  with (out/'progress_history.jsonl').open('a') as f:f.write(json.dumps(report)+'\n');f.flush();os.fsync(f.fileno())
 def alert(label,message,name):notify(label,message,out/name,cfg['notification_configuration'])
 episode_specs=[]
 try:
  for window,order in zip(prepared['workloads'],cfg['registered_orders']):
   require(sorted(order)==sorted(cfg['policies']),'Incomplete physical policy group')
   for policy in order:
    index=len(episode_specs)+1;eid=f"{cfg['experiment_prefix']}_{index:02d}";episode=dict(cfg['episode_template']);episode.update(schema_version='queue_aware_full_drain_episode_v1',experiment_id=eid,output_directory=str(out/'episodes'/eid),destination_table=f"local.experiment.{cfg['table_prefix']}_{index:02d}",policy=policy,mapping=window['mapping'],arrival_count=window['arrivals'],horizon_seconds=window['horizon_seconds'],source_start_utc=window['start'],source_end_utc=window['end'],forecast_history_freeze_utc=prepared['workloads'][0]['start'],model=model,observation_origin_utc=cfg['observation_origin_utc'],arrivals=cfg['arrivals'],query_ids=cfg['query_ids'],forecast_history_days=cfg['forecast_history_days'],decision_interval_seconds=cfg['decision_interval_seconds'],no_new_operation_after_utc=cfg['no_new_operation_after_utc'],limitations=cfg['limitations']);path=protocols/(eid+'.json');write_json(path,episode);episode_specs.append({'experiment_id':eid,'window_index':window['window_index'],'policy':policy,'protocol':{'path':str(path),'sha256':sha(path)},'table':episode['destination_table']})
  write_json(out/'execution_manifest.json',{'registered_utc':now(),'all_episodes':episode_specs,'revision':revision,'code_sha256':code_hashes,'primary_objective':'sum_response_ns_for_all_original_offered_queries_through_complete_drain','maintenance_allowance':'at_most_one_whole_table_rewrite_per_episode_noaction_allowed','no_invented_scalar_SLA_or_cloud_cost':True});save();alert('Capstone physical feasibility started',str(len(episode_specs))+' full-drain arms registered; actual source windows20min each, no dropped arrivals. All decisions/models remain exploratory.','start_notification.json')
  for item in episode_specs:
   require(datetime.now(timezone.utc)<utc(cfg['no_new_episode_after_utc']),'Launch cutoff reached; preserve unattempted arms')
   require(all(sha(root/name)==h for name,h in code_hashes.items()),'Frozen runtime code changed');checked(item['protocol']);attempt=dict(item,status='running',started_utc=now());report['attempts'].append(attempt);report['unattempted']-=1;save()
   logpath=out/(item['experiment_id']+'.log');receipt=out/(item['experiment_id']+'.failure_notification.json')
   command=[sys.executable,'-B','-u',str(repo/'scripts/phase6-live-evaluation/run_with_failure_alert.py'),'--label',item['experiment_id'],'--receipt',str(receipt),'--',sys.executable,'-B','-u',str(root/'run_episode.py'),'--protocol',item['protocol']['path'],'--expected-revision',revision]
   with logpath.open('x') as f:child=subprocess.Popen(command,cwd=repo,stdout=f,stderr=subprocess.STDOUT);attempt['wrapper_pid']=child.pid;attempt['log']=str(logpath);save();rc=child.wait()
   attempt.update(returncode=rc,ended_utc=now());result_path=out/'episodes'/item['experiment_id']/'result.json'
   if rc or not result_path.exists():attempt['status']='failed_preserved';report['status']='stopped_failed_physical_or_raw_gate_no_retry';save();break
   result=json.loads(result_path.read_text());require(result['status']=='audited_complete_real_full_drain_episode_only' and result['completed']==result['arrival_count'] and not result['unfinished'],'Incomplete physical cohort')
   signature=result['initial_layout_signature'];wi=item['window_index']
   if wi in signatures:require(signature==signatures[wi],'Matched initial file/layout signatures differ')
   else:signatures[wi]=signature
   attempt.update(status='passed_complete_physical_and_raw_audit',result_sha256=sha(result_path),sum_response_ns=result['sum_response_ns'],completed=result['completed'],maintenance_count=result['maintenance_count'],drain_end_after_start_seconds=result['drain_end_after_start_seconds']);save();alert('Capstone physical arm completed',item['experiment_id']+' '+item['policy']+': '+str(result['completed'])+' actual queries drained; raw audit passed. No causal/novelty claim.',item['experiment_id']+'.completion_notification.json')
  else:report['status']='completed_full_physical_feasibility_pending_independent_comparison'
 except Exception as e:report.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc())
 finally:
  report.update(ended_utc=now(),passed=sum(r['status']=='passed_complete_physical_and_raw_audit' for r in report['attempts']),failed=sum(r['status']!='passed_complete_physical_and_raw_audit' for r in report['attempts']));save();write_json(out/'result.json',report);lock.close();alert('Capstone feasibility collection status',report['status']+'; passed '+str(report['passed'])+' failed '+str(report['failed'])+' unattempted '+str(report['unattempted'])+'. Inspect saved raw evidence before claims.','terminal_notification.json');print(json.dumps({k:report[k] for k in ['status','passed','failed','unattempted']}),flush=True)
 return 0 if report['status']=='completed_full_physical_feasibility_pending_independent_comparison' else 1
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--expected-revision',required=True);a=p.parse_args();sys.exit(run(a.protocol,a.expected_revision))
