#!/usr/bin/env python3
"""Bounded real-query plan/maintenance collection, not fitted-model promotion."""
if __package__ in (None,''):
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
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
import time
import traceback
from datetime import timedelta
from queue_aware_maintenance.core.common import checked,sha,require,write_json,utc,now,notify
from queue_aware_maintenance.observability.complexity_adapter import original,install,capture
from queue_aware_maintenance.observability.evidence_workspace import prepare_workspace,publish_terminal_copy
from queue_aware_maintenance.runtime.run_storage_comparison import locked,child,save
from queue_aware_maintenance.runtime.run_timing_study import append_docs
from queue_aware_maintenance.audits.audit_complexity_episode import audit,plan_records

REPO=Path(__file__).resolve().parents[2]


def load(protocol):
    cfg=json.loads(Path(protocol).read_text());require(cfg['schema_version']=='queue_complexity_maintenance_bounded_v1','Unknown unit')
    require([x['policy'] for x in cfg['arms']]==['no_maintenance','fixed_start'] and cfg['arms'][1]['fixed_start_seconds']==600,'Changed bounded control/maintenance scope')
    for n,h in cfg['complexity_source_sha256'].items():
        p=REPO/n;require(sha(p)==h,'Changed frozen complexity source '+n)
        if p.suffix=='.py':ast.parse(p.read_text())
    proof=json.loads(checked(cfg['storage_result']).read_text());require(proof['status']=='passed_four_arm_raw_storage_comparison_only','Missing actual storage comparison')
    base=original(cfg)
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=cfg['physical_runtime'],text=True).strip()==cfg['physical_revision'],'Wrong original frozen HEAD')
    require((Path(cfg['physical_runtime'])/'results').resolve()==(Path(cfg['canonical_repository'])/'results').resolve(),'Shared physical lock path differs')
    for n in ('mapping','preparation_result','model','arrivals','snapshot_model_verification','telemetry_publication_validation','telemetry_publication_audit'):checked(cfg['episode_template'][n])
    for spec in cfg['episode_template']['expected_query_ledgers']:checked(spec)
    return cfg,base


def guard(cfg):require(utc(now())<utc(cfg['no_new_SQL_after_utc']),'No new SQL after registered cutoff')


def preflight(protocol,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False);report={'status':'running','started_utc':now(),'protocol_sha256':sha(protocol),'new_query_cost_labels':0};handles=[];log=None;connection=None
    try:
        cfg,base=load(protocol);handles=locked(cfg);guard(cfg)
        physical=(Path(cfg['canonical_repository'])/'results/.physical_correctness.lock').open('a');handles.append(physical);fcntl.flock(physical,fcntl.LOCK_EX|fcntl.LOCK_NB)
        from physical_measurements import EventLog,StatementRecorder,SparkEvidence
        from run_correctness_pilot import query_templates
        from pyhive import hive
        d=Path(cfg['plan_source_episode']);saved=json.loads(checked(cfg['plan_source_result']).read_text())
        require(sha(d/'events.jsonl')==saved['events_sha256'] and saved['maintenance_count']==0 and saved['completed']==3094,'Changed real plan source episode')
        old=json.loads((d/'config.json').read_text());snapshots={r['snapshot_id'] for r in saved['queries']};require(len(snapshots)==1,'Ambiguous source snapshot');snapshot=next(iter(snapshots))
        log=EventLog(out/'events.jsonl','queuecomplexity_plan_preflight_20261025');rec=StatementRecorder(log);rest=SparkEvidence(old['spark_rest_url'],old['spark_app_id'],old['rest_timeout_seconds'],log)
        require(not rest._capture('jobs?status=running'),'Competing active Spark work')
        connection=hive.Connection(**{k:old['engine'][k] for k in ('host','port','username')});cursor=connection.cursor();plans=[]
        # Existing immutable terminal snapshots are read-only plan-capability
        # sources; neither table reuse nor a new query-performance experiment.
        for qid,sql in enumerate(query_templates(old['destination_table'])):
            guard(cfg);sql=sql.replace('FROM '+old['destination_table'],'FROM '+old['destination_table']+' VERSION AS OF '+str(snapshot))
            plans.append(capture(rec,cursor,sql,qid,dict(cfg,no_new_operation_after_utc=cfg['no_new_SQL_after_utc'])))
        log.close();log=None
        rows=[json.loads(s) for s in (out/'events.jsonl').open()];_,_,receipts,_=plan_records(rows)
        require(len(receipts)==4,'Four actual query plans required')
        report.update(status='passed_actual_four_query_plan_and_source_preflight_only',actual_SQL_explain_calls=8,plan_features=[r['parsed']['features'] for r in receipts.values()],events_sha256=sha(out/'events.jsonl'),source_snapshot=snapshot,source_terminal_result_sha256=cfg['plan_source_result']['sha256'],runtime_model_changed=False,limitations=['Real EXPLAIN outputs only, no executed query-cost labels or fitted predictor.','Four single-table templates do not validate joins/unseen templates or SF10.'])
    except BaseException as e:report.update(status='failed_preserved_no_retry',error=str(e),traceback=traceback.format_exc());raise
    finally:
        if log is not None:log.close()
        if connection is not None:connection.close()
        for h in handles:h.close()
        report['ended_utc']=now();write_json(out/'result.json',report)


