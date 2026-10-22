"""Raw reconstruction and offline admission of one named development episode."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from three_model_maintenance.contracts import require
from three_model_maintenance.models.latency import boolean, STATE, feature_vector, content_sha256, _binding_admission


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def read(path):return json.loads(Path(path).read_text())

def save(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def selected_data(cfg):
    directory=Path(cfg['candidate_directory'])
    with (directory/'queries.csv').open() as stream:rows=list(csv.DictReader(stream))
    records=[json.loads(line) for line in (directory/'publication_evidence.jsonl').open()]
    evidence={(r['experiment_id'],r['measurement_id']):r['receipt'] for r in records}
    require(len(evidence)==len(records)==len(rows),'Duplicate/missing evidence')
    selected=[];excluded=[]
    for row in rows:
        key=(row['experiment_id'],row['measurement_id']);require(key in evidence,'Unknown exported identity')
        why=_binding_admission(row,evidence[key])
        if why:
            require(all(reason.startswith('incomplete_offered_history_') for reason in why),'Invalid evidence beyond registered missing history')
            excluded.append({'experiment_id':key[0],'measurement_id':key[1],'reasons':why})
        else:
            feature_vector(row,cfg['feature_names']);selected.append(row)
    require(selected and {boolean(r[STATE]) for r in selected}=={False,True},'Both audited conditions required')
    require(len({(r['experiment_id'],r['measurement_id']) for r in rows})==len(rows),'Duplicate query rows')
    return selected,{(r['experiment_id'],r['measurement_id']):evidence[(r['experiment_id'],r['measurement_id'])] for r in selected},excluded


def verify(cfg,protocol,out):
    from three_model_maintenance.preparation.export_live_candidates import export
    from three_model_maintenance.observability.evidence_workspace import inventory
    from three_model_maintenance.preparation.fit_registration import intervals_overlap
    out.mkdir(exist_ok=False)
    for name,spec in cfg['inputs'].items():require(sha(Path(spec['path']))==spec['sha256'],'Changed registered input '+name)
    parent=read(Path(cfg['parent_directory'])/'result.json')
    raw=Path(cfg['physical_directory']);candidate=Path(cfg['candidate_directory'])
    require(parent['status']=='completed_one_real_development_measurement_only' and
            all(s['returncode']==0 for s in parent['stages']) and parent['model_fit_performed'] is False,
            'Unsuccessful or nonterminal producer')
    require(parent['physical_registration_sha256']==cfg['expected_physical_registration_sha256'] and
            parent['protocol_sha256']==cfg['expected_collection_protocol_sha256'],'Different collection identity')
    require(sha(raw/'result.json')==parent['physical_result_sha256'] and
            sha(candidate/'result.json')==parent['candidate_export_sha256'],'Changed physical/export receipt')
    archive=read(Path(cfg['parent_directory'])/'raw_archive_manifest.json')
    require(archive['status']=='verified_terminal_copy_not_scientific_acceptance' and archive['source_retained'] is True and
            sha(Path(cfg['parent_directory'])/'raw_archive_manifest.json')==parent['raw_archive_manifest_sha256'] and
            inventory(raw)==archive['files'],'Canonical physical package differs from complete manifest')
    collection=read(Path(cfg['inputs']['collection_protocol']['path']))
    mapping_cfg=read(Path(cfg['inputs']['mapping_config']['path']))
    # Verify exact real source and imposed SQL vocabulary; no consumed test reuse.
    base=Path(cfg['inputs']['mapping_config']['path']).parent
    for name in ('cohort_record','arrivals','bins','sql_template_code'):
        spec=mapping_cfg[name];require(sha((base/spec['path']).resolve())==spec['sha256'],'Changed real source '+name)
    registry=read(Path(cfg['inputs']['consumed_registry']['path']))
    interval=parent['source_registration']['expanded_interval']
    require(all(not intervals_overlap(interval,old) for old in registry['consumed_families']),'Consumed cost source overlap')
    require(parent['source_registration']['independent_test_accepted'] is False and
            cfg['source_roles']=={'train':['known_day6_engineering_development_only'],'validation':[],'calibration':[],'test':[]},
            'One known family must remain whole training only')
    require(read(raw/'mapping_record.json')['source_interval_start_utc']==cfg['source_interval_start_utc'] and
            read(raw/'mapping_record.json')['source_interval_end_utc']==cfg['source_interval_end_utc'],'Source interval changed')
    export(raw,out/'reconstructed_export')  # Full raw/publication re-audit and deterministic target/history reconstruction.
    for name in ('queries.csv','publication_evidence.jsonl'):
        require(sha(out/'reconstructed_export'/name)==sha(candidate/name),'Reconstructed training artifact differs')
    rows,evidence,excluded=selected_data(cfg)
    bindings={r['experiment_id']+'/'+r['measurement_id']:{'row_sha256':content_sha256(r),
              'evidence_sha256':content_sha256(evidence[(r['experiment_id'],r['measurement_id'])])} for r in rows}
    counts=dict(Counter('A' if boolean(r[STATE]) else 'B' for r in rows))
    receipt={'status':'verified_development_training_inputs_only','scope':'exploratory_development_only',
             'runtime_adapter_accepted':False,'scheduler_authorized':False,'calibration_accepted':False,
             'validation_or_test_scored':False,'protocol_sha256':sha(protocol),'source_interval_expanded':interval,
             'source_role':'known_day6_engineering_development_only','eligible_rows':len(rows),'condition_counts':counts,
             'excluded_rows':excluded,'eligible_row_binding':bindings,'training_rows_sha256':content_sha256(rows),
             'training_evidence_sha256':content_sha256([dict(identity=list(k),evidence=v) for k,v in sorted(evidence.items())]),
             'physical_result_sha256':sha(raw/'result.json'),'candidate_result_sha256':sha(candidate/'result.json'),
             'ended_utc':datetime.now(timezone.utc).isoformat(),
             'limitations':['One known development family, not independently held-out validation.',
                            'Offline verified data does not authorize a live runtime or scheduler.',
                            'Prior failed03 and consumed historical test sources are excluded.']}
    save(out/'result.json',receipt)
    return receipt
