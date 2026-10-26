"""Registered serial SF10 matched collection, audited export and frozen comparison.

Fresh tables, original arrival spacing, common-horizon residual ledger. No retry,
service changes, source-table writes or prediction/calibration promotion.
"""
import argparse,ast,copy,csv,fcntl,json,os,shutil,subprocess,sys,time,traceback
from datetime import datetime,timedelta,timezone
from pathlib import Path
import urllib.request
from three_model_maintenance.contracts import require
from three_model_maintenance.training.data import read,save,sha
from three_model_maintenance.preparation.fit_registration import intervals_overlap
from three_model_maintenance.experiments.scale_query import REPO,connection
from three_model_maintenance.preparation.sf10_candidates import export
from three_model_maintenance.training.sf10_comparison import run as compare


def now():return datetime.now(timezone.utc).isoformat()


def document(cfg,title,detail):
    """Append actual stage evidence; preserve existing history and dirty files."""
    text='\n\n## '+title+' — '+now()+'\n'+detail+'\n'
    lock=(REPO/'results/.sf10_methodology_append.lock').open('a')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for name in ('methodology_working_doc.md','updated_methodology_working_doc.md'):
            with (REPO/'docs'/name).open('a') as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
        require(not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=REPO).strip(),'Existing staged files; do not commit another unit')
        paths=['docs/methodology_working_doc.md','docs/updated_methodology_working_doc.md']
        subprocess.run(['git','add','--',*paths],cwd=REPO,check=True)
        subprocess.run(['git','commit','-m',title,'--',*paths],cwd=REPO,check=True,stdout=subprocess.DEVNULL)
        pushed=subprocess.run(['git','push','origin','main'],cwd=REPO,capture_output=True,text=True)
        # Direct server credentials may be absent. Preserve its actual failure;
        # a laptop transport relay can publish this exact commit and raw mirror.
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
        sync=Path(cfg['output_directory'])/('sync_'+commit+'.json')
        save(sync,dict(commit=commit,direct_push_returncode=pushed.returncode,direct_push_stderr=pushed.stderr,
                       client_relay_required=pushed.returncode!=0,client_mirror_pending=True))
        while True:
            fetched=subprocess.run(['git','fetch','origin','main'],cwd=REPO,capture_output=True,text=True)
            ack=Path(cfg['output_directory'])/('client_sync_'+commit+'.json')
            mirrored=ack.exists() and read(ack).get('head')==commit and read(ack).get('raw_checksum_verified') is True and read(ack).get('methodology_SHA256_verified') is True
            if mirrored and fetched.returncode==0 and subprocess.run(['git','merge-base','--is-ancestor',commit,'origin/main'],cwd=REPO).returncode==0:break
            require(datetime.now(timezone.utc)<datetime.fromisoformat(cfg['no_new_episode_after_utc']),'GitHub synchronization deadline reached; no dependent work')
            time.sleep(cfg['sync_poll_seconds'])
    finally:lock.close()


def frozen(cfg):
    for s in cfg['sources']:
        p=REPO/s['path'];require(sha(p)==s['sha256'],'Changed campaign source '+s['path'])
        if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p))
    for s in cfg['inputs'].values():require(sha(Path(s['path']))==s['sha256'],'Changed source evidence '+s['path'])


