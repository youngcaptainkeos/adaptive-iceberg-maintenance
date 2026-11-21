"""Freeze every intended arm before any physical result exists."""
import argparse
import hashlib
import json
from pathlib import Path
from three_model_maintenance.research.common import now,read,require,sha,utc,write_new


def configuration_digest(cfg):
    value={k:v for k,v in cfg.items() if k not in ('readiness','study_registration')}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def verify_study(cfg):
    from .contract import checked
    study=read(checked(cfg['study_registration']))
    require(study['schema']=='full_drain_fixed_timing_study_v1','Unknown prospective study')
    require(study['comparison_id']==cfg['comparison_id'] and study['block_id']==cfg['block_id'],'Study identity differs')
    arms=study['arms'];ids=[a['experiment_id'] for a in arms]
    require(len(ids)>=2 and len(ids)==len(set(ids)) and study['baseline_experiment_id'] in ids,'Invalid prospective arms')
    require(len({a['action_offset_ns'] for a in arms})>=2,'No prospective timing contrast')
    selected=[a for a in arms if a['experiment_id']==cfg['experiment_id']]
    require(len(selected)==1 and selected[0]['configuration_sha256']==configuration_digest(cfg),
            'Arm differs from the pre-execution study')
    require(utc(study['registered_utc'])<utc(cfg['no_new_episode_after_utc']),'Study registered after episode window')
    return study


def prepare(drafts_file,baseline,output):
    from .contract import checked,validate
    specs=read(drafts_file);require(type(specs) is list and len(specs)>=2,'Actual pinned draft protocols required')
    configurations=[]
    for spec in specs:
        cfg=read(checked(spec));require(cfg['readiness']=='prepared_not_authorized','Use unlaunched drafts')
        validate(dict(cfg,readiness='registered_for_remote_validation'),require_study=False)
        require(not Path(cfg['output_directory']).exists(),'Study arm already has output; no retrospective registration')
        configurations.append(cfg)
    common=None
    for cfg in configurations:
        # Only identity/table/output, action timing and its rationale may differ.
        excluded={'experiment_id','destination_table','output_directory','action_offset_ns',
                  'latest_action_offset_ns','action_window_rationale','readiness','study_registration'}
        values={k:v for k,v in cfg.items() if k not in excluded}
        if common is None:common=values
        else:require(common==values,'Unmatched prospective study configuration')
    ids=[c['experiment_id'] for c in configurations]
    require(len(set(ids))==len(ids) and baseline in ids,'Duplicate arm/missing baseline')
    require(len({c['destination_table'] for c in configurations})==len(ids)
            and len({c['output_directory'] for c in configurations})==len(ids),'Fresh arm tables/directories required')
    require(len({c['action_offset_ns'] for c in configurations})>=2,'No timing contrast')
    require(all(utc(now())<utc(c['no_new_episode_after_utc']) for c in configurations),'Expired study window')
    study=dict(schema='full_drain_fixed_timing_study_v1',registered_utc=now(),
        comparison_id=configurations[0]['comparison_id'],block_id=configurations[0]['block_id'],
        baseline_experiment_id=baseline,order_semantics='registered_serial_order_no_surviving_subsets',
        arms=[dict(experiment_id=c['experiment_id'],configuration_sha256=configuration_digest(c),
                   action_offset_ns=c['action_offset_ns']) for c in configurations],
        draft_list_sha256=sha(drafts_file),no_model_or_confirmatory_claim=True)
    write_new(output,study)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--drafts',type=Path,required=True)
    p.add_argument('--baseline',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();prepare(a.drafts,a.baseline,a.output)
