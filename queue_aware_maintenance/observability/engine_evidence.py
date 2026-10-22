"""Incremental archive of actual Spark task evidence before UI retention expires."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
from queue_aware_maintenance.core.common import require
from engine_overlap import task_intervals

class EngineArchive:
 def __init__(self,rest,log,table):
  self.rest=rest;self.log=log;self.table=table;self.jobs={};self.stages={};self.tasks={};self.certified=set();self.maintenance=set();self.baseline_job_ids={j['jobId'] for j in rest.capture('jobs')};log.emit('cohort_engine_baseline',job_ids=sorted(self.baseline_job_ids))
 def capture_tasks(self,stage,attempt,count):
  key=(stage,attempt,count)
  if key not in self.tasks:self.tasks[key]=self.rest.capture_tasks(stage,attempt,count)
  return self.tasks[key]
 def checkpoint(self,probes,actions,known_markers,*,final=False):
  jobs=self.rest.capture('jobs');stages=self.rest.capture('stages')
  for j in jobs:self.jobs[j['jobId']]=j
  for s in stages:self.stages[(s['stageId'],s['attemptId'])]=s
  for job in jobs:
   if job['jobId'] in self.baseline_job_ids:continue
   description=str(job.get('description',''));require(any(m in description for m in known_markers) or description.startswith('Rewriting ') and description.endswith(' in '+self.table),'Foreign Spark work in exclusive physical study: '+description)
  for probe in probes:
   if probe['measurement_id'] in self.certified:continue
   relevant=[j for j in self.jobs.values() if probe['marker'] in str(j.get('description',''))]
   if not relevant or any(j['status']!='SUCCEEDED' for j in relevant):
    require(not final,'Missing/non-successful actual query job at final audit');continue
   task_intervals(list(self.jobs.values()),list(self.stages.values()),self,marker=probe['marker']);self.certified.add(probe['measurement_id'])
  for action in actions:
   if action['measurement_id'] in self.maintenance:continue
   task_intervals(list(self.jobs.values()),list(self.stages.values()),self,rewrite_table=self.table,request=action);self.maintenance.add(action['measurement_id'])
  self.log.emit('cohort_engine_checkpoint',certified_queries=sorted(self.certified),certified_maintenance=sorted(self.maintenance),final=final)
  if final:require(len(self.certified)==len(probes) and len(self.maintenance)==len(actions),'Incomplete actual task certification')
