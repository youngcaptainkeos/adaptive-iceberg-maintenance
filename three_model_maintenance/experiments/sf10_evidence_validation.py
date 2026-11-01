"""Two-arm engineering validation of prospective terminal engine archiving.

The original failed source window is explicitly reused for repair validation,
never independent training, accuracy, calibration or resource-efficiency proof.
No estimators are fitted and all original physical/publication gates remain.
"""
import argparse
import copy
import csv
import fcntl
import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime,timezone
from pathlib import Path
import urllib.request
from three_model_maintenance.contracts import require
from three_model_maintenance.training.data import read,save,sha
from three_model_maintenance.experiments.sf10_campaign import REPO,frozen,mapping,window,document,now


def registration(protocol):
    cfg=read(protocol);frozen(cfg)
    require(cfg['schema_version']=='sf10_matched_comparison_campaign_v2' and
            cfg['execution_scope']=='two_arm_terminal_evidence_validation_no_fit_v1','Unknown validation registration')
    require(cfg['arms']==['no_maintenance','compact_later'] and len(cfg['families'])==1,'Exactly two repair-validation arms required')
    require(cfg['families'][0]['role']=='engineering_reuse_not_training' and
            cfg['source_reuse']['independent_evidence'] is False and cfg['model_fit_authorized'] is False,
            'Engineering source reuse must not become training evidence')
    require(cfg['episode_template']['terminal_engine_archive_contract']=='completed_calls_before_final_validation_v1',
            'Prospective terminal-evidence contract required')
    require(subprocess.check_output(['git','show','HEAD:'+str(protocol.relative_to(REPO))],cwd=REPO)==protocol.read_bytes(),
            'Registration must be committed unchanged')
    if 'fresh_backend_result' in cfg['inputs']:
        service=read(Path(cfg['inputs']['fresh_backend_result']['path']))
        require(service['status']=='ready_fresh_isolated_backend_only' and
                service['base_url']==cfg['episode_template']['spark_rest_url'] and
                service['spark_app_id']==cfg['episode_template']['spark_app_id'],
                'Fresh backend identity differs from registered service proof')
    return cfg


def actual_preflight(cfg,out):
    """Reconstruct real source/12 saved SQL results; no synthetic fixture or SQL."""
    start,end,expanded,arrivals=window(cfg,cfg['families'][0])
    prior=read(Path(cfg['source_reuse']['original_mapping_record']['path']))
    require(sha(Path(cfg['source_reuse']['original_mapping_record']['path']))==cfg['source_reuse']['original_mapping_record']['sha256'],
            'Changed original mapping provenance')
    require(start.isoformat()==prior['source_interval_start_utc'] and end.isoformat()==prior['source_interval_end_utc'] and
            len(arrivals)==prior['arrival_count'],'Not the explicitly registered original engineering source window')
    from three_model_maintenance.runtime.sf10_contract import canonical_result,pin_query
    from three_model_maintenance.runtime.terminal_archive import validate_contract
    validate_contract(cfg['episode_template'])
    cap=Path(cfg['capability_directory']);tables={r['table']:r for r in read(cap/'prepare/result.json')['tables']}
    proto=dict(cfg['episode_template'],sf10_tables=tables,query_suite=cfg['query_suite'])
    events=[json.loads(s) for s in (cap/'plan_query/events.jsonl').open()]
    requests={r['measurement_id']:r for r in events if r['kind']=='statement_requested'}
    calls={r['measurement_id']:r for r in events if r['kind']=='statement_completed'}
    refs={r['query_id']:r['canonical_rows'] for r in read(Path(cfg['inputs']['query_references']['path']))}
    observations=read(cap/'plan_query/observations.json')
    for r in observations:
        receipt=read(cap/'plan_query'/r['receipt']);mid=r['measurement_id'];qid=r['query_id']
        require(canonical_result(calls[mid]['rows'],qid,proto)==refs[qid] and
                requests[mid]['sql']==pin_query(proto,tables['lineitem']['iceberg_table'],qid,receipt['snapshots']['lineitem']),
                'Actual saved SF10 SQL/result binding differs')
    # Validate the stricter task schema using only actually recorded REST payloads.
    # This checks field/identity compatibility, never upgrades the failed episode.
    from engine_archive import ArchivedTaskEvidence
    from three_model_maintenance.runtime.terminal_archive import _CachedTasks
    task_frames=0;task_records=0
    with Path(cfg['inputs']['failed_episode_events']['path']).open() as stream:
        for line in stream:
            event=json.loads(line)
            resource=event.get('resource','')
            if event.get('kind')=='spark_rest' and resource.startswith('stages/') and '/taskList?' in resource:
                fields=resource.split('/');stage,attempt=int(fields[1]),int(fields[2])
                count=int(resource.split('length=',1)[1]);actual=_CachedTasks(ArchivedTaskEvidence([event])).capture_tasks(stage,attempt,count)
                task_frames+=1;task_records+=len(actual)
    require(task_frames>0 and task_records>0,'No actual saved task frames to validate new archive schema')
    save(out/'preflight_result.json',dict(status='passed_actual_source_and_twelve_saved_sql_reconstructions_only',
        source_window=[start.isoformat(),end.isoformat()],expanded_interval=expanded,arrivals=len(arrivals),
        saved_sql_checks=len(observations),actual_retained_task_frames_checked=task_frames,actual_retained_task_records_checked=task_records,SQL_executed=False,model_fitted=False,independent_evidence=False))


