#!/usr/bin/env python3
"""Operational prefix diagnostic, not a terminal result, fit or policy evaluation."""
import argparse,json,statistics
from pathlib import Path
from collections import Counter
from common import checked,require,write_json,sha,now

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 episode=json.loads(checked(cfg['episode_protocol']).read_text());source=Path(episode['output_directory'])/'events.jsonl';data=source.read_bytes()
 # A live writer's final unterminated record is not evidence. Preserve the exact
 # complete prefix inspected; missing later records remain explicitly missing.
 if not data.endswith(b'\n'):data=data[:data.rfind(b'\n')+1]
 prefix=out/'observed_prefix.jsonl';prefix.write_bytes(data);events=[json.loads(l) for l in data.splitlines()]
 clock=[r for r in events if r['kind']=='cohort_clock'];require(len(clock)==1,'Replay has not started');lo=clock[0]['start_monotonic_ns'];frontier=max(r['recorded']['monotonic_ns'] for r in events);elapsed=(frontier-lo)/1e9
 queries=sorted([r for r in events if r['kind']=='statement_completed' and r.get('role')=='trace_query'],key=lambda r:r['client_execute_start']['monotonic_ns']);require(len(queries)>1,'Need actual completed calls')
 states={};offered={}
 for r in events:
  if r['kind']=='cohort_queue_transition':
   states[r['source']['source_query_id']]=r['state']
   if r['state']=='offered':offered[r['measurement_id']]=r['actual_transition']['monotonic_ns']
 gaps=[]
 for a,b in zip(queries,queries[1:]):
  start=a['fetch_end']['monotonic_ns'];end=b['client_execute_start']['monotonic_ns'];require(end>=start,'Serial calls overlap');busy=offered[b['measurement_id']]<=start
  kinds=Counter(r['kind'] for r in events if start<=r['recorded']['monotonic_ns']<=end)
  gaps.append({'after_measurement_id':a['measurement_id'],'before_measurement_id':b['measurement_id'],'seconds':(end-start)/1e9,'next_query_already_offered':busy,'recorded_event_kinds':dict(kinds)})
 rest=[r for r in events if r['kind']=='spark_rest' and r['request_start']['monotonic_ns']>=lo]
 service=sum(r['client_elapsed_ns']/1e9 for r in queries);byqid={}
 for qid in sorted({r['query_id'] for r in queries}):
  v=[r['client_elapsed_ns']/1e9 for r in queries if r['query_id']==qid];byqid[qid]={'calls':len(v),'median_client_seconds':statistics.median(v),'sum_client_seconds':sum(v)}
 report={'status':'observed_live_prefix_operational_diagnostic_only','observed_utc':now(),'protocol_sha256':sha(protocol),'code_sha256':sha(__file__),'prefix_sha256':sha(prefix),'prefix_bytes':len(data),'completed_cohort':False,'elapsed_frontier_seconds':elapsed,'state_counts':dict(Counter(states.values())),'completed_calls':len(queries),'sum_completed_client_service_seconds':service,'sum_inter_call_gap_seconds':sum(g['seconds'] for g in gaps),'sum_busy_inter_call_gap_seconds':sum(g['seconds'] for g in gaps if g['next_query_already_offered']),'largest_inter_call_gaps':sorted(gaps,key=lambda g:g['seconds'],reverse=True)[:cfg['maximum_report_gaps']],'service_by_query':byqid,'completed_rest_requests':len(rest),'sum_rest_response_seconds':sum((r['response_end']['monotonic_ns']-r['request_start']['monotonic_ns'])/1e9 for r in rest),'completion_rate_calls_per_second_so_far':len(queries)/elapsed,'linear_remaining_seconds_diagnostic_only':(episode['arrival_count']-len(queries))*elapsed/len(queries),'limitations':['Live prefix, not full-drain evidence; active calls/REST/serialization work may be absent from completed intervals.','Linear remaining time assumes stationary observed throughput and may be wrong; no model refit or scientific performance claim.','Inter-call gaps include observer, driver, metadata and idle time; event presence alone does not establish which caused delay.']}
 write_json(out/'result.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
