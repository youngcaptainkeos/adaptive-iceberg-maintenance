#!/usr/bin/env python3
"""Independent raw full-cohort conservation, causal binding and Spark task audit."""
import argparse,json,csv,re
from pathlib import Path
from collections import Counter
from common import require,sha,checked,write_json,utc
from statement_timing import completed_statements
from query_observation_binding import verify_observations
from run_correctness_pilot import canonical,query_templates
from engine_archive import merged_engine_frames
from engine_overlap import task_intervals,engine_time,overlap_evidence

class RawTasks:
 def __init__(self,events):
  self.frames={}
  for r in events:
   if r['kind']=='spark_rest' and '/taskList?length=' in r['resource']:
    payload=r['payload'];require(isinstance(payload,list),'Missing actual tasks');key=r['resource']
    if key in self.frames:require({t['taskId'] for t in payload}=={t['taskId'] for t in self.frames[key]},'Changed task identities')
    self.frames[key]=payload
 def capture_tasks(self,stage,attempt,count):
  key=f'stages/{stage}/{attempt}/taskList?length={count}';require(key in self.frames,'Actual archived task evidence missing');p=self.frames[key];require(len(p)==count and all(t['status']=='SUCCESS' and t['duration']>0 for t in p),'Incomplete successful tasks');return p

