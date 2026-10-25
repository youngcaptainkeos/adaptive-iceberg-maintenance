"""Versioned pre-execution plan adapter over an unchanged proven physical runner.

Only statement-recording/archive bindings are extended. No plan feature changes
SQL, demand, the original telemetry sampler, query dispatch or policy decisions.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import uuid
from queue_aware_maintenance.core.common import checked,require,sha,utc,now
from three_model_maintenance.preparation.query_plan import parse


def original(cfg):
    root=Path(cfg['physical_runtime'])/'queue_aware_maintenance'
    for name,h in cfg['physical_code_sha256'].items():require(sha(root/name)==h,'Changed original physical source '+name)
    sys.path.insert(0,str(root))
    spec=importlib.util.spec_from_file_location('queue_complexity_frozen_physical',root/'run_episode.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def sql_hash(sql):return hashlib.sha256(sql.encode()).hexdigest()


def capture(recorder,cursor,sql,qid,cfg):
    """Persist real EXPLAIN outputs before publishing a structure-only receipt."""
    from physical_measurements import stamp
    require(utc(now())<utc(cfg['no_new_operation_after_utc']),'No new plan SQL after cutoff')
    snapshot=re.search(r'\bVERSION AS OF ([0-9]+)\b',sql)
    require(snapshot,'Plan must pin exact observed snapshot')
    results=[]
    for mode in ('FORMATTED','COST'):
        require(utc(now())<utc(cfg['no_new_operation_after_utc']),'Plan operation cutoff')
        r=recorder.execute(cursor,'EXPLAIN '+mode+' '+sql,role='complexity_plan',query_id=qid,measurement_id=uuid.uuid4().hex)
        require(r['rows'] and all(len(row)==1 and isinstance(row[0],str) for row in r['rows']),'Missing actual string EXPLAIN output')
        results.append(r)
    formatted,cost=['\n'.join(row[0] for row in r['rows']) for r in results]
    features=parse(formatted,cost)
    pid=uuid.uuid4().hex
    recorder.log.emit('complexity_plan_receipt',plan_id=pid,query_id=qid,sql=sql,sql_sha256=sql_hash(sql),snapshot_id=int(snapshot.group(1)),
                      explain_measurement_ids=[r['measurement_id'] for r in results],parsed=features,
                      contract='preexecution_initial_plan_by_exact_sql_snapshot_v1')
    # The source receipt's EventLog fsync has returned. Publication is separately
    # persisted; the in-memory availability timestamp is taken after that too.
    recorder.log.emit('complexity_plan_publication',plan_id=pid,receipt_persisted_by=stamp())
    return {'plan_id':pid,'query_id':qid,'sql_sha256':sql_hash(sql),'snapshot_id':int(snapshot.group(1)),
            'features':features['features'],'available_at':stamp(),'explain_markers':[r['marker'] for r in results]}


def install(base,cfg,source_repository):
    """Explicit adapter installation; original files/proofs remain byte unchanged."""
    OriginalRecorder=base.StatementRecorder; OriginalArchive=base.EngineArchive
    class PlanRecorder(OriginalRecorder):
        def __init__(self,log):
            super().__init__(log);self.cache={};self.bound={};log.complexity_markers=[]
            out=Path(log.stream.name).parent/'complexity_code';out.mkdir(exist_ok=False)
            for name,h in cfg['complexity_source_sha256'].items():
                src=Path(source_repository)/name;require(sha(src)==h,'Changed complexity source '+name)
                dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
            log.emit('complexity_adapter_protocol',contract='preexecution_initial_plan_by_exact_sql_snapshot_v1',source_sha256=cfg['complexity_source_sha256'],
                     original_physical_revision=cfg['physical_revision'],runtime_predictions_changed=False,training_accepted=False)
        def execute(self,cursor,sql,*,role,query_id=None,measurement_id=None,**kwargs):
            if role=='trace_query':
                key=sql_hash(sql)
                if key not in self.cache:
                    # Call an unmodified base recorder for EXPLAIN, avoiding recursion.
                    receipt=capture(OriginalRecorder(self.log),cursor,sql,query_id,cfg)
                    self.log.complexity_markers.extend(receipt['explain_markers']);self.cache[key]=receipt
                receipt=self.cache[key]
                require(receipt['query_id']==query_id,'Plan cache query identity differs')
                if measurement_id not in self.bound:
                    self.log.emit('complexity_query_binding',measurement_id=measurement_id,**{k:v for k,v in receipt.items() if k!='explain_markers'})
                    self.bound[measurement_id]=key
                else:require(self.bound[measurement_id]==key,'Preparation deferral changed pinned query plan')
            return super().execute(cursor,sql,role=role,query_id=query_id,measurement_id=measurement_id,**kwargs)
    class PlanArchive(OriginalArchive):
        def checkpoint(self,probes,actions,known_markers,*,final=False):
            return super().checkpoint(probes,actions,list(known_markers)+self.log.complexity_markers,final=final)
    base.StatementRecorder=PlanRecorder; base.EngineArchive=PlanArchive