def run(protocol,phase='campaign',episode_config=None,directory=None,output=None):
    cfg=registration(protocol)
    if phase=='episode':
        from three_model_maintenance.runtime.sf10_collect import run as collect
        collect(episode_config,subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip());return
    if phase=='audit':
        from three_model_maintenance.runtime.sf10_collect import audit
        from three_model_maintenance.runtime.collector_bridge import audit_publications
        path=Path(directory);raw=audit(path);publications=audit_publications(path);terminal=read(path/'result.json')
        require(raw['events_sha256']==terminal['events_sha256'] and publications==terminal['three_model_publication_audit'],
                'Independent raw/publication reconstruction differs from completed collector')
        save(Path(output),dict(status='passed_full_raw_and_publication_reconstruction_only',
            raw_audit=raw,publication_audit=publications,terminal_result_sha256=sha(path/'result.json'),
            independent_evidence=False,model_fit_authorized=False,ended_utc=now()));return
    root=Path(cfg['output_directory']);root.mkdir(parents=True,exist_ok=False);save(root/'registration.json',cfg)
    state=dict(status='starting',pid=os.getpid(),started_utc=now(),protocol_sha256=sha(protocol),stages=[],
               passed_episodes=0,failed_episodes=0,unattempted_episodes=2,model_fit_performed=False,
               independent_evidence=False,scheduler_authorized=False)
    locks=[]
    def progress():
        p=root/'progress.next.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'progress.json')
    def child(label,args):
        frozen(cfg);s=dict(label=label,started_utc=now());state['stages'].append(s);progress()
        with (root/(label+'.log')).open('x') as stream:
            p=subprocess.Popen([sys.executable,'-B',str(REPO/'scripts/phase6-live-evaluation/run_with_failure_alert.py'),
                '--label',cfg['label']+'_'+label,'--receipt',str(root/(label+'_failure_alert.json')),'--',*args],
                cwd=REPO,stdout=stream,stderr=subprocess.STDOUT)
            s['wrapper_pid']=p.pid;progress();rc=p.wait()
        s.update(returncode=rc,ended_utc=now());progress();require(rc==0,'Failed '+label+'; preserve original and new failures, no retry')
    try:
        for name in ('.three_model_collection.lock','.queue_aware_study.lock','.common_horizon_cohort.lock'):
            f=(REPO/'results'/name).open('a');locks.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(shutil.disk_usage(REPO).free>=cfg['minimum_data_free_bytes'] and
                shutil.disk_usage('/home/ccbd').free>=cfg['minimum_evidence_free_bytes'],'Registered free-space floors not met')
        mem=next(int(r.split()[1])*1024 for r in Path('/proc/meminfo').read_text().splitlines() if r.startswith('MemAvailable:'))
        require(mem>=cfg['minimum_available_memory_bytes'],'Registered available-memory floor not met')
        for url in cfg['idle_rest_endpoints']:
            with urllib.request.urlopen(url,timeout=cfg['episode_template']['rest_timeout_seconds']) as response:
                require(not json.load(response),'Active Spark work before validation admission')
        require(read(Path(cfg['inputs']['capability_audit']['path']))['status']=='passed_saved_sf10_typed_capability_audit_only',
                'Missing accepted typed SF10 capability')
        actual_preflight(cfg,root)
        if phase=='preflight':state['status']='completed_actual_source_preflight_only';return
        cap=Path(cfg['capability_directory']);prepared=read(cap/'prepare/result.json');maintenance=read(cap/'plan_query/maintenance.json')
        tables={r['table']:r for r in prepared['tables']};tables['lineitem'].update(snapshot_id=maintenance['after_snapshot'],
            file_count=maintenance['after_files'],data_bytes=maintenance['after_bytes'])
        source=dict(status='accepted_sf10_trace_source_with_typed_capability',table=tables['lineitem']['iceberg_table'],
            snapshot_id=tables['lineitem']['snapshot_id'],file_count=tables['lineitem']['file_count'],
            record_count=tables['lineitem']['rows'],capability_audit=cfg['inputs']['capability_audit'])
        save(root/'sf10_source.json',source);family=cfg['families'][0];mroot=root/'mapping';mapping(cfg,family,mroot)
        matched=None
        for arm in cfg['arms']:
            require(datetime.now(timezone.utc)<datetime.fromisoformat(cfg['no_new_episode_after_utc']),'No new episode after registered cutoff')
            require(shutil.disk_usage('/home/ccbd').free>=cfg['per_episode_evidence_budget_bytes'],'Per-arm evidence reserve unavailable')
            eid=cfg['label']+'_'+arm;work=Path(cfg['working_directory'])/eid;ecfg=copy.deepcopy(cfg['episode_template'])
            ecfg.update(experiment_id=eid,output_directory=str(work),destination_table='local.experiment.integrity_horizon_'+eid,
                action_arm=arm,action_offset_ns=None if arm=='no_maintenance' else cfg['horizon_seconds']*10**9//2,
                metadata_checkpoint_offsets_ns=[0,cfg['horizon_seconds']*10**9//2],engine_archive_offsets_ns=[],
                no_new_operation_after_utc=cfg['no_new_SQL_after_utc'],query_suite=cfg['query_suite'],sf10_tables=tables,
                preparation_result=dict(path=str(root/'sf10_source.json'),sha256=sha(root/'sf10_source.json')),
                typed_reference=cfg['inputs']['query_references'],mapping_record=dict(path=str(mroot/'mapping_record.json'),sha256=sha(mroot/'mapping_record.json')),
                mapping_audit=dict(path=str(mroot/'mapping_audit.json'),sha256=sha(mroot/'mapping_audit.json')))
            target=root/(eid+'.json');save(target,ecfg);state['status']='collecting_'+eid;state['unattempted_episodes']-=1;progress()
            try:
                child(eid,[sys.executable,'-B','-m','three_model_maintenance.experiments.sf10_evidence_validation',
                    '--protocol',str(protocol),'--phase','episode','--episode-config',str(target)])
            except Exception:state['failed_episodes']+=1;raise
            state['passed_episodes']+=1;state['status']='auditing_'+eid;progress()
            child(eid+'_raw_audit',[sys.executable,'-B','-m','three_model_maintenance.experiments.sf10_evidence_validation',
                '--protocol',str(protocol),'--phase','audit','--directory',str(work),'--output',str(root/(eid+'_raw_audit.json'))])
            # Preserve originals; canonical copy is a distinct verified transport artifact.
            archive=root/'episodes'/eid;shutil.copytree(work,archive)
            def contents(d):return {str(p.relative_to(d)):sha(p) for p in d.rglob('*') if p.is_file()}
            require(contents(work)==contents(archive),'Canonical raw copy differs')
            raw=[json.loads(s) for s in (archive/'events.jsonl').open()];initial=next(r for r in raw if r['kind']=='common_horizon_initial_state')
            inv=next(r for r in raw if r['kind']=='statement_completed' and r['measurement_id']==initial['file_inventory_measurement_id'])
            signature=(initial['file_state'],sorted((r[1],r[2]) for r in inv['rows']))
            if matched is None:matched=signature
            else:require(signature==matched,'Initial matched-layout row/byte distribution differs')
            entry=dict(experiment_id=eid,arm=arm,raw=str(archive),result_sha256=sha(archive/'result.json'),
                events_sha256=sha(archive/'events.jsonl'),independent_raw_audit_sha256=sha(root/(eid+'_raw_audit.json')),
                queries=len(read(archive/'result.json')['queries']),independent_evidence=False)
            state.setdefault('episodes',[]).append(entry);progress()
            document(cfg,'SF10 terminal-archive engineering arm passed '+eid,
                json.dumps(entry)+'. Full raw/publication reconstruction and canonical checksum passed. Source engineering reuse only; no fit, independent training, calibration, equal-work resource or scheduling superiority. Original02 remains0passed1failed5unattempted. Direct GitHub publication/client mirror verified before dependent arm.')
        state['status']='completed_two_arm_terminal_evidence_validation_only';progress()
        document(cfg,'SF10 two-arm terminal-evidence validation completed',
            'Actual2passed0failed0unattempted. ProtocolSHA '+sha(protocol)+', preterminalProgressSHA '+sha(root/'progress.json')+
            ', root '+str(root)+'. No fitting/objective change/independent evidence or scheduler promotion. Proceed to reviewed overhead/action-sensitivity gates, not automatic model training.')
    except Exception as exc:
        state.update(status='failed_or_blocked_preserved_no_retry',error=str(exc),traceback=traceback.format_exc())
        if phase!='preflight':
            try:document(cfg,'SF10 terminal-evidence validation failure preserved',json.dumps({k:state[k] for k in ('error','passed_episodes','failed_episodes','unattempted_episodes')})+'. No automatic retry or downstream fit; raw retained.')
            except Exception as doc:state['documentation_error']=str(doc)
        raise
    finally:
        state['ended_utc']=now();progress()
        if not (root/'result.json').exists():save(root/'result.json',state)
        for f in locks:f.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--phase',choices=('preflight','campaign','episode','audit'),default='campaign')
    for n in ('episode-config','directory','output'):p.add_argument('--'+n)
    a=p.parse_args();run(a.protocol.resolve(),a.phase,a.episode_config,a.directory,a.output)