def audit(directory):
 d=Path(directory);cfg=json.loads((d/'config.json').read_text());events=[json.loads(s) for s in (d/'events.jsonl').open()];protocols=[r for r in events if r['kind']=='queue_aware_protocol'];require(len(protocols)==1 and protocols[0]['configuration']==cfg,'Raw registration differs')
 for n,h in protocols[0]['code_sha256'].items():require(sha(d/'code'/n)==h,'Frozen code differs')
 require(sha(d/'mapped_arrivals.csv')==cfg['mapping']['sha256'] and sha(d/'preparation_result.json')==cfg['preparation_result']['sha256'],'Changed physical source files');source=json.loads((d/'preparation_result.json').read_text());mapped=list(csv.DictReader((d/'mapped_arrivals.csv').open()));require(len(mapped)==cfg['arrival_count'],'Arrival population changed')
 clocks=[r for r in events if r['kind']=='cohort_clock'];require(len(clocks)==1,'Missing unique cohort clock');clock=clocks[0];lo=clock['start_monotonic_ns'];hi=clock['arrival_end_monotonic_ns'];require(hi-lo==int(cfg['horizon_seconds']*1e9),'Arrival horizon changed');require((utc(cfg['source_end_utc'])-utc(cfg['source_start_utc'])).total_seconds()==cfg['horizon_seconds'],'Source interval changed')
 transitions=[r for r in events if r['kind']=='cohort_queue_transition'];states={};mids={};times={};mapping={r['source_query_id']:r for r in mapped};active=None;dispatch=[]
 for r in transitions:
  identity=r['source']['source_query_id'];require(identity in mapping and r['source']==mapping[identity],'Changed source identity');previous=states.get(identity);state=r['state'];require(previous==r['previous_state'] and (previous,state) in [(None,'offered'),('offered','queued'),('queued','dispatched'),('dispatched','completed'),('dispatched','failed')],'Broken queue chain');actual=r['actual_transition']['monotonic_ns'];require(actual<=r['recorded']['monotonic_ns'],'Future queue clock')
  scheduled=lo+int(mapping[identity]['offset_ns']);require(r['scheduled_monotonic_ns']==scheduled,'Retimed input demand')
  if state=='offered':require(actual>=scheduled,'Offered before true source arrival');mids[identity]=r['measurement_id'];times[identity]={}
  require(mids[identity]==r['measurement_id'],'Changed measurement identity')
  if times[identity]:require(actual>=max(times[identity].values()),'Reversed queue clock')
  times[identity][state]=actual;states[identity]=state
  if state=='dispatched':require(active is None,'Concurrent serial query calls');active=identity;dispatch.append(identity)
  if state in ('completed','failed'):require(active==identity,'Completion without own slot');active=None
 require(active is None and set(states)==set(mapping) and all(s=='completed' for s in states.values()),'Not a complete drained cohort; retain failures/debt')
 require(dispatch==[r['source_query_id'] for r in mapped] and len(set(mids.values()))==len(mapped),'FIFO population/identity violation')
 statements=completed_statements([d/'events.jsonl']);measured={mid:r for (eid,mid),r in statements.items() if eid==cfg['experiment_id']};requests={r['measurement_id']:r for r in events if r['kind']=='statement_requested'};require(not any(r['kind'] in ('statement_failed','statement_not_submitted','cohort_failed_preserved','cohort_thread_failed','spark_rest_failed') for r in events),'Failed/censored run cannot pass complete-cohort audit')
 expected={}
 for i,spec in enumerate(cfg['expected_query_ledgers']):
  p=d/f'expected_ledger_{i}.jsonl';require(sha(p)==spec['sha256'],'Changed correctness reference');rr=[r for r in completed_statements([p]).values() if r['role']=='control_before'];require(len(rr)==1,'Ambiguous reference');expected[int(rr[0]['query_id'])]=canonical(rr[0]['rows'])
 require(len([r for r in measured.values() if r['role']=='trace_query'])==len(mapped),'Unbound/extra actual query result')
 verify_observations(events,cfg);maint_obs=[r for r in events if r['kind']=='maintenance_decision_observation']
 if maint_obs:verify_observations(events,cfg,kind='maintenance_decision_observation')
 observations={r['measurement_id']:r for r in events if r['kind']=='query_observation'};jobs,stages=merged_engine_frames(events);tasks=RawTasks(events);baseline=[r for r in events if r['kind']=='cohort_engine_baseline'];require(len(baseline)==1,'Missing raw engine boundary');known=[r['marker'] for r in requests.values()]
 for j in jobs:
  if j['jobId'] in baseline[0]['job_ids']:continue
  desc=str(j.get('description',''));require(any(m in desc for m in known) or desc.startswith('Rewriting ') and desc.endswith(' in '+cfg['destination_table']),'Foreign engine work')
 actions=[r for r in measured.values() if r['role']=='maintenance'];require(len(actions)<=1 and len(actions)==len(maint_obs),'More than registered one rewrite allowance')
 require((cfg['policy']=='no_maintenance' and not actions) or cfg['policy']!='no_maintenance','Maintenance in null control')
 if cfg['policy'] in ('immediate','forecast_quiet'):require(len(actions)==1,'Registered compaction control did not execute')
 if cfg['policy']=='fixed_start':require(len(actions)==1,'Registered fixed-time intervention did not execute')
 action_tasks=[]
 for r in actions:
  require(lo<=r['client_execute_start']['monotonic_ns']<hi and utc(r['client_execute_start']['utc'])<utc(cfg['no_new_operation_after_utc']),'Maintenance outside registered window');action_tasks+=task_intervals(jobs,stages,tasks,rewrite_table=cfg['destination_table'],request=r)
 result_queries=[];response_sum=0;service_sum=0;wait_sum=0;accounting=[]
 for identity in dispatch:
  mid=mids[identity];r=measured[mid];source_row=mapping[identity];qid=int(source_row['query_id']);obs=observations[mid];scheduled=lo+int(source_row['offset_ns']);started=r['client_execute_start']['monotonic_ns'];ended=r['fetch_end']['monotonic_ns'];require(times[identity]['dispatched']<=started<ended<=times[identity]['completed'] and utc(r['client_execute_start']['utc'])<utc(cfg['no_new_operation_after_utc']),'Actual SQL clock/slot mismatch')
  require(requests[mid]['sql']==query_templates(cfg['destination_table'])[qid].replace(f"FROM {cfg['destination_table']}",f"FROM {cfg['destination_table']} VERSION AS OF {obs['snapshot_id']}") and canonical(r['rows'])==expected[qid],'SQL identity/snapshot/result mismatch')
  actual_tasks=task_intervals(jobs,stages,tasks,marker=r['marker']);overlap=overlap_evidence(actual_tasks,action_tasks);response=ended-scheduled;wait=started-scheduled;service=ended-started;require(wait>=0 and response==wait+service,'Response time decomposition');response_sum+=response;wait_sum+=wait;service_sum+=service;accounting.extend([(scheduled,1),(ended,-1)])
  result_queries.append({'source_query_id':identity,'measurement_id':mid,'query_id':qid,'response_ns':response,'waiting_before_actual_call_ns':wait,'service_ns':service,'generator_lateness_ns':times[identity]['offered']-scheduled,'completed_before_arrival_end':ended<=hi,'snapshot_id':obs['snapshot_id'],'verified_task_lifetime_overlap':overlap['verified_task_lifetime_overlap'],'task_overlap_seconds':overlap['overlap_seconds']})
 # Independent exact integer area under outstanding-request count. This includes
 # every query waiting after the arrival horizon, not just early completions.
 level=0;area=0;previous=min(t for t,_ in accounting)
 for t,delta in sorted(accounting):area+=level*(t-previous);level+=delta;require(level>=0,'Negative outstanding cohort');previous=t
 require(level==0 and area==response_sum and response_sum==wait_sum+service_sum,'Exact full-population response area mismatch')
 boundaries=[r for r in events if r['kind']=='cohort_arrival_boundary'];require(len(boundaries)==1 and boundaries[0]['recorded']['monotonic_ns']>=hi,'Missing arrival boundary');before={}
 for r in transitions:
  if r['recorded']['monotonic_ns']<boundaries[0]['recorded']['monotonic_ns']:before[r['source']['source_query_id']]=r['state']
 require(boundaries[0]['states']==before and boundaries[0]['counts']==dict(Counter(before.values())),'Boundary census not bound to actual ledger')
 initial=[r for r in events if r['kind']=='cohort_initial_state'];final=[r for r in events if r['kind']=='cohort_final_state'];require(len(initial)==len(final)==1,'Missing initial/final layout');require(initial[0]['file_state']['file_count']==cfg['initial_file_count'] and all(r['file_state']['record_count']==source['record_count'] for r in initial+final),'Changed record population/layout')
 multisets=[r for r in events if r['kind']=='cohort_multiset_validation'];require(len(multisets)==2 and {r['snapshot_id'] for r in multisets}=={initial[0]['snapshot_id'],final[0]['snapshot_id']},'Missing original/final logical equality')
 for r in multisets:require(measured[r['measurement_id']]['rows']==[[0]],'Nonzero logical difference')
 decisions=[r for r in events if r['kind']=='controller_decision'];require(decisions,'No actual controller decisions');starts=[r for r in decisions if r['decision']['execute_now']];require(len(starts)==len(actions),'Controller action/physical rewrite mismatch')
 for r in decisions:
  decision=r['decision'];require(r['model_sha256']==cfg['model']['sha256'] and decision['policy']==cfg['policy'],'Changed policy/model');require(r['decision_started']['monotonic_ns']<=r['decision_finished']['monotonic_ns']<=r['recorded']['monotonic_ns'],'Controller observation chronology');require(abs(decision['elapsed_seconds']-(r['decision_started']['monotonic_ns']-lo)/1e9)<=cfg['numeric_absolute_tolerance_seconds'],'Controller source clock differs')
  if 'forecast' in decision:
   f=decision['forecast'];require(utc(f['maximum_history_timestamp'])<utc(cfg['forecast_history_freeze_utc'])<=utc(f['decision_source_time']) and f['source_sha256']==cfg['arrivals']['sha256'],'Future/missing forecast input')
   require(all(utc(b['end'])<=utc(cfg['source_end_utc']) for b in f['bins']),'Forecast extends offered cohort')
 if cfg['policy']=='fixed_start':
  require(cfg.get('fixed_start_contract')=='first_controller_opportunity_v1','Missing timing intervention contract')
  target=cfg['fixed_start_seconds'];require(0<=target<cfg['horizon_seconds'],'Invalid timing target')
  for event in decisions:
   decision=event['decision'];require(decision['registered_start_seconds']==target and decision['execute_now']==(target<=decision['elapsed_seconds']<cfg['horizon_seconds']),'Fixed start differs from registered opportunity')
  require((actions[0]['client_execute_start']['monotonic_ns']-lo)/1e9>=target,'Physical rewrite submitted before registered time')
 if starts:require(starts[0]['recorded']['monotonic_ns']<=actions[0]['request_start']['monotonic_ns'],'Action before recorded decision')
 return {'status':'audited_complete_real_full_drain_episode_only','policy':cfg['policy'],'experiment_id':cfg['experiment_id'],'arrival_count':len(mapped),'completed':len(result_queries),'failed':0,'unfinished':0,'sum_response_ns':response_sum,'sum_wait_before_call_ns':wait_sum,'sum_service_ns':service_sum,'independent_outstanding_area_ns':area,'mean_response_seconds':response_sum/len(mapped)/1e9,'drain_end_after_start_seconds':(max(measured[mids[i]]['fetch_end']['monotonic_ns'] for i in dispatch)-lo)/1e9,'completed_before_arrival_end':sum(r['completed_before_arrival_end'] for r in result_queries),'maintenance_count':len(actions),'maintenance_service_seconds':[r['client_elapsed_ns']/1e9 for r in actions],'initial_file_state':initial[0]['file_state'],'initial_layout_signature':initial[0]['layout_signature'],'final_file_state':final[0]['file_state'],'controller_decisions':len(decisions),'events_sha256':sha(d/'events.jsonl'),'queries':result_queries,'model_accepted':False,'novelty_or_performance_improvement_established':False,'limitations':cfg['limitations']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--output',required=True);a=p.parse_args();write_json(a.output,audit(a.directory))