def window(cfg,family):
    cohort=read(Path(cfg['inputs']['cohort']['path']));origin=datetime.fromisoformat(cohort['observation_origin_utc'])
    require(cfg['selection_rule']=='first_nonempty_start_bin_unconsumed_complete_window','Unregistered source selection')
    bins=list(csv.DictReader(Path(cfg['inputs']['bins']['path']).open()))
    registry=read(Path(cfg['inputs']['consumed_registry']['path']))
    lower=family['day_index']*86400;upper=(family['day_index']+1)*86400
    choices=[]
    for r in bins:
        offset=int(r['elapsed_seconds'])
        if not (lower<=offset and offset+cfg['horizon_seconds']<=upper and int(r['observed_arrivals'])>0):continue
        bounds={'start_utc':(origin+timedelta(seconds=offset-cfg['source_history_seconds'])).isoformat(),'end_utc':(origin+timedelta(seconds=offset+cfg['horizon_seconds'])).isoformat()}
        if not any(intervals_overlap(bounds,p) for p in registry['consumed_families']):choices.append(offset)
    require(choices,'No nonempty unconsumed starting bin in registered day')
    start=origin+timedelta(seconds=choices[0]);end=start+timedelta(seconds=cfg['horizon_seconds'])
    require(end<=datetime.fromisoformat(cohort['training_end_utc']),'Window outside original training-arrival partition')
    expanded={'start_utc':(start-timedelta(seconds=cfg['source_history_seconds'])).isoformat(),'end_utc':end.isoformat()}
    require(all(not intervals_overlap(expanded,r) for r in registry['consumed_families']),'Consumed source interval overlaps new dependency bounds')
    selected=[];total=0;previous=None;ids=set()
    with Path(cfg['inputs']['arrivals']['path']).open() as stream:
        for r in csv.DictReader(stream):
            t=datetime.fromisoformat(r['arrival_utc'].replace('Z','+00:00'));total+=1
            require(int(r['warehouseId'])==cohort['selected_warehouse_id'] and r['queryId'] not in ids and (previous is None or t>=previous),'Mixed/duplicate/unsorted source')
            ids.add(r['queryId']);previous=t
            if start<=t<end:
                delta=t-start;offset=(delta.days*86400+delta.seconds)*10**9+delta.microseconds*1000
                selected.append(dict(source_query_id=r['queryId'],warehouse_id=r['warehouseId'],source_arrival_utc=r['arrival_utc'],offset_ns=str(offset)))
    require(total==cohort['selected_total_arrivals'] and selected,'Incomplete/empty source')
    selected.sort(key=lambda r:(int(r['offset_ns']),int(r['source_query_id'])))
    for i,r in enumerate(selected):r['query_id']=str(cfg['query_suite'][i%len(cfg['query_suite'])]['query_id'])
    base=int((start-origin).total_seconds());included=[r for r in bins if base<=int(r['elapsed_seconds'])<base+cfg['horizon_seconds']]
    require(len(included)==cfg['horizon_seconds']//cohort['configuration']['bin_seconds'] and sum(int(r['observed_arrivals']) for r in included)==len(selected),'Incomplete exact source-bin coverage')
    return start,end,expanded,selected


def mapping(cfg,family,out):
    start,end,expanded,selected=window(cfg,family)
    out.mkdir(parents=True,exist_ok=False)
    with (out/'mapped_arrivals.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(selected[0]));writer.writeheader();writer.writerows(selected)
    record=dict(status='mapped_real_arrivals_no_physical_replay',source_interval_start_utc=start.isoformat(),source_interval_end_utc=end.isoformat(),horizon_ns=cfg['horizon_seconds']*10**9,
        arrival_count=len(selected),mapped_arrivals_sha256=sha(out/'mapped_arrivals.csv'),source_sha256=dict(sql_template_code=sha(REPO/'three_model_maintenance/runtime/sf10_contract.py')),
        source_family=family,expanded_interval=expanded,sql_mapping='arrival_order_round_robin_six_registered_benchmark_queries',source_inputs=cfg['inputs'])
    save(out/'mapping_record.json',record)
    # Independent reconstruction from immutable real arrivals/bins, not a generated dummy trace.
    a,b,e,actual=window(cfg,family)
    require(actual==list(csv.DictReader((out/'mapped_arrivals.csv').open())) and a==start and b==end and e==expanded,'Mapped arrival reconstruction differs')
    save(out/'mapping_audit.json',dict(status='audited_complete_real_arrival_benchmark_mapping_only',mapping_record_sha256=sha(out/'mapping_record.json'),arrival_count=len(actual),source_family=family))
    return record


def run(protocol,phase='campaign',episode_config=None):
    cfg=read(protocol);frozen(cfg)
    if phase=='episode':
        from three_model_maintenance.runtime.sf10_collect import run as collect
        collect(episode_config,subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip());return
    if phase=='export':
        item=read(Path(episode_config));export(item['directory'],item['output'],item['family'],item['role']);return
    require(cfg['schema_version']=='sf10_matched_comparison_campaign_v2','Unknown campaign registration')
    require(subprocess.check_output(['git','show','HEAD:'+str(protocol.relative_to(REPO))],cwd=REPO)==protocol.read_bytes(),'Uncommitted registration')
    root=Path(cfg['output_directory']);root.mkdir(parents=True,exist_ok=False);save(root/'registration.json',cfg)
    state=dict(status='starting',pid=os.getpid(),started_utc=now(),protocol_sha256=sha(protocol),stages=[],passed_episodes=0,failed_episodes=0,unattempted_episodes=2*len(cfg['families']),model_fit_performed=False)
    held=[];collections=[]
    def progress():
        temp=root/'progress.next.json';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'progress.json')
    def stage(label,args):
        frozen(cfg);r=dict(label=label,started_utc=now());state['stages'].append(r);progress()
        with (root/(label+'.log')).open('x') as log:
            result=subprocess.run([sys.executable,'-B',str(REPO/'scripts/phase6-live-evaluation/run_with_failure_alert.py'),'--label',cfg['label']+'_'+label,'--receipt',str(root/(label+'_failure_alert.json')),'--',*args],cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
        r.update(returncode=result.returncode,ended_utc=now());progress();require(result.returncode==0,'Failed '+label+'; preserve all attempts, no retry')
    try:
        for name in ('.three_model_collection.lock','.queue_aware_study.lock','.common_horizon_cohort.lock'):
            stream=(REPO/'results'/name).open('a');held.append(stream);fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(shutil.disk_usage(REPO).free>=cfg['minimum_data_free_bytes'] and shutil.disk_usage('/home/ccbd').free>=cfg['minimum_evidence_free_bytes'],'Insufficient retained data/evidence capacity')
        memory={s.split(':')[0]:int(s.split()[1])*1024 for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')}
        require(memory['MemAvailable']>=cfg['minimum_available_memory_bytes'],'Insufficient memory headroom')
        require(read(Path(cfg['inputs']['capability_audit']['path']))['status']=='passed_saved_sf10_typed_capability_audit_only','SF10 capability not accepted')
        for base in cfg['idle_rest_endpoints']:
            with urllib.request.urlopen(base,timeout=5) as response:require(not json.load(response),'Active Spark jobs before campaign')
        if phase=='preflight':
            # Actual-source inspection plus estimator constructor checks only; no SQL/fitting.
            from three_model_maintenance.training.sf10_comparison import estimator
            for kind,spec in cfg['comparison']['estimators'].items():estimator(kind,cfg['comparison']['feature_names'],spec)
            actual_windows=[]
            for family in cfg['families']:
                start,end,expanded,arrivals=window(cfg,family)
                actual_windows.append(dict(family=family,start_utc=start.isoformat(),end_utc=end.isoformat(),expanded_interval=expanded,arrivals=len(arrivals)))
            from three_model_maintenance.runtime.sf10_contract import canonical_result,pin_query
            cap=Path(cfg['capability_directory']);tables={r['table']:r for r in read(cap/'prepare/result.json')['tables']}
            proto=dict(cfg['episode_template'],sf10_tables=tables,query_suite=cfg['query_suite'])
            events=[json.loads(s) for s in (cap/'plan_query/events.jsonl').open()]
            requests={r['measurement_id']:r for r in events if r['kind']=='statement_requested'}
            calls={r['measurement_id']:r for r in events if r['kind']=='statement_completed'}
            refs={r['query_id']:r['canonical_rows'] for r in read(Path(cfg['inputs']['query_references']['path']))}
            observations=read(cap/'plan_query/observations.json')
            for r in observations:
                receipt=read(cap/'plan_query'/r['receipt']);mid=r['measurement_id'];qid=r['query_id']
                require(canonical_result(calls[mid]['rows'],qid,proto)==refs[qid] and requests[mid]['sql']==pin_query(proto,tables['lineitem']['iceberg_table'],qid,receipt['snapshots']['lineitem']),'New contract differs on actual saved SF10 query/result')
            save(root/'preflight_result.json',dict(status='passed_source_and_twelve_actual_SF10_contract_reconstructions_only',SQL_executed=False,model_fitted=False,actual_saved_query_checks=len(observations),actual_windows=actual_windows,protocol_sha256=sha(protocol)))
            state['status']='completed_preflight_only';return
        caproot=Path(cfg['capability_directory']);prepared=read(caproot/'prepare/result.json');maintenance=read(caproot/'plan_query/maintenance.json')
        tables={r['table']:r for r in prepared['tables']};tables['lineitem'].update(snapshot_id=maintenance['after_snapshot'],file_count=maintenance['after_files'],data_bytes=maintenance['after_bytes'])
        source=dict(status='accepted_sf10_trace_source_with_typed_capability',table=tables['lineitem']['iceberg_table'],snapshot_id=tables['lineitem']['snapshot_id'],file_count=tables['lineitem']['file_count'],record_count=tables['lineitem']['rows'],capability_audit=cfg['inputs']['capability_audit'])
        save(root/'sf10_source.json',source)
        # All intervals/roles fixed before collection, including the one-time reserved test.
        intervals=[window(cfg,f)[2] for f in cfg['families']]
        require(not any(intervals_overlap(a,b) for i,a in enumerate(intervals) for b in intervals[i+1:]),'Overlapping family dependency intervals')
        for family in cfg['families']:
            require(datetime.now(timezone.utc)<datetime.fromisoformat(cfg['no_new_episode_after_utc']),'Episode cutoff; remaining arms unattempted')
            mroot=root/('mapping_'+family['id']);mapping(cfg,family,mroot)
            matched_signature=None
            for arm in cfg['arms']:
                require(datetime.now(timezone.utc)<datetime.fromisoformat(cfg['no_new_episode_after_utc']),'No new physical episode after cutoff')
                require(shutil.disk_usage('/home/ccbd').free>=cfg['per_episode_evidence_budget_bytes'],'Evidence budget unavailable')
                eid=cfg['label']+'_'+family['id']+'_'+arm
                work=Path(cfg['working_directory'])/eid;ecfg=copy.deepcopy(cfg['episode_template'])
                ecfg.update(experiment_id=eid,output_directory=str(work),destination_table='local.experiment.integrity_horizon_'+eid,
                    action_arm=arm,action_offset_ns=None if arm=='no_maintenance' else cfg['horizon_seconds']*10**9//2,
                    metadata_checkpoint_offsets_ns=[0,cfg['horizon_seconds']*10**9//2],engine_archive_offsets_ns=[cfg['horizon_seconds']*10**9//2],
                    no_new_operation_after_utc=cfg['no_new_SQL_after_utc'],query_suite=cfg['query_suite'],sf10_tables=tables,
                    preparation_result=dict(path=str(root/'sf10_source.json'),sha256=sha(root/'sf10_source.json')),
                    typed_reference=cfg['inputs']['query_references'],mapping_record=dict(path=str(mroot/'mapping_record.json'),sha256=sha(mroot/'mapping_record.json')),
                    mapping_audit=dict(path=str(mroot/'mapping_audit.json'),sha256=sha(mroot/'mapping_audit.json')))
                target=root/(eid+'.json');save(target,ecfg)
                state['status']='collecting_'+eid;state['unattempted_episodes']-=1;progress()
                try:stage(eid,[sys.executable,'-B','-m','three_model_maintenance.experiments.sf10_campaign','--protocol',str(protocol),'--phase','episode','--episode-config',str(target)])
                except Exception:state['failed_episodes']+=1;raise
                state['passed_episodes']+=1;progress()
                archive=root/'episodes'/eid;shutil.copytree(work,archive)
                def contents(d):return {str(p.relative_to(d)):sha(p) for p in d.rglob('*') if p.is_file()}
                require(contents(work)==contents(archive),'Raw archive checksum mismatch; keep original')
                raw=[json.loads(s) for s in (archive/'events.jsonl').open()]
                initial=next(r for r in raw if r['kind']=='common_horizon_initial_state')
                inventory_call=next(r for r in raw if r['kind']=='statement_completed' and r['measurement_id']==initial['file_inventory_measurement_id'])
                signature=(initial['file_state'],sorted((r[1],r[2]) for r in inventory_call['rows']))
                if matched_signature is None:matched_signature=signature
                else:require(signature==matched_signature,'Initial physical layout differs between matched arms; no survivor comparison')
                candidate=root/'candidates'/eid;item=dict(directory=str(archive),output=str(candidate),family=family['id'],role=family['role'])
                x=root/(eid+'_export.json');save(x,item)
                stage(eid+'_export',[sys.executable,'-B','-m','three_model_maintenance.experiments.sf10_campaign','--protocol',str(protocol),'--phase','export','--episode-config',str(x)])
                collections.append(dict(directory=str(candidate),family=family['id'],role=family['role']))
                document(cfg,'SF10 matched arm and candidate audit completed '+eid,
                    'Actual physical/raw/publication/typed-plan export passed. Family '+family['id']+' role '+family['role']+'. ResultSHA '+sha(archive/'result.json')+
                    ', eventsSHA '+sha(archive/'events.jsonl')+', candidateSHA '+sha(candidate/'result.json')+'. Raw '+str(archive)+', candidate '+str(candidate)+
                    '. Original working files retained; canonical checksum matched. Actual counts '+json.dumps(read(candidate/'result.json'))+
                    '. Client raw/HEAD mirror pending next connection; worker3 commit/push attempted. No calibration/causal penalty/SF100/scheduler acceptance.')
            if family['role']=='train':
                counts={s:sum(read(Path(c['directory'])/'result.json')['eligible_counts'][s] for c in collections if c['role']=='train') for s in ('A','B')}
                save(root/'pilot_support.json',dict(actual_eligible_counts=counts,minimum_per_state=cfg['comparison']['minimum_state_rows'],statistical_sufficiency_claimed=False))
                require(min(counts.values())>=cfg['comparison']['minimum_state_rows'],'Pilot A/B support insufficient; stop dependent collection/fitting, preserve all counts')
        state.update(status='comparing_frozen_training_models',model_fit_attempted=True,model_fit_performed=None);progress()
        compare(cfg['comparison'],collections,root/'comparison');state['model_fit_performed']=True
        state['status']='completed_exploratory_sf10_collection_and_comparison_only'
        document(cfg,'SF10 shared-separate exploratory comparison completed',
            'Actual result '+str(root/'comparison/result.json')+' SHA '+sha(root/'comparison/result.json')+'. '+json.dumps(read(root/'comparison/result.json'))+
            ' All attempted and unsupported outcomes retained; no test refit/tuning/calibration/scheduler claim. Client mirror pending next connection.')
    except Exception as exc:
        state.update(status='failed_or_blocked_preserved_no_retry',error=str(exc),traceback=traceback.format_exc())
        try:document(cfg,'SF10 campaign failure or support blocker preserved',
            'Error '+str(exc)+'; passed '+str(state['passed_episodes'])+'/failed '+str(state['failed_episodes'])+'/unattempted '+str(state['unattempted_episodes'])+
            '. Progress/raw '+str(root)+'. No automatic physical retry or weakened gate. Fit attempted '+str(state.get('model_fit_attempted',False))+
            '; fit completed '+str(state['model_fit_performed'])+'. Partial artifacts retained; client mirror pending.')
        except Exception as error:state['documentation_error']=str(error)
        raise
    finally:
        state['ended_utc']=now();progress();save(root/'result.json',state)
        for stream in held:stream.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--phase',choices=('preflight','campaign','episode','export'),default='campaign');p.add_argument('--episode-config');a=p.parse_args();run(a.protocol.resolve(),a.phase,a.episode_config)
