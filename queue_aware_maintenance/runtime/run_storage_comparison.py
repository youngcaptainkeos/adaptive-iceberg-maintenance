#!/usr/bin/env python3
"""Registered real-SQL ABBA storage comparison using an unchanged proven runtime."""
if __package__ in (None, ''):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
import ast
import copy
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from datetime import timedelta
from queue_aware_maintenance.core.common import checked, sha, require, write_json, now, utc, notify
from queue_aware_maintenance.observability.evidence_workspace import prepare_workspace, publish_terminal_copy
from queue_aware_maintenance.runtime.run_timing_study import append_docs

AUDIT = '''import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'queue_aware_maintenance'))
from audit_episode import audit
from compare_study import reconstruct_decisions
p=Path(sys.argv[1]); actual=audit(p)
actual['revision']=sys.argv[3]
assert actual==json.loads((p/'result.json').read_text()), 'Raw reconstruction differs'
replay=reconstruct_decisions(p)
Path(sys.argv[2]).write_text(json.dumps({'actual':actual,'decision_replay':replay},indent=2)+'\\n')
'''
PROOFS = '''import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'queue_aware_maintenance'))
from sampler_factory import build_sampler
from controller_factory import build_policy
from costs import EmpiricalCosts
from forecast import SeasonalArrivalForecast
cfg=json.loads(Path(sys.argv[1]).read_text())['episode_template']
build_sampler(cfg,None)
cost=EmpiricalCosts.load(cfg['model']['path'])
f=SeasonalArrivalForecast(cfg['arrivals'],origin=cfg['observation_origin_utc'],history_days=cfg['forecast_history_days'],bin_seconds=cfg['decision_interval_seconds'],freeze_source_time=cfg['forecast_history_freeze_utc'])
p=build_policy(cfg,cost,f)
assert cfg['policy']=='no_maintenance'
print('Original sampler/model source proofs and null controller constructed unchanged',flush=True)
'''

def save(path, value):
    """Durable replace of the coordinator's own progress; never raw producer files."""
    path=Path(path); tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as f:
        json.dump(value,f,indent=2,allow_nan=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
    tmp.replace(path)


def load(protocol):
    cfg=json.loads(Path(protocol).read_text())
    require(cfg['schema_version']=='matched_sql_evidence_storage_abba_v1','Unknown registration')
    require(cfg['order']==['evidence_disk','system_disk','system_disk','evidence_disk'],'Changed ABBA scope')
    require(cfg['episode_template']['policy']=='no_maintenance','Storage-only comparison requires no rewrite')
    runtime=Path(cfg['physical_runtime']); canonical=Path(cfg['canonical_repository'])
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=runtime,text=True).strip()==cfg['physical_revision'],'Changed physical revision')
    require((runtime/'results').resolve()==(canonical/'results').resolve(),'Physical runtime locks must share canonical results')
    names=list(cfg['physical_code_sha256'])
    require(not subprocess.check_output(['git','diff','HEAD','--',*['queue_aware_maintenance/'+n for n in names]],cwd=runtime,text=True),'Dirty frozen physical source')
    for name,h in cfg['physical_code_sha256'].items():
        require(sha(runtime/'queue_aware_maintenance'/name)==h,'Changed proven physical file '+name)
    repo=Path(__file__).resolve().parents[2]
    for name,h in cfg['coordinator_code_sha256'].items():
        p=repo/name; require(sha(p)==h,'Changed coordinator source '+name)
        if p.suffix=='.py':ast.parse(p.read_text())
    checked(cfg['baseline_study']); checked(cfg['baseline_episode_result'])
    for name in ('mapping','preparation_result','model','arrivals','snapshot_model_verification','telemetry_publication_validation','telemetry_publication_audit'):
        checked(cfg['episode_template'][name])
    for spec in cfg['episode_template']['expected_query_ledgers']:checked(spec)
    return cfg


