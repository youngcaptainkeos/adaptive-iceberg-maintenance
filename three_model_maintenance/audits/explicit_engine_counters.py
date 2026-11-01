"""Post-block supplementary raw counter-presence audit, without zero defaults.

This reads immutable completed engineering episodes only. It cannot turn missing
counters into zero, accept failed source episodes, or claim an exhaustive inventory
of jobs which were never observed. No SQL, model fitting or source mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone


def require(ok,message):
    if not ok:raise ValueError(message)


def read(path):return json.loads(Path(path).read_text())


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def write(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def counters(record,names,identity):
    for name in names:
        require(name in record and type(record[name]) is int and record[name]==0,
                'Missing, invalid or nonzero actual counter '+str(identity)+'/'+name)


def episode(directory):
    cfg=read(directory/'config.json');terminal=read(directory/'result.json')
    require(cfg['terminal_engine_archive_contract']=='completed_calls_before_final_validation_v1',
            'Supplement only applies to registered prospective repair')
    requests={};completed={};engine=[];certificate=None
    for line in (directory/'events.jsonl').open():
        e=json.loads(line)
        if e['kind']=='statement_requested':
            require(e['measurement_id'] not in requests,'Duplicate actual SQL request')
            requests[e['measurement_id']]=e
        if e['kind']=='statement_completed' and e['role'] in ('trace_query','maintenance'):
            require(certificate is None and e['measurement_id'] not in completed,'Workload outcome after terminal certificate or duplicate')
            completed[e['measurement_id']]=e
        if e['kind']=='spark_rest' and certificate is None:engine.append(e)
        if e['kind']=='terminal_engine_archive_checkpoint' and e['terminal']:
            require(certificate is None,'Duplicate terminal certificate');certificate=e
    require(certificate and completed,'Missing actual terminal evidence')
    by_marker={requests[mid]['marker']:mid for mid,c in completed.items() if c['role']=='trace_query'}
    table=cfg['destination_table'];actions={mid for mid,c in completed.items() if c['role']=='maintenance'}
    histories={};associated={mid:set() for mid in completed};job_frames=0
    for frame in engine:
        if frame['resource']!='jobs':continue
        for job in frame['payload']:
            description=job.get('description') or ''
            query_ids=[mid for marker,mid in by_marker.items() if marker in description]
            action_ids=list(actions) if description.startswith('Rewriting ') and description.endswith(' in '+table) else []
            ids=query_ids+action_ids
            if not ids:continue
            require(len(ids)==1,'Ambiguous observed job-to-call attribution')
            counters(job,('numFailedTasks','numKilledTasks','numFailedStages'),('job',job['jobId']))
            require(job['status'] in ('RUNNING','SUCCEEDED'),'Adverse/unknown observed job state')
            histories.setdefault(job['jobId'],[]).append(job);associated[ids[0]].add(job['jobId']);job_frames+=1
    require(all(associated.values()),'Completed call has no observed attributed job inventory')
    for jid,values in histories.items():
        require(values[-1]['status']=='SUCCEEDED','Known job lacks actual successful terminal state '+str(jid))
    stage_ids={sid for h in histories.values() for j in h for sid in j['stageIds']};stage_frames=0
    for frame in engine:
        if frame['resource']!='stages':continue
        for stage in frame['payload']:
            if stage['stageId'] not in stage_ids:continue
            counters(stage,('numFailedTasks','numKilledTasks','attemptId'),('stage',stage['stageId']))
            stage_frames+=1
    require(stage_frames>0,'No actual applicable stage frames')
    require(set(certificate['certified_completed_query_ids'])=={mid for mid,c in completed.items() if c['role']=='trace_query'} and
            set(certificate['certified_completed_maintenance_ids'])==actions,'Terminal call inventory differs')
    require(terminal['events_sha256']==sha(directory/'events.jsonl'),'Raw differs from terminal collector audit')
    return dict(experiment_id=cfg['experiment_id'],completed_query_calls=len(by_marker),completed_maintenance_calls=len(actions),
                observed_attributed_jobs=len(histories),observed_job_frames_checked=job_frames,
                applicable_stage_frames_checked=stage_frames,events_sha256=terminal['events_sha256'],
                fields_were_explicit=True,zero_defaults_used=False,SQL_exhaustive_job_inventory_claimed=False)


def capability_proof(cfg):
    """Bind just the real files used by preflight to the prior typed manifest."""
    spec=cfg['inputs']['capability_audit'];proofpath=Path(spec['path'])
    require(sha(proofpath)==spec['sha256'],'Changed accepted capability proof')
    proof=read(proofpath)
    protocol=Path(__file__).resolve().parents[2]/'three_model_maintenance/protocols/sf10_saved_typed_audit_20261026.json'
    require(sha(protocol)==proof['protocol_sha256'],'Typed capability registration no longer matches proof')
    typed=read(protocol);cap=Path(cfg['capability_directory'])
    require(Path(typed['input_directory'])==cap,'Different saved capability package')
    observed=read(cap/'plan_query/observations.json');query_ids={q['query_id'] for q in cfg['query_suite']}
    require(len(observed)==2*len(query_ids) and len({r['measurement_id'] for r in observed})==len(observed)
            and {(r['phase'],r['query_id']) for r in observed}=={(phase,qid) for phase in ('fragmented','compacted') for qid in query_ids},
            'Actual saved preflight phase/query coverage differs')
    names={'prepare/result.json','plan_query/events.jsonl','plan_query/observations.json','plan_query/maintenance.json','source_reference/query_references.json'}
    for r in observed:
        names.add('plan_query/'+r['receipt'])
        prefix='plan_query/'+r['phase']+'_'+str(r['query_id'])
        names.update((prefix+'_FORMATTED.txt',prefix+'_COST.txt'))
    inputs={str(proofpath):sha(proofpath),str(protocol):sha(protocol)}
    for name in sorted(names):
        path=cap/name
        require(name in typed['input_files'] and sha(path)==typed['input_files'][name],
                'Actual preflight capability file differs from typed manifest: '+name)
        inputs[str(path)]=typed['input_files'][name]
    return inputs,dict(status='actual_preflight_reference_files_match_frozen_typed_manifest',
                       saved_query_cases=len(observed),files_checked=sorted(names),full_large_source_inventory_rehashed=False)


def run(campaign,output):
    campaign=Path(campaign).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    state=read(campaign/'result.json')
    require(state['status']=='completed_two_arm_terminal_evidence_validation_only' and
            state['passed_episodes']==2 and state['failed_episodes']==0 and state['unattempted_episodes']==0 and
            state['model_fit_performed'] is False,'Two-arm campaign not completed successfully; preserve state')
    entries=state.get('episodes',[]);require(len(entries)==2,'Missing independently audited episode entries')
    cfg=read(campaign/'registration.json')
    require(sha(campaign/'registration.json')==state['protocol_sha256'],'Campaign registration differs from terminal protocol')
    inputs,capability=capability_proof(cfg)
    inputs.update({str(campaign/'result.json'):sha(campaign/'result.json'),str(campaign/'registration.json'):sha(campaign/'registration.json')});prepared=[]
    for e in entries:
        directory=Path(e['raw']).resolve();require(directory.parent==campaign/'episodes','Not a canonical completed episode')
        audit=campaign/(e['experiment_id']+'_raw_audit.json')
        for p in (directory/'config.json',directory/'events.jsonl',directory/'result.json',audit):inputs[str(p)]=sha(p)
        require(inputs[str(directory/'events.jsonl')]==e['events_sha256'] and
                inputs[str(directory/'result.json')]==e['result_sha256'] and
                inputs[str(audit)]==e['independent_raw_audit_sha256'] and
                read(audit)['status']=='passed_full_raw_and_publication_reconstruction_only','Completed raw/audit binding differs')
        prepared.append(directory)
    write(output/'registration.json',dict(scope='supplementary_actual_counter_presence_only',
          inputs=inputs,script_sha256=sha(Path(__file__)),started_utc=datetime.now(timezone.utc).isoformat(),
          model_fitted=False,SQL_executed=False,calibration_accepted=False,scheduler_authorized=False))
    reports=[episode(d) for d in prepared]
    require(all(sha(p)==h for p,h in inputs.items()),'Completed input changed during independent audit')
    result=dict(status='passed_explicit_actual_engine_counter_presence_only',episodes=reports,capability_reference_audit=capability,
                zero_defaults_used=False,calibration_accepted=False,scheduler_authorized=False,
                ended_utc=datetime.now(timezone.utc).isoformat(),
                limitations=['Supplementary field-presence audit does not replace full raw/publication/task/multiset gates.',
                             'Observed marker attribution does not discover jobs which were never captured.',
                             'Engineering source reuse is not independent model or scheduler evidence.'])
    write(output/'result.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.campaign,a.output)
