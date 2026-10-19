"""Empirical estimates from SHA-bound physical labels, never policy constants."""
from collections import defaultdict,Counter
from statistics import median
from pathlib import Path
import json
from common import checked,read_csv,require,sha

class UnsupportedEvidence(ValueError):pass

class EmpiricalCosts:
 def __init__(self,query_cells,rewrites,turnaround,provenance):
  self.query_cells=query_cells;self.rewrites=rewrites;self.turnaround=turnaround;self.provenance=provenance
 @classmethod
 def from_protocol(cls,cfg):
  export=checked(cfg['candidate_export']);manifest=json.loads(export.read_text())
  for name,h in manifest['artifact_sha256'].items():require(sha(export.parent/name)==h,'Changed training artifact '+name)
  samples=defaultdict(list);episode_ids=defaultdict(set)
  for r in read_csv(export.parent/'queries.csv'):
   k=(int(r['query_id']),int(r['file_count']),r['maintenance_client_pending_at_feature_time']=='True');v=float(r['service_target_ms'])/1000;require(v>0,'Nonpositive observed service');samples[k].append(v);episode_ids[k].add(r['experiment_id'])
  rewrite_samples=defaultdict(list);outcomes=defaultdict(list)
  for r in read_csv(export.parent/'rewrites.csv'):
   f=int(r['file_count']);post=f-int(r['actual_rewritten_files_target'])+int(r['actual_added_files_target']);require(post>0,'Missing physical rewrite outcome');rewrite_samples[f].append(float(r['rewrite_service_target_ms'])/1000);outcomes[f].append(post)
  # Account for the instrumented serial client's measured turn-around between
  # already-offered consecutive requests. This is not engine service time.
  gaps=[];gap_sources=[]
  for spec in cfg['turnaround_events']:
   p=checked(spec);events=[json.loads(s) for s in p.open()];starts={r['measurement_id']:r for r in events if r['kind']=='statement_completed' and r['role']=='trace_query'};scheduled={r['measurement_id']:r['scheduled_monotonic_ns'] for r in events if r['kind']=='queue_transition' and r['state']=='offered'};ordered=sorted(starts.values(),key=lambda r:r['client_execute_start']['monotonic_ns'])
   for prev,nxt in zip(ordered,ordered[1:]):
    end=prev['fetch_end']['monotonic_ns'];begin=nxt['client_execute_start']['monotonic_ns']
    if scheduled[nxt['measurement_id']]<=end:
     require(begin>=end,'Overlapping single-client calls');gaps.append((begin-end)/1e9)
   gap_sources.append({'path':str(p),'sha256':sha(p)})
  require(gaps,'No measured busy-client turn-around evidence')
  cells={k:{'median_seconds':median(v),'observations':len(v),'episodes':sorted(episode_ids[k]),'samples_seconds':v} for k,v in samples.items()}
  rewrites={f:{'median_seconds':median(v),'observations':len(v),'predicted_post_files':min(Counter(outcomes[f]),key=lambda k:(-Counter(outcomes[f])[k],k)),'observed_post_files':outcomes[f]} for f,v in rewrite_samples.items()}
  return cls(cells,rewrites,median(gaps),{'candidate_export_sha256':sha(export),'turnaround_sources':gap_sources,'turnaround_rows':len(gaps),'all_prior_cost_families_are_development':True})
 def service(self,qid,files,pending):
  k=(int(qid),int(files),bool(pending))
  if k not in self.query_cells:raise UnsupportedEvidence('No measured conditional service '+str(k))
  return self.query_cells[k]['median_seconds']
 def rewrite(self,files):
  if int(files) not in self.rewrites:raise UnsupportedEvidence('No measured rewrite duration '+str(files))
  return self.rewrites[int(files)]
 def summary(self):return {'query_cells':[dict(query_id=k[0],files=k[1],pending=k[2],**{n:v for n,v in c.items() if n!='samples_seconds'}) for k,c in sorted(self.query_cells.items())],'rewrites':self.rewrites,'client_turnaround_seconds':self.turnaround,'provenance':self.provenance,'status':'uncalibrated_observational_empirical_estimates_no_causal_labels'}

 def save(self,path):
  from common import write_json
  write_json(path,self.summary())
 @classmethod
 def load(cls,path):
  v=json.loads(Path(path).read_text());cells={(int(r['query_id']),int(r['files']),bool(r['pending'])):{k:x for k,x in r.items() if k not in ('query_id','files','pending')} for r in v['query_cells']};return cls(cells,{int(k):x for k,x in v['rewrites'].items()},v['client_turnaround_seconds'],v['provenance'])
