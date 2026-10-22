#!/usr/bin/env python3
"""Serial repeated physical timing study, durable progress, docs and ntfy."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,fcntl,json,os,subprocess,sys,traceback
from pathlib import Path
from datetime import timedelta
from queue_aware_maintenance.core.common import checked,sha,require,write_json,now,utc,notify

def timing_details(directory):
 clock=None;action=None
 with (Path(directory)/'events.jsonl').open() as f:
  for line in f:
   if '"kind": "cohort_clock"' in line:clock=json.loads(line)['start_monotonic_ns']
   elif '"kind": "statement_completed"' in line and '"role": "maintenance"' in line:action=json.loads(line)
 return {'actual_rewrite_start_after_arrival_clock_seconds':None if action is None else (action['client_execute_start']['monotonic_ns']-clock)/1e9,'actual_rewrite_call_seconds':None if action is None else action['client_elapsed_ns']/1e9}

def append_docs(cfg,heading,body):
 repo=Path(cfg['canonical_repository']);names=['docs/methodology_working_doc.md','docs/updated_methodology_working_doc.md']
 # Avoid staging unrelated user edits into this unit. Frozen experiment source
 # is elsewhere and never changed by these documentation-only commits.
 require(not subprocess.check_output(['git','status','--porcelain','--',*names],cwd=repo,text=True).strip(),'Methodology has concurrent changes; preserve rather than stage unrelated text')
 delivery=cfg.get('documentation_delivery','immediate_push')
 require(delivery in ('immediate_push','worker_commits_deferred_push_v1'),'Unknown documentation delivery')
 if delivery=='immediate_push':subprocess.run(['git','pull','--ff-only','origin','main'],cwd=repo,check=True)
 else:require(cfg.get('deferred_push_user_authorization')=='Proceed; defer documentation pushes','Deferred publication not authorized')
 text='\n\n## '+heading+' — '+now()+'\n'+body+'\n'
 for name in names:
  with (repo/name).open('a') as f:f.write(text);f.flush();os.fsync(f.fileno())
 subprocess.run(['git','diff','--check','--',*names],cwd=repo,check=True)
 subprocess.run(['git','add','--',*names],cwd=repo,check=True)
 subprocess.run(['git','commit','-m',heading],cwd=repo,check=True)
 if delivery=='immediate_push':subprocess.run(['git','push','origin','main'],cwd=repo,check=True)
 return {'github_publication_pending':delivery!='immediate_push','canonical_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'files_sha256':{n:sha(repo/n) for n in names},'local_client_sync':'deferred_until_client_reconnects; no current client agreement claimed'}

def run(protocol,revision,preflight_path):
 cfg=json.loads(Path(protocol).read_text());runtime=REPOSITORY_ROOT;root=Path(cfg['output_directory']);root.mkdir(parents=True,exist_ok=False)
 report={'status':'starting','started_utc':now(),'pid':os.getpid(),'runtime_revision':revision,'protocol_sha256':sha(protocol),'attempts':[],'planned':sum(map(len,cfg['orders'])),'failed':0,'passed':0,'unattempted':sum(map(len,cfg['orders'])),'model_accepted':False,'novelty_accepted':False}
 lock=None
 def save():
  p=root/'progress.tmp';p.write_text(json.dumps(report,indent=2)+'\n');p.replace(root/'progress.json')
 def announce(message,name):notify('Capstone physical timing study',message,root/name,cfg['notification_configuration'])
 save()
 try:
  require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=runtime,text=True).strip()==revision,'Frozen runtime HEAD differs')
  for n,h in cfg['code_sha256'].items():require(sha(source_file(n, repository=runtime))==h,'Frozen source differs '+n)
  preflight=json.loads(Path(preflight_path).read_text());require(preflight['status']=='passed_actual_frontier_timing_preflight_only' and preflight['protocol_sha256']==sha(protocol),'Real-source preflight not passed')
  checked(cfg['previous_raw_audit']);checked(cfg['episode_template']['mapping']);checked(cfg['episode_template']['model'])
  lock=(Path(cfg['canonical_repository'])/'results/.queue_aware_study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with (Path(cfg['canonical_repository'])/'results/.physical_correctness.lock').open('a') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
  prior=json.loads(checked(cfg['previous_cohort']).read_text());worst=max((utc(a['ended_utc'])-utc(a['started_utc'])).total_seconds() for a in prior['attempts']);extra=max(cfg['episode_template']['telemetry']['warmup_seconds'],cfg['previous_raw_audit_wall_seconds']/prior['passed']);estimate=worst+extra;clock=utc(now());terminal=clock+timedelta(seconds=estimate*report['planned']);last_start=clock+timedelta(seconds=estimate*(report['planned']-1))
  admission={'observed_max_whole_arm_wall_seconds':worst,'additional_measured_planning_margin_seconds':extra,'estimated_total_seconds':estimate*report['planned'],'estimated_terminal_utc':terminal.isoformat(),'estimated_last_start_utc':last_start.isoformat(),'limitations':'Observed full arm includes setup/warmup/drain/raw audit; add greater of measured re-audit per-arm wall time or warmup as planning margin, not a guarantee.'};write_json(root/'admission.json',admission)
  require(last_start<utc(cfg['no_new_episode_after_utc']) and terminal<utc(cfg['no_new_SQL_after_utc']),'Full observed-runtime budget does not fit; no scope thinning')
  actions={a['name']:a for a in cfg['actions']};manifest=[];(root/'protocols').mkdir();(root/'episodes').mkdir();write_json(root/'registration.json',cfg)
  for repeat,order in enumerate(cfg['orders']):
   for name in order:
    index=len(manifest)+1;action=actions[name];eid=f"{cfg['experiment_prefix']}_{index:02d}";episode=dict(cfg['episode_template'],experiment_id=eid,destination_table='local.experiment.'+eid,output_directory=str(root/'episodes'/eid),policy=action['policy'],no_new_operation_after_utc=cfg['no_new_SQL_after_utc'])
    if action['policy']=='fixed_start':episode['fixed_start_seconds']=action['seconds']
    p=root/'protocols'/(eid+'.json');write_json(p,episode);manifest.append({'experiment_id':eid,'repeat':repeat,'action':name,'protocol':{'path':str(p),'sha256':sha(p)},'table':episode['destination_table']})
  write_json(root/'manifest.json',{'episodes':manifest,'runtime_revision':revision,'protocol_sha256':sha(protocol)});report['status']='running';save()
  report['initial_doc_sync']=append_docs(cfg,'Physical timing study started',f"Registered8arms, two reversed-order repeats on one development source window. Fixed0/60/600s experimental opportunities plus noaction, all original3094arrivals/full drain, fresh16file tables. CoordinatorPID{os.getpid()}, preflightSHA{sha(preflight_path)}, ProtocolSHA{sha(protocol)}, runtime{revision}, estimatedwholewall{admission['estimated_total_seconds']/3600:.2f}h including observed setup/audit. No fitting/independent-day/novelty claim. Output{root}; source manifest fixed before physical work. Local client mirror deferred while offline; server documentation committed after units; GitHub delivery follows registered mode.")
  announce('Started8-arm fixed-timing development experiment; full drain, fresh tables, no model fitting. Estimated~'+str(round(admission['estimated_total_seconds']/3600,1))+'h. Methodology updated after each arm.','start_notification.json')
  matched=None
  for item in manifest:
   require(utc(now())<utc(cfg['no_new_episode_after_utc']),'New-episode cutoff reached; preserve unattempted arms')
   for n,h in cfg['code_sha256'].items():require(sha(source_file(n, repository=runtime))==h,'Frozen source changed during study')
   checked(item['protocol']);attempt=dict(item,status='running',started_utc=now());report['attempts'].append(attempt);report['unattempted']-=1;save()
   log=root/(item['experiment_id']+'.log');receipt=root/(item['experiment_id']+'.failure_notification.json')
   command=['nohup',sys.executable,'-B','-u',str(runtime/'scripts/phase6-live-evaluation/run_with_failure_alert.py'),'--label',item['experiment_id'],'--receipt',str(receipt),'--',sys.executable,'-B','-u',str(source_file('run_episode.py', repository=runtime)),'--protocol',item['protocol']['path'],'--expected-revision',revision]
   with log.open('x') as f:child=subprocess.Popen(command,cwd=runtime,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL);attempt['wrapper_pid']=child.pid;attempt['log']=str(log);save();rc=child.wait()
   attempt.update(status='returned_pending_validation',returncode=rc,ended_utc=now());p=root/'episodes'/item['experiment_id']/'result.json'
   if rc or not p.exists():attempt['status']='failed_preserved';report['failed']+=1;save();raise RuntimeError('Physical/raw gate failed; no retry or survivor comparison')
   result=json.loads(p.read_text());require(result['status']=='audited_complete_real_full_drain_episode_only' and result['completed']==result['arrival_count'] and result['unfinished']==0,'Incomplete full-drain result')
   signature={'mapping_sha256':cfg['episode_template']['mapping']['sha256'],'layout':result['initial_layout_signature'],'rows':result['initial_file_state']['record_count'],'model':cfg['episode_template']['model']}
   if matched is None:matched=signature
   else:require(signature==matched,'Repeated policies lack matched original source/layout/model')
   attempt.update(status='passed',result_sha256=sha(p),completed=result['completed'],sum_response_ns=result['sum_response_ns'],mean_response_seconds=result['mean_response_seconds'],drain_seconds=result['drain_end_after_start_seconds'],**timing_details(p.parent));report['passed']+=1;save()
   attempt['documentation']=append_docs(cfg,'Timing study completed '+item['experiment_id'],f"Action{item['action']}, repeat{item['repeat']}, raw/full-drain PASSED {result['completed']}queries. ResultSHA{sha(p)}, eventsSHA{result['events_sha256']}; sumresponse{result['sum_response_ns']}ns = rawoutstandingarea; mean{result['mean_response_seconds']:.6f}s, drain{result['drain_end_after_start_seconds']:.6f}s. Actualtiming{json.dumps(timing_details(p.parent))}. Frozen{revision}; sourcewindow reused intentionally as development, no newfit or calibratedmodel. No policy contrasts before full8armgate. Output{p.parent}. Preserve all failed/unattempted scope. Local raw mirror pending client reconnect.")
   save();announce(f"Arm{report['passed']}/8 passed: {item['action']}, repeat{item['repeat']}, {result['completed']}queries. Both methodology docs saved/committed; publication follows registered mode. No benefit claim yet.",item['experiment_id']+'.notification.json')
  report['status']='collected_all_arms_pending_reconstruction';save()
  # Post-collection replay is a distinct failure-alerted job. No hidden refitting.
  compare_out=root/'analysis';command=['nohup',sys.executable,'-B','-u',str(runtime/'scripts/phase6-live-evaluation/run_with_failure_alert.py'),'--label',cfg['experiment_prefix']+'_raw_comparison','--receipt',str(root/'analysis_failure_notification.json'),'--',sys.executable,'-B','-u',str(source_file('compare_timing_study.py', repository=runtime)),'--study',str(root),'--output',str(compare_out)]
  with (root/'analysis.log').open('x') as f:child=subprocess.Popen(command,cwd=runtime,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL);report['analysis_wrapper_pid']=child.pid;save();require(child.wait()==0,'Final raw comparison failed; preserve physical evidence')
  summary=json.loads((compare_out/'result.json').read_text());report['status']='completed_repeated_development_timing_study';report['analysis_sha256']=sha(compare_out/'result.json');report['final_doc_sync']=append_docs(cfg,'Physical timing study terminal review',f"All8physicalarms/rawreconstruction complete. AnalysisSHA{report['analysis_sha256']}, report{compare_out/'report.md'}. Descriptive contrasts{json.dumps(summary['contrasts'])}. Repeatedlowerresponseactions{summary['delayed_actions_lower_both_repeats']}; no causal/generalization/calibration/novelty accepted. Only two repeats of one development arrival window; actualstartlateness/tableendstates and all negative outcomes retained. No refit. Rawbackup/localHEADsync deferred until client returns; immutable rawoutputs onworker3.")
  announce('All8arms and final raw reconstruction complete. Saved report; delayed actions lower in both repeats: '+str(summary['delayed_actions_lower_both_repeats'])+'. Descriptive development evidence only.','terminal_notification.json')
 except Exception as e:
  report.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc());save()
  try:report['failure_doc_sync']=append_docs(cfg,'Timing study failure preserved',f"Status{report['status']}, error{e}, passed{report['passed']}, failed{report['failed']}, unattempted{report['unattempted']}. No retry or survivorcomparison. Raw/progress{root}; actual running operations preserved.")
  except Exception as doc_error:report['documentation_error']=str(doc_error)
  raise
 finally:
  report['failed']=sum(a['status']!='passed' for a in report['attempts']);report['ended_utc']=now();save();write_json(root/'result.json',report)
  if lock is not None:lock.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--expected-revision',required=True);p.add_argument('--preflight',required=True);a=p.parse_args();run(a.protocol,a.expected_revision,a.preflight)