def locked(cfg):
    handles=[]
    try:
        for name in ('.queue_aware_study.lock','.three_model_collection.lock','.common_horizon_cohort.lock'):
            h=(Path(cfg['canonical_repository'])/'results'/name).open('a'); handles.append(h)
            fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with (Path(cfg['canonical_repository'])/'results/.physical_correctness.lock').open('a') as h:
            fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return handles
    except BaseException:
        for h in handles:h.close()
        raise


def child(cfg, label, command, directory, report=None):
    directory=Path(directory); log=directory/(label+'.log')
    cmd=['nohup',sys.executable,'-B','-u',str(Path(cfg['canonical_repository'])/'scripts/phase6-live-evaluation/run_with_failure_alert.py'),'--label',label,'--receipt',str(directory/(label+'.failure_notification.json')),'--',*command]
    with log.open('x') as f:
        p=subprocess.Popen(cmd,cwd=cfg['physical_runtime'],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
        if report is not None:
            report['active_child']={'label':label,'wrapper_pid':p.pid,'log':str(log),'command':command}
            save(directory/'progress.json',report)
        rc=p.wait()
    if report is not None:
        report['last_child']=dict(report.pop('active_child'),returncode=rc,returned_utc=now()); save(directory/'progress.json',report)
    require(rc==0,'Child failed; no retry, preserve evidence: '+label)


def estimate(cfg):
    prior=json.loads(checked(cfg['baseline_study']).read_text())
    require(prior['status']=='completed_repeated_development_timing_study' and prior['passed']==8 and prior['failed']==prior['unattempted']==0,'Wrong complete development baseline')
    worst=max((utc(a['ended_utc'])-utc(a['started_utc'])).total_seconds() for a in prior['attempts'])
    per=worst+cfg['episode_template']['telemetry']['warmup_seconds']
    start=utc(now()); terminal=start+timedelta(seconds=4*per+cfg['final_reaudit_budget_seconds'])
    require(start+timedelta(seconds=3*per)<utc(cfg['no_new_episode_after_utc']) and terminal<utc(cfg['no_new_SQL_after_utc']),'Full four-arm budget fails cutoff; no thinning')
    return {'observed_max_whole_arm_seconds':worst,'per_arm_margin_seconds':cfg['episode_template']['telemetry']['warmup_seconds'],'final_reaudit_budget_seconds':cfg['final_reaudit_budget_seconds'],'estimated_terminal_utc':terminal.isoformat(),'guaranteed':False}


def preflight(protocol, out):
    out=Path(out); out.mkdir(parents=True,exist_ok=False)
    report={'status':'running','started_utc':now(),'protocol_sha256':sha(protocol),'new_SQL_executed':False}; handles=[]
    try:
        cfg=load(protocol); handles=locked(cfg); report['planning']=estimate(cfg)
        for loc in cfg['locations'].values():
            require(not os.path.lexists(loc['working_root']),'Working root already occupied')
            p=Path(loc['device_reference']); require(p.is_dir(),'Missing actual device reference')
            require(shutil.disk_usage(p).free>=4*cfg['per_arm_byte_budget'],'Insufficient full retained-work budget')
        require(os.stat(cfg['locations']['evidence_disk']['device_reference']).st_dev!=os.stat(cfg['locations']['system_disk']['device_reference']).st_dev,'Intervention devices are identical')
        subprocess.run([sys.executable,'-B','-u','-c',PROOFS,str(Path(protocol).resolve())],cwd=cfg['physical_runtime'],check=True)
        child(cfg,'queue_storage_original_raw_preflight_20261024',[sys.executable,'-B','-u','-c',AUDIT,str(Path(cfg['baseline_episode_result']['path']).parent),str(out/'baseline_raw_reconstruction.json'),cfg['physical_revision']],out)
        report.update(status='passed_real_source_and_unchanged_runtime_preflight',baseline_audit_sha256=sha(out/'baseline_raw_reconstruction.json'))
    except BaseException as e:
        report.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc()); raise
    finally:
        for h in handles:h.close()
        report['ended_utc']=now(); write_json(out/'result.json',report)


