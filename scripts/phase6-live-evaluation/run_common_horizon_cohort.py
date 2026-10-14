#!/usr/bin/env python3
"""Complete preregistered serial action/control cohort with raw audit before each dependency."""
import argparse,fcntl,json,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from experiment_validation import load_json,require,verified_file,sha256


def run(config,revision):
    cfg,base=load_json(config);repo=Path(__file__).resolve().parents[2];module=Path(__file__).parent
    require(cfg['schema_version']=='common_horizon_cohort_pilot_v1','Unknown cohort')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==revision,'Initial HEAD differs')
    paths=[verified_file(spec,base) for spec in cfg['episodes']];settings=[json.loads(p.read_text()) for p in paths]
    require([c['action_arm'] for c in settings]==cfg['registered_order'] and len({c['experiment_id'] for c in settings})==len(settings) and len({c['destination_table'] for c in settings})==len(settings),'Order/unique episode registration differs')
    common=('mapping_record','mapping_audit','preparation_result','expected_query_ledgers','engine','spark_app_id','spark_rest_url','telemetry','client_count','boundary_rule','metadata_checkpoint_offsets_ns','no_new_operation_after_utc','decision_state_contract','metadata_max_age_seconds')
    require(all(all(c[k]==settings[0][k] for k in common) for c in settings),'Different non-action conditions')
    lock=(repo/'results'/'.common_horizon_cohort.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False);shutil.copy2(config,out/'config.json');code=out/'code';code.mkdir()
    dependencies=('run_common_horizon_cohort.py','run_trace_queue_diagnostic.py','common_horizon_binding.py','offered_queue_ledger.py','prepare_trace_benchmark_mapping.py','physical_measurements.py','experiment_validation.py','statement_timing.py','query_observation_binding.py','telemetry_binding.py','run_correctness_pilot.py','engine_overlap.py')
    digests={name:sha256(module/name) for name in dependencies}
    for name in dependencies:shutil.copy2(module/name,code/name)
    report={'schema_version':cfg['schema_version'],'status':'running','protocol_revision':revision,'code_sha256':digests,'started_utc':datetime.now(timezone.utc).isoformat(),'planned_episodes':len(settings),'attempts':[],'cost_training_accepted':False,'limitations':cfg['limitations']};signature=None
    def checkpoint(name='progress.json'):(out/name).write_text(json.dumps(report,indent=2)+'\n')
    checkpoint()
    try:
        for index,(path,c) in enumerate(zip(paths,settings),start=1):
            require(datetime.now(timezone.utc)<datetime.fromisoformat(c['no_new_operation_after_utc']),'No new episode after cutoff')
            require(all(sha256(module/name)==digest for name,digest in digests.items()),'Runtime code changed')
            require(sha256(path)==cfg['episodes'][index-1]['sha256'],'Registered config changed')
            # Documentation-only commits are permitted; code/protocol changes are not.
            require(subprocess.run(['git','diff','--exit-code',revision,'HEAD','--','scripts/phase6-live-evaluation/*.py','docs/experiment_protocols/*.json'],cwd=repo,capture_output=True).returncode==0,'Code/protocol revision changed')
            head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
            attempt={'index':index,'experiment_id':c['experiment_id'],'action_arm':c['action_arm'],'status':'running','protocol_sha256':sha256(path),'execution_head':head,'started_utc':datetime.now(timezone.utc).isoformat()};report['attempts'].append(attempt);checkpoint()
            raw=(base/c['output_directory']).resolve()
            with (out/f'episode_{index:02d}.log').open('x') as log:
                result=subprocess.run([sys.executable,str(module/'run_trace_queue_diagnostic.py'),'--config',str(path),'--expected-revision',head],cwd=repo,stdout=log,stderr=subprocess.STDOUT)
            attempt['returncode']=result.returncode;require(result.returncode==0,'Physical episode failed; preserve all, stop dependent work')
            require(sha256(raw/'config.json')==attempt['protocol_sha256'],'Executed config differs from preregistration')
            audit_path=out/f'episode_{index:02d}_audit.json'
            with (out/f'episode_{index:02d}_audit.log').open('x') as log:
                result=subprocess.run([sys.executable,str(raw/'code'/'run_trace_queue_diagnostic.py'),'--audit-directory',str(raw),'--audit-output',str(audit_path)],cwd=repo,stdout=log,stderr=subprocess.STDOUT)
            require(result.returncode==0,'Frozen raw post-run audit failed; stop')
            audited=json.loads(audit_path.read_text());require(audited['common_horizon_arm']['action_arm']==c['action_arm'],'Audited arm differs')
            layout=audited['common_horizon_arm']['initial_layout_signature']
            if signature is None:signature=layout
            require(layout==signature,'Initial file row/byte distribution differs across arms; no equivalence claim')
            attempt.update(status='passed_physical_and_raw_audit_only',ended_utc=datetime.now(timezone.utc).isoformat(),raw_result_sha256=sha256(raw/'result.json'),audit_sha256=sha256(audit_path),events_sha256=audited['events_sha256'],outcomes={k:audited[k] for k in ('offered','dispatched','horizon_actual_transition_counts','final_states','boundary_observation_lateness_ms')},physical_arm=audited['common_horizon_arm'])
            checkpoint();print(json.dumps({'index':index,'arm':c['action_arm'],'status':attempt['status'],'outcomes':attempt['outcomes']}),flush=True)
        report['status']='completed_common_horizon_diagnostic_only'
        report['descriptive_arm_outcomes']={arm:[a['outcomes'] for a in report['attempts'] if a['action_arm']==arm] for arm in cfg['registered_order']}
        report['automatic_winner_selection']=False
    except Exception as e:
        report.update(status='stopped_failed_gate_preserve_all',error_type=type(e).__name__,error=str(e))
        if report['attempts'] and report['attempts'][-1]['status']=='running':report['attempts'][-1]['status']='failed_preserved'
        raise
    finally:
        report['unattempted_episodes']=len(settings)-len(report['attempts'])
        report['ended_utc']=datetime.now(timezone.utc).isoformat();checkpoint();checkpoint('result.json');lock.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--expected-revision',required=True);a=p.parse_args();run(a.config,a.expected_revision)
