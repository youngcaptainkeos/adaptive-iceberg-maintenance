#!/usr/bin/env python3
"""Frozen, bounded real collection and candidate export; no automatic model fitting."""
import argparse,csv,json,os,shutil,subprocess,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
from experiment_validation import load_json,verified_file,require,sha256

def now():return datetime.now(timezone.utc).isoformat()

def run(protocol,revision):
    cfg,base=load_json(protocol);module=Path(__file__).resolve().parent;repo=module.parents[1]
    require(cfg['schema_version']=='detached_consistent_collection_v1','Unsupported collection registration')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==revision,'Runtime revision differs')
    require(datetime.now(timezone.utc)<datetime.fromisoformat(cfg['no_new_episode_after_utc']),'Registered launch cutoff passed')
    out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(protocol,out/'registration.json');code=out/'code';code.mkdir()
    hashes={p.name:sha256(p) for p in module.glob('*.py')}
    for p in module.glob('*.py'):shutil.copyfile(p,code/p.name)
    protocols=out/'protocols';protocols.mkdir()
    report={'status':'running','phase':'source_preparation','started_utc':now(),'pid':os.getpid(),
            'execution_revision':revision,'registration_sha256':sha256(protocol),'code_sha256':hashes,
            'planned_episodes':len(cfg['mapping_protocols'])*len(cfg['initial_file_counts'])*len(cfg['arms']),
            'scheduler_authorized':False,'calibrated_training_accepted':False,'automatic_model_fitting':False}
    def save():(out/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
    def child(script,args,logname):
        require(all(sha256(module/n)==h for n,h in hashes.items()),'Frozen runtime code changed')
        with (out/logname).open('x') as stream:
            result=subprocess.run([sys.executable,'-u',str(module/script),*map(str,args)],cwd=repo,stdout=stream,stderr=subprocess.STDOUT)
        return result.returncode
    def write(name,value):
        path=protocols/name
        with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
        return path
    def spec(path):return {'path':str(path.resolve()),'sha256':sha256(path)}
    def absolute_paths(value,original_base):
        if isinstance(value,dict):return {k:str((original_base/v).resolve()) if k=='path' else absolute_paths(v,original_base) for k,v in value.items()}
        if isinstance(value,list):return [absolute_paths(v,original_base) for v in value]
        return value
    save()
    try:
        template_path=verified_file(cfg['episode_template'],base);template=json.loads(template_path.read_text())
        cohort_path=verified_file(cfg['cohort_template'],base);cohort=json.loads(cohort_path.read_text())
        old_export=verified_file(cfg['previous_export_record'],base);old_manifest=json.loads(old_export.read_text())
        old_episodes=old_export.parent/'episodes.csv';require(sha256(old_episodes)==old_manifest['artifact_sha256']['episodes.csv'],'Old source inventory changed')
        with old_episodes.open() as stream:old_intervals=[(datetime.fromisoformat(r['source_interval_start_utc']),datetime.fromisoformat(r['source_interval_end_utc'])) for r in csv.DictReader(stream)]
        for historical in cfg['historical_inventories']:verified_file(historical,base)
        mappings=[];mapping_intervals=[]
        for index,item in enumerate(cfg['mapping_protocols']):
            path=verified_file(item['protocol'],base);mcfg,mbase=load_json(path)
            require(mcfg['training_day_index']==item['training_day_index'] and mcfg['window_bin_count']==cfg['window_bin_count'],'Source registration differs')
            require(child('prepare_trace_benchmark_mapping.py',['--config',path],f'mapping_{index}_prepare.log')==0,'Real source mapping failed; no physical run')
            directory=(mbase/mcfg['output_directory']).resolve();audit_path=directory/'source_mapping_audit.json'
            require(child('audit_trace_benchmark_mapping.py',['--config',path,'--mapping-directory',directory,'--output',audit_path],f'mapping_{index}_audit.log')==0,'Independent source audit failed')
            record_path=directory/'mapping_record.json';record=json.loads(record_path.read_text())
            start,end=map(datetime.fromisoformat,(record['source_interval_start_utc'],record['source_interval_end_utc']))
            require(all(not(start<b and a<end) for a,b in old_intervals+mapping_intervals),'New source overlaps previous or another registered family')
            mapping_intervals.append((start,end));mappings.append((item,spec(record_path),spec(audit_path)))
        episodes=[];order=[];group_index=0;identities=[]
        for item,mapping,mapping_audit in mappings:
            require(sorted(item['layout_order'])==sorted(cfg['initial_file_counts']),'Registered layout order differs')
            for files in item['layout_order']:
                arm_order=cfg['registered_group_orders'][group_index];group_index+=1
                require(sorted(arm_order)==sorted(cfg['arms']),'Incomplete registered matched group')
                for arm in arm_order:
                    i=len(episodes)+1;eid=f"{cfg['experiment_prefix']}_{i:02d}"
                    arm_cfg=absolute_paths(template,template_path.parent)
                    arm_cfg.update(experiment_id=eid,output_directory=str(out/'arms'/eid),
                        destination_table=f"local.experiment.{cfg['table_prefix']}_{i:02d}",
                        mapping_record=mapping,mapping_audit=mapping_audit,initial_file_count=files,
                        comparison_group=f"day_{item['training_day_index']}_files_{files}",layout_signature_group=f'initial_files_{files}',
                        action_arm=arm,action_offset_ns=None if arm=='no_maintenance' else cfg['action_offsets_ns'][arm],
                        no_new_operation_after_utc=cfg['no_new_operation_after_utc'],
                        configuration_rationale=cfg['rationale'],limitations=cfg['limitations'])
                    arm_path=write(eid+'.json',arm_cfg);episodes.append(spec(arm_path));order.append(arm)
                    identities.append({'experiment_id':eid,'table':arm_cfg['destination_table'],'source_role':item['role'],'source_day':item['training_day_index'],'files':files,'arm':arm})
        cohort.update(episodes=episodes,registered_order=order,output_directory=str(out/'cohort'),
            no_new_episode_after_utc=cfg['no_new_episode_after_utc'],rationale=cfg['rationale'],limitations=cfg['limitations'])
        cohort_protocol=write('cohort.json',cohort)
        # Registration with actual source receipts and all table identities is saved
        # before the first physical operation. No placeholder digest is accepted.
        (out/'execution_manifest.json').write_text(json.dumps({'source_mappings':[{'registration':i,'mapping':m,'audit':a} for i,m,a in mappings],
            'cohort':spec(cohort_protocol),'episodes':episodes,'identities':identities,'registered_utc':now(),'code_sha256':hashes},indent=2)+'\n')
        report.update(phase='physical_collection',cohort_protocol_sha256=sha256(cohort_protocol),identities=identities);save()
        rc=child('run_common_horizon_cohort.py',['--config',cohort_protocol,'--expected-revision',revision],'cohort_launch.log')
        result_path=out/'cohort'/'result.json';require(result_path.is_file(),'Cohort has no terminal receipt; preserve logs')
        result=json.loads(result_path.read_text());report.update(cohort_returncode=rc,cohort_status=result['status'],
            attempted_episodes=len(result['attempts']),unattempted_episodes=result['unattempted_episodes'])
        passed=[a for a in result['attempts'] if a['status']=='passed_physical_and_raw_audit_only']
        report['passed_episodes']=len(passed);report['failed_episodes']=len(result['attempts'])-len(passed);report['phase']='candidate_export';save()
        if passed and any(a['action_arm']!='no_maintenance' for a in passed):
            registered_results=[spec(out/'arms'/a['experiment_id']/'result.json') for a in passed]
            export_cfg={'schema_version':'physical_cost_candidate_export_v1','successful_arm_results':registered_results,
                'attempt_inventories':[absolute_paths(s,base) for s in cfg['historical_inventories']]+[spec(result_path)],
                'output_directory':str(out/'candidates'),'limitations':cfg['limitations']}
            export_path=write('candidate_export.json',export_cfg)
            require(child('export_physical_cost_candidates.py',['--config',export_path],'candidate_export.log')==0,'Candidate raw export failed')
            require(child('verify_physical_cost_candidates.py',['--config',export_path,'--export-directory',out/'candidates','--output',out/'candidate_independent_verification.json'],'candidate_verify.log')==0,'Independent candidate roundtrip failed')
            report['candidate_status']='raw_roundtrip_verified_only_not_model_accepted'
        else:report['candidate_status']='not_exported_no_successful_rewrite_or_query_corpus'
        report['status']='completed_candidate_collection_no_models' if rc==0 else 'stopped_failed_physical_gate_preserved_no_retry'
    except Exception as exc:
        report.update(status='failed_preserved_no_retry',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
    finally:
        report['ended_utc']=now();report['phase']='finished';save()
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        (out/'handover.md').write_text('# Detached collection handover\n\n'+report['status']+'\n\n'
            +json.dumps({k:v for k,v in report.items() if k not in ('code_sha256','identities','traceback')},indent=2)
            +'\n\nNo model was fitted/promoted. All failures and queued work retained. Review raw receipts before further work.\n')
        print(json.dumps({'status':report['status'],'output_directory':str(out)}),flush=True)
    return 0 if report['status']=='completed_candidate_collection_no_models' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--expected-revision',required=True);a=p.parse_args();sys.exit(run(a.protocol,a.expected_revision))