def analyze(protocol, root, output):
    cfg=load(protocol); root=Path(root); out=Path(output); out.mkdir(parents=True,exist_ok=False)
    progress=json.loads((root/'progress.json').read_text())
    require(progress['protocol_sha256']==sha(protocol) and progress['passed']==4 and progress['failed']==progress['unattempted']==0,'Incomplete study; no survivor comparison')
    report={'status':'running','started_utc':now(),'protocol_sha256':sha(protocol),'policy_benefit_established':False}; rows=[]; signature=None
    try:
        for item in progress['attempts']:
            require(item['status']=='passed','Failed physical unit')
            d=Path(item['archive']); require(sha(d/'result.json')==item['result_sha256'],'Changed terminal result')
            require(sha(root/'protocols'/(item['experiment_id']+'.json'))==item['episode_protocol_sha256'],'Changed episode registration')
            require((d/'config.json').read_bytes()==(root/'protocols'/(item['experiment_id']+'.json')).read_bytes(),'Raw config differs')
            rebuilt=out/(item['experiment_id']+'.raw.json')
            child(cfg,item['experiment_id']+'_independent_reaudit',[sys.executable,'-B','-u','-c',AUDIT,str(d),str(rebuilt),cfg['physical_revision']],out)
            actual=json.loads(rebuilt.read_text())['actual']
            current={k:actual[k] for k in ('initial_layout_signature','initial_file_state','final_file_state','arrival_count','completed','maintenance_count')}
            if signature is None:signature=current
            else:require(current==signature,'Unmatched actual population/layout/final state')
            require(actual['maintenance_count']==0 and actual['completed']==3094,'Wrong no-maintenance population')
            clock=None; calls=0; last=None
            with (d/'events.jsonl').open() as f:
                for line in f:
                    r=json.loads(line)
                    if r['kind']=='cohort_clock':clock=r['start_monotonic_ns']
                    if r['kind']=='statement_completed' and r.get('role')=='trace_query':
                        calls+=r['client_elapsed_ns']; last=r['fetch_end']['monotonic_ns']
            elapsed=last-clock; require(elapsed>=calls,'Invalid call partition')
            rows.append({'experiment_id':item['experiment_id'],'location':item['location'],'sum_response_ns':actual['sum_response_ns'],'mean_response_seconds':actual['mean_response_seconds'],'drain_seconds':elapsed/1e9,'foreground_call_seconds':calls/1e9,'outside_foreground_call_seconds':(elapsed-calls)/1e9,'result_sha256':item['result_sha256']})
        contrasts=[]
        for a,b in ((0,1),(3,2)):
            base,fast=rows[a],rows[b]
            contrasts.append({'evidence_disk':base['experiment_id'],'system_disk':fast['experiment_id'],'fraction_lower_total_response':1-fast['sum_response_ns']/base['sum_response_ns'],'drain_difference_seconds':fast['drain_seconds']-base['drain_seconds'],'outside_call_difference_seconds':fast['outside_foreground_call_seconds']-base['outside_foreground_call_seconds']})
        report.update(status='passed_four_arm_raw_storage_comparison_only',episodes=rows,contrasts=contrasts,lower_response_both_pairs=all(x['fraction_lower_total_response']>0 for x in contrasts),limitations=cfg['limitations'])
        lines=['# Matched SQL evidence-storage comparison','','Four full-drain raw audits passed. All results retained; no policy or calibration acceptance.','','| Location | Run | Mean response(s) | Drain(s) | SQL calls(s) | Outside SQL(s) |','|---|---|---:|---:|---:|---:|']
        for r in rows:lines.append(f"| {r['location']} | {r['experiment_id']} | {r['mean_response_seconds']:.3f} | {r['drain_seconds']:.3f} | {r['foreground_call_seconds']:.3f} | {r['outside_foreground_call_seconds']:.3f} |")
        lines+=['','## Every registered paired contrast',json.dumps(contrasts,indent=2),'','Two pairs on one development window cannot establish significance, universal speedup or forecast-aware scheduling benefit.']
        (out/'report.md').write_text('\n'.join(lines)+'\n')
    except BaseException as e:report.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc()); raise
    finally:report['ended_utc']=now(); write_json(out/'result.json',report)