def episode(protocol):
    p=Path(protocol);ecfg=json.loads(p.read_text());cfg=json.loads(checked(ecfg['complexity_unit_protocol']).read_text());cfg,base=load(ecfg['complexity_unit_protocol']['path'])
    require(ecfg['complexity_source_sha256']==cfg['complexity_source_sha256'],'Changed episode adapter binding')
    install(base,ecfg,REPO);base.run(str(p),cfg['physical_revision'])
    audit(ecfg['output_directory'],Path(ecfg['output_directory'])/'complexity_audit')


def analysis(protocol,output):
    cfg,_=load(protocol);root=Path(cfg['output_directory']);out=Path(output);out.mkdir(parents=True,exist_ok=False)
    p=json.loads((root/'progress.json').read_text());require(p['passed']==2 and p['failed']==p['unattempted']==0,'No survivor analysis')
    rows=[]
    for a in p['attempts']:
        d=Path(a['archive']);require(sha(d/'result.json')==a['result_sha256'] and sha(d/'complexity_audit/result.json')==a['complexity_audit_sha256'],'Changed accepted candidate package')
        rebuilt=audit(d,out/a['experiment_id']);saved=json.loads((d/'complexity_audit/result.json').read_text());require(rebuilt==saved,'Independent complete plan/feature reconstruction differs')
        old=json.loads((d/'result.json').read_text());rows.append({'experiment_id':a['experiment_id'],'policy':a['policy'],'completed':old['completed'],'mean_response_seconds':old['mean_response_seconds'],'sum_response_ns':old['sum_response_ns'],'drain_seconds':old['drain_end_after_start_seconds'],'maintenance_count':old['maintenance_count'],'maintenance_service_seconds':old['maintenance_service_seconds'],'plan_receipts':saved['actual_plan_receipts'],'support':saved['support'],'fragmented_pending_observations':saved['fragmented_pending_observations'],'fragmented_nonpending_observations':saved['fragmented_nonpending_observations']})
    require(rows[0]['maintenance_count']==0 and rows[1]['maintenance_count']==1,'Registered maintenance did not happen')
    result={'status':'passed_two_real_episode_complexity_maintenance_reconstruction_only','episodes':rows,'matched_fragmented_pending_rows':rows[1]['fragmented_pending_observations'],'matched_fragmented_nonpending_rows':sum(r['fragmented_nonpending_observations'] for r in rows),'maintenance_minus_control_total_response_ns':rows[1]['sum_response_ns']-rows[0]['sum_response_ns'],'plan_features_integrated_in_predictor':False,'training_accepted':False,'calibration_accepted':False,'policy_superiority_accepted':False,'limitations':cfg['limitations']}
    write_json(out/'result.json',result)
    lines=['# Queue complexity / maintenance bounded unit','','Both full raw/plan audits passed. This is candidate collection and a maintenance-enabled boundary check, not model validation or a policy-benefit test.','','| Policy | Queries | Mean response(s) | Drain(s) | Actual rewrites | Fragmented pending | Fragmented nonpending |','|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['policy']} | {r['completed']} | {r['mean_response_seconds']:.3f} | {r['drain_seconds']:.3f} | {r['maintenance_count']} | {r['fragmented_pending_observations']} | {r['fragmented_nonpending_observations']} |")
    lines+=['','Plan features are captured/bound before query execution; the old frozen model does not consume them. Support and missing offered history are explicit. No causal pending-state penalty or independent accuracy/calibration follows.']
    (out/'report.md').write_text('\n'.join(lines)+'\n')


def run(protocol,preflight_result):
    cfg,_=load(protocol);pre=json.loads(Path(preflight_result).read_text());require(pre['status']=='passed_actual_four_query_plan_and_source_preflight_only' and pre['protocol_sha256']==sha(protocol),'Actual plan capability not passed')
    root=Path(cfg['output_directory']);root.mkdir(parents=True,exist_ok=False);handles=[]
    r={'status':'starting','started_utc':now(),'pid':os.getpid(),'protocol_sha256':sha(protocol),'attempts':[],'passed':0,'failed':0,'unattempted':2}
    save(root/'progress.json',r)
    def announce(label,message):notify(label,message,root/(label+'.notification.json'),cfg['notification_configuration'])
    try:
        # A laptop backup is not part of the controlled foreground workload.
        # Wait for its actual sender to leave; never cancel/restart that transfer.
        while any('rsync --server --sender' in s and '/results/queue_storage_sql_20261024/' in s for s in subprocess.check_output(['ps','-eo','args'],text=True).splitlines() if s.lstrip().startswith('rsync ')):
            require(utc(now())<utc(cfg['no_new_episode_after_utc']),'Backup wait consumed launch allowance')
            r['status']='waiting_for_previous_raw_transfer';save(root/'progress.json',r);time.sleep(30)
        handles=locked(cfg);guard(cfg)
        baseline=json.loads(checked(cfg['storage_terminal']).read_text());worst=max((utc(a['ended_utc'])-utc(a['started_utc'])).total_seconds() for a in baseline['attempts']);per=worst+cfg['episode_template']['telemetry']['warmup_seconds'];end=utc(now())+timedelta(seconds=2*per+cfg['reaudit_budget_seconds'])
        require(end<utc(cfg['no_new_SQL_after_utc']) and utc(now())+timedelta(seconds=per)<utc(cfg['no_new_episode_after_utc']),'Whole-unit observed-runtime budget fails')
        r['estimated_terminal_utc']=end.isoformat();shutil.copyfile(protocol,root/'registration.json');shutil.copyfile(preflight_result,root/'preflight.json');(root/'protocols').mkdir();manifest=[]
        for i,a in enumerate(cfg['arms'],1):
            eid=cfg['experiment_prefix']+f'_{i:02d}';work=Path(cfg['working_root'])/eid
            ep=copy.deepcopy(cfg['episode_template']);ep.update(a,experiment_id=eid,destination_table='local.experiment.'+eid,output_directory=str(work/'episode'),no_new_operation_after_utc=cfg['no_new_SQL_after_utc'],physical_runtime=cfg['physical_runtime'],physical_revision=cfg['physical_revision'],physical_code_sha256=cfg['physical_code_sha256'],complexity_source_sha256=cfg['complexity_source_sha256'],source_overlap_family=cfg['source_overlap_family'],complexity_limitations=cfg['limitations'],complexity_unit_protocol={'path':str(Path(protocol).resolve()),'sha256':sha(protocol)})
            p=root/'protocols'/(eid+'.json');write_json(p,ep);manifest.append({'experiment_id':eid,'policy':a['policy'],'protocol':str(p),'protocol_sha256':sha(p),'workspace':str(work),'working_episode':str(work/'episode'),'archive':str(root/'episodes'/eid)})
        write_json(root/'manifest.json',manifest);r['status']='running';save(root/'progress.json',r)
        r['documentation']=append_docs(cfg,'Queue complexity and maintenance unit started',f"Two full3094arrival/16file matched development arms null/fixed600, originalphysical{cfg['physical_revision']}, newversionedplanadapter. ActualpreflightSHA{sha(preflight_result)}, protocolSHA{sha(protocol)}, PID{os.getpid()}, estimatedterminal{r['estimated_terminal_utc']}, output{root}. Sharedlocks/strictfreshness/perrecordfsync/wholecohort/rawtasks unchanged. RealpreexecutionFORMATTED/COST cache byexactSQLsnapshot; unknownstatsNone, no model fit/predictor promotion or synthetic/counterfactual labels. ActualA/Bfragmented support may remain insufficient/missing; preserve results. Each major stage bothmethodologydocs committed; authorized deferredworkerpush/clientmirror pendingnextcheck.")
        announce('queue_complexity_started','Started bounded two-episode maintenance/plan-feature unit; full cohort, no fit/promotion. '+str(root))
        matched=None
        for item in manifest:
            load(protocol);require(utc(now())<utc(cfg['no_new_episode_after_utc']),'No new episode after cutoff')
            require(shutil.disk_usage(cfg['device_reference']).free>=2*cfg['per_arm_byte_budget'],'Insufficient retained evidence budget')
            a=dict(item,status='running',started_utc=now());r['attempts'].append(a);r['unattempted']-=1;save(root/'progress.json',r)
            a['workspace_admission']=prepare_workspace(item['workspace'],device_reference=cfg['device_reference'],required_bytes=cfg['per_arm_byte_budget'])
            child(cfg,item['experiment_id'],[sys.executable,'-B','-u',str(Path(__file__).resolve()),'--phase','episode','--protocol',item['protocol']],root,r)
            d=Path(item['working_episode']);physical=json.loads((d/'result.json').read_text());features=json.loads((d/'complexity_audit/result.json').read_text())
            require(physical['completed']==physical['arrival_count']==3094 and physical['unfinished']==0 and features['completed']==3094,'Incomplete real cohort')
            sig=(physical['initial_layout_signature'],physical['initial_file_state'])
            if matched is None:matched=sig
            else:require(sig==matched,'Mismatched initial layout')
            expected=0 if item['policy']=='no_maintenance' else 1;require(physical['maintenance_count']==expected,'Actual intervention missing')
            a['result_sha256']=sha(d/'result.json');a['complexity_audit_sha256']=sha(d/'complexity_audit/result.json');a['publication']=publish_terminal_copy(d,item['archive'],result_sha256=a['result_sha256'],expected_terminal_status='audited_complete_real_full_drain_episode_only');require(a['publication']['bytes']<=cfg['per_arm_byte_budget'],'Registered budget exceeded; preserve completed work/no dependent arm')
            a.update(status='passed',ended_utc=now(),completed=physical['completed'],support=features['support']);r['passed']+=1;save(root/'progress.json',r)
            a['documentation']=append_docs(cfg,'Queue complexity arm completed '+item['experiment_id'],f"Full3094query originalraw/planbinding gates passed, policy{item['policy']}, actualrewrites{physical['maintenance_count']}, resultSHA{a['result_sha256']}, eventsSHA{physical['events_sha256']}, candidateSHA{a['complexity_audit_sha256']}, support{json.dumps(features['support'])}. Allplan/candidate/raw sources retained and canonical copy verified; clientmirror pending. Oldcostmodelunchanged, no training/calibration/causalpendingpenalty or policy acceptance. Output{item['archive']}.")
            announce(item['experiment_id']+'_completed',f"Arm{r['passed']}/2 raw/plan audit passed; {physical['completed']}queries, maintenance{physical['maintenance_count']}. Candidate support saved, no fit claims.")
        r['status']='all_episodes_pending_independent_audit';save(root/'progress.json',r)
        child(cfg,'queue_complexity_final_analysis_20261025',[sys.executable,'-B','-u',str(Path(__file__).resolve()),'--phase','analysis','--protocol',str(Path(protocol).resolve()),'--output',str(root/'analysis')],root,r)
        result=json.loads((root/'analysis/result.json').read_text());r['analysis_sha256']=sha(root/'analysis/result.json');r['status']='completed_bounded_plan_collection_and_maintenance_validation_only'
        r['documentation']=append_docs(cfg,'Queue complexity unit terminal review',f"Two fullcohorts/independentrawplanexport reconstruction passed; analysisSHA{r['analysis_sha256']}, fragmentedpending{result['matched_fragmented_pending_rows']}/nonpending{result['matched_fragmented_nonpending_rows']}. Descriptive maintenance-minuscontrol response{result['maintenance_minus_control_total_response_ns']}ns, not replicatedcausalcomparison. Newplanfeatures bound/collected but predictor notchanged/trained; allhistorymasks/support/missingness preserved. Sourceoneconsumedfamily, no calibration/generalization/novelty accepted. Report{root/'analysis/report.md'}, fullclientmirror pending.")
        announce('queue_complexity_terminal','Two full episodes and independent audits complete. Saved plan-feature/support report; no trained model or policy-benefit acceptance. '+str(root))
    except BaseException as e:
        r.update(status='failed_preserved_no_retry',error=str(e),traceback=traceback.format_exc())
        if r['attempts'] and r['attempts'][-1]['status']!='passed':r['attempts'][-1]['status']='failed_preserved';r['failed']+=1
        try:r['failure_documentation']=append_docs(cfg,'Queue complexity failure preserved',f"Error{e}; passed{r['passed']}/failed{r['failed']}/unattempted{r['unattempted']}. No retry/survivoranalysis/gate weakening. Raw/progress{root}; failed/partial evidence retained.")
        except Exception as error:r['documentation_error']=str(error)
        raise
    finally:
        r['ended_utc']=now();save(root/'progress.json',r);write_json(root/'result.json',r)
        for h in handles:h.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',required=True,choices=('preflight','run','episode','analysis'));p.add_argument('--protocol',required=True);p.add_argument('--output');p.add_argument('--preflight-result');a=p.parse_args()
    if a.phase=='preflight':preflight(a.protocol,a.output)
    elif a.phase=='episode':episode(a.protocol)
    elif a.phase=='analysis':analysis(a.protocol,a.output)
    else:run(a.protocol,a.preflight_result)
