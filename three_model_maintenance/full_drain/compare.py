"""Compare every preregistered timing arm; never select surviving arms."""
import argparse
from pathlib import Path
from three_model_maintenance.research.common import decode,read,require,sha,utc,write_new
from .audit import audit_saved
from .contract import ROOT,WORKER,checked
from .study import verify_study


def compare(manifest,output):
    require(ROOT==WORKER,'Scientific comparison only in worker3 checkout through detached failure wrapper')
    registration=read(manifest)
    require(registration['schema']=='full_drain_fixed_timing_comparison_v1','Wrong comparison registration')
    arms=registration['arms'];require(len(arms)>=2 and len({a['experiment_id'] for a in arms})==len(arms),'Missing/duplicate arms')
    study=read(checked(registration['study_registration']))
    require(study['schema']=='full_drain_fixed_timing_study_v1','Missing prospective study')
    require([a['experiment_id'] for a in arms]==[a['experiment_id'] for a in study['arms']],
            'Cannot omit failed/unattempted arms or change registered order')
    require(all(registration[k]==study[k] for k in ('comparison_id','block_id','baseline_experiment_id')),
            'Retrospective comparison identity/baseline differs')
    require(len({a['action_offset_ns'] for a in arms})>=2,'Timing contrast needs different start times')
    reports=[];signature=None;previous_acceptance=None
    for arm in arms:
        directory=Path(arm['directory']);accept=read(directory/'acceptance.json')
        require(accept['status']=='passed_full_drain_engineering_checks_only','Arm lacks all engineering checks')
        require(sha(directory/'result.json')==accept['result_sha256'] and sha(directory/'acceptance.json')==arm['acceptance_sha256'],'Result/acceptance changed')
        require(sha(directory/'engine_audit_inputs.json')==accept['engine_audit_inputs_sha256'],'Engine audit registration changed')
        result=read(directory/'result.json');proofs=audit_saved(directory);raw=proofs['response_accounting']
        events=[decode(line) for line in (directory/'events.jsonl').read_text().splitlines()]
        started=next(r['recorded']['utc'] for r in events if r['kind']=='full_drain_protocol')
        require(previous_acceptance is None or utc(previous_acceptance)<utc(started),'Arms did not run in registered serial order')
        require(utc(started)<utc(accept['completed_utc']),'Acceptance preceded episode')
        require(all(accept[k]==proofs[k] for k in proofs if k!='response_accounting'),'Saved engineering proof differs from raw replay')
        require(all(result[k]==v for k,v in raw.items() if k!='status'),'Independent accounting differs')
        require(result['experiment_id']==arm['experiment_id'],'Arm identity differs')
        cfg=read(directory/'config.json');require(sha(directory/'config.json')==arm['protocol_sha256'],'Changed registered protocol')
        child_path=ROOT/'results'/(cfg['experiment_id']+'_launch')/'child_result.json'
        child=read(child_path)
        require(sha(child_path)==arm['terminal_receipt_sha256'] and child['status']=='child_exited'
                and type(child['exit_code']) is int and child['exit_code']==0
                and type(child['pid']) is int and child['pid']>0,'Missing/failed actual terminal child receipt')
        require(child['label']==cfg['experiment_id'] and child['protocol_sha256']==arm['protocol_sha256']
                and child['acceptance_sha256']==arm['acceptance_sha256']
                and child['result_sha256']==accept['result_sha256']
                and child['code_revision']==accept['code_revision']==result['code_revision'],
                'Terminal child/evidence provenance differs')
        require(utc(accept['completed_utc'])<=utc(child['ended_utc']),'Child completed before acceptance')
        previous_acceptance=child['ended_utc']
        require(cfg['study_registration']==registration['study_registration'] and verify_study(cfg)==study,
                'Arm bound to another prospective study')
        require(cfg['action_offset_ns']==arm['action_offset_ns'],'Wrong timing intervention')
        require(result['completed_rewrites']==1 and result['unfinished']==result['failed']==0,'Unequal/incomplete work')
        require(not (directory/'failure.json').exists(),'Failed arm cannot enter comparison')
        require(accept['engine_audit']['dependency_inventory_complete'] is True,'Incomplete engine evidence')
        current={k:result[k] for k in ('comparison_id','block_id','source_family','mapping_sha256',
            'initial_layout_signature','initial_file_state','query_suite_sha256','observer_contract_sha256',
            'required_rewrites','rewrite_options','source_preparation_sha256','source_config_sha256')}
        if signature is None:signature=current
        else:require(current==signature,'Unmatched input/layout/observer/work obligation')
        require(result['comparison_id']==registration['comparison_id'] and result['block_id']==registration['block_id'],'Wrong comparison block')
        reports.append(dict(experiment_id=result['experiment_id'],action_offset_ns=cfg['action_offset_ns'],
            mean_response_seconds=result['mean_response_seconds'],actual_action_start_seconds=result['actual_action_start_seconds'],
            post_arrival_work_drain_seconds=result['post_arrival_work_drain_seconds'],final_file_state=result['final_file_state']))
    baseline=next(r for r in reports if r['experiment_id']==registration['baseline_experiment_id'])
    require(baseline['mean_response_seconds']>0,'Invalid baseline response')
    result=dict(status='complete_matched_development_timing_comparison_only',manifest_sha256=sha(manifest),
        reports=reports,contrasts=[dict(experiment_id=r['experiment_id'],
            response_difference_seconds=r['mean_response_seconds']-baseline['mean_response_seconds'],
            fraction_lower_response=1-r['mean_response_seconds']/baseline['mean_response_seconds']) for r in reports],
        independent_generalization_established=False,model_accepted=False,
        limitations=['One matched development block is not a population effect or confidence interval.',
                     'Final measured layouts are reported; equal successful rewrite obligation is not identical future read performance.',
                     'No resource reduction claim; resource fields require separate attributable coverage.'])
    write_new(output,result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();compare(a.manifest,a.output)