def run(protocol, preflight_result):
    cfg=load(protocol); proof=json.loads(checked({'path':preflight_result,'sha256':sha(preflight_result)}).read_text())
    require(proof['status']=='passed_real_source_and_unchanged_runtime_preflight' and proof['protocol_sha256']==sha(protocol),'Preflight not passed')
    root=Path(cfg['output_directory']); root.mkdir(parents=True,exist_ok=False); handles=[]
    report={'status':'starting','started_utc':now(),'pid':os.getpid(),'protocol_sha256':sha(protocol),'coordinator_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[2],text=True).strip(),'physical_revision':cfg['physical_revision'],'passed':0,'failed':0,'unattempted':4,'attempts':[]}
    save(root/'progress.json',report)
    def message(label,body):notify(label,body,root/(label+'.notification.json'),cfg['notification_configuration'])
    try:
        handles=locked(cfg); report['admission']=estimate(cfg); (root/'protocols').mkdir()
        shutil.copyfile(protocol,root/'registration.json'); shutil.copyfile(preflight_result,root/'preflight.json')
        # Freeze all four identities/configs before the first physical operation.
        manifest=[]
        for i,location in enumerate(cfg['order'],1):
            eid=cfg['experiment_prefix']+f'_{i:02d}'
            base=Path(cfg['locations'][location]['working_root'])/eid
            ecfg=copy.deepcopy(cfg['episode_template']); ecfg.update(experiment_id=eid,destination_table='local.experiment.'+eid,output_directory=str(base/'episode'),no_new_operation_after_utc=cfg['no_new_SQL_after_utc'])
            p=root/'protocols'/(eid+'.json'); write_json(p,ecfg)
            manifest.append({'experiment_id':eid,'location':location,'workspace':str(base),'working_episode':ecfg['output_directory'],'archive':str(root/'episodes'/eid),'episode_protocol_sha256':sha(p)})
        write_json(root/'manifest.json',manifest)
        report['initial_documentation']=append_docs(cfg,'Queue matched storage comparison started',f"Four full3094arrival null-maintenance arms ABBA, frozen original runtime{cfg['physical_revision']}; only evidence device changes. ProtocolSHA{sha(protocol)}, coordinator{report['coordinator_revision']}, PID{os.getpid()}, planning{json.dumps(report['admission'])}. Output{root}; registered full source/correctness/freshness/perrecordfsync/snapshot/task/FIFO/full-drain gates unchanged. No synthetic labels/model fits or policy acceptance. Each terminal package copied/fsynced/checksummed to canonical archive; all work retained. Worker documentation commits use previously authorized deferred GitHub publication; client sync at next check.")
        report['status']='running'; save(root/'progress.json',report); message('queue_storage_started','Started four matched full-drain SQL runs, ABBA disks, no compaction. Estimated five to six hours, no automatic retries. '+str(root))
        matched=None
        for item in manifest:
            load(protocol); require(utc(now())<utc(cfg['no_new_episode_after_utc']),'Episode cutoff reached; preserve unattempted scope')
            require(shutil.disk_usage(cfg['locations'][item['location']]['device_reference']).free>=4*cfg['per_arm_byte_budget'],'Insufficient retained-work headroom')
            attempt=dict(item,status='preparing',started_utc=now()); report['attempts'].append(attempt); report['unattempted']-=1
            attempt['workspace_admission']=prepare_workspace(item['workspace'],device_reference=cfg['locations'][item['location']]['device_reference'],required_bytes=cfg['per_arm_byte_budget']); save(root/'progress.json',report)
            command=[sys.executable,'-B','-u',str(Path(cfg['physical_runtime'])/'queue_aware_maintenance/run_episode.py'),'--protocol',str(root/'protocols'/(item['experiment_id']+'.json')),'--expected-revision',cfg['physical_revision']]
            attempt['status']='running'; child(cfg,item['experiment_id'],command,root,report)
            d=Path(item['working_episode']); p=d/'result.json'; result=json.loads(p.read_text())
            require(result['status']=='audited_complete_real_full_drain_episode_only' and result['completed']==result['arrival_count']==3094 and result['unfinished']==result['maintenance_count']==0,'Not full audited null-maintenance run')
            signature={k:result[k] for k in ('initial_layout_signature','initial_file_state','final_file_state')}
            if matched is None:matched=signature
            else:require(signature==matched,'Changed actual table layout')
            attempt['result_sha256']=sha(p)
            attempt['publication']=publish_terminal_copy(d,item['archive'],result_sha256=sha(p),expected_terminal_status=result['status'])
            require(attempt['publication']['bytes']<=cfg['per_arm_byte_budget'],'Artifact exceeded registered budget; no next arm')
            attempt.update(status='passed',ended_utc=now(),completed=result['completed'],sum_response_ns=result['sum_response_ns'],events_sha256=result['events_sha256']); report['passed']+=1; save(root/'progress.json',report)
            attempt['documentation']=append_docs(cfg,'Queue storage arm completed '+item['experiment_id'],f"Location{item['location']}, all{result['completed']}queries/full-drain/raw gates passed, zero rewrite. ResultSHA{sha(p)}, eventsSHA{result['events_sha256']}, response{result['sum_response_ns']}ns, drain{result['drain_end_after_start_seconds']}s. Verified retained working→canonical archive{item['archive']}, manifest{attempt['publication']['manifest_sha256']}. No survivor comparison. Original working evidence retained; full client mirror pending.")
            save(root/'progress.json',report); message(item['experiment_id']+'_complete',f"Storage arm{report['passed']}/4 passed all3094queries and verified archive, {item['location']}. No performance claim before all four raw reconstructions.")
        report['status']='all_arms_pending_independent_analysis'; save(root/'progress.json',report)
        child(cfg,'queue_storage_complete_analysis_20261024',[sys.executable,'-B','-u',str(Path(__file__).resolve()),'--phase','analyze','--protocol',str(Path(protocol).resolve()),'--output',str(root/'analysis')],root,report)
        result=json.loads((root/'analysis/result.json').read_text()); require(result['status']=='passed_four_arm_raw_storage_comparison_only','Final analysis failed')
        report['analysis_sha256']=sha(root/'analysis/result.json')
        report['documentation']=append_docs(cfg,'Queue matched storage comparison terminal review',f"Four complete arms and independent raw reconstruction passed; analysisSHA{report['analysis_sha256']}, all contrasts{json.dumps(result['contrasts'])}. Report{root/'analysis/report.md'}. One development window/two order-balanced pairs only; no independent significance, calibration, model or scheduling-benefit acceptance. All negative results/raw copies retained. Client backup pending explicit checksum confirmation.")
        report['status']='completed_storage_comparison_development_only'; message('queue_storage_terminal','Four full-drain storage runs and independent audits completed. See saved analysis/report.md; no scheduler benefit claim. '+str(root))
    except BaseException as e:
        report.update(status='failed_preserved_no_retry',error=str(e),traceback=traceback.format_exc())
        if report['attempts'] and report['attempts'][-1]['status']!='passed':report['attempts'][-1]['status']='failed_preserved'; report['failed']+=1
        save(root/'progress.json',report)
        try:report['failure_documentation']=append_docs(cfg,'Queue storage comparison failure preserved',f"Error{e}; passed{report['passed']}/failed{report['failed']}/unattempted{report['unattempted']}. Logs/raw{root}. No retries/survivor comparison; failed working artifacts retained, do not claim completed mirror.")
        except Exception as error:report['documentation_error']=str(error)
        raise
    finally:
        report['ended_utc']=now(); save(root/'progress.json',report); write_json(root/'result.json',report)
        for h in handles:h.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--phase',choices=('preflight','run','analyze'),required=True); p.add_argument('--protocol',required=True); p.add_argument('--output'); p.add_argument('--preflight-result'); a=p.parse_args()
    if a.phase=='preflight':preflight(a.protocol,a.output)
    elif a.phase=='analyze':analyze(a.protocol,json.loads(Path(a.protocol).read_text())['output_directory'],a.output)
    else:run(a.protocol,a.preflight_result)
