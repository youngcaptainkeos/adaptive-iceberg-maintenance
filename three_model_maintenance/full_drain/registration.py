"""Bind real source/arrival inputs and explicit parameters; never invent them."""
import argparse
import hashlib
import json
from pathlib import Path
from three_model_maintenance.research.common import read,require,sha,write_new
from .contract import ROOT,WORKER,SCHEMA,checked,validate,verify_inputs,source_files

PARAMETERS = {
    'experiment_id','comparison_id','block_id','source_family','output_directory','destination_table',
    'action_offset_ns','latest_action_offset_ns','action_window_rationale','parameter_rationale',
    'no_new_episode_after_utc','no_new_operation_after_utc','minimum_free_bytes','minimum_drain_admission_ns',
    'initial_file_count','archive_interval_seconds','idle_poll_seconds','direct_archive',
    'expected_spark_properties',
}
INPUTS = {'source_config','source_preparation','source_capability','executed_work_gate','mapping','mapping_record','mapping_audit'}


def prepare(inputs_file,parameters_file,output,remote_ready=False,study=None):
    inputs=read(inputs_file);parameters=read(parameters_file)
    require(set(inputs)==INPUTS and set(parameters)==PARAMETERS,'Explicit complete input/parameter schema required')
    source=read(checked(inputs['source_config']));mapping=read(checked(inputs['mapping_record']))
    require(sha(checked(inputs['mapping']))==mapping['mapped_arrivals_sha256'],'Real mapping digest differs')
    cfg={key:source[key] for key in ('engine','spark_rest_url','spark_app_id','rest_timeout_seconds',
        'expected_spark_master','query_suite','sf10_tables','typed_reference','telemetry','three_model_capture',
        'metadata_max_age_seconds','decision_state_contract','terminal_engine_archive_contract',
        'telemetry_acquisition_contract','telemetry_lifecycle_contract','telemetry_persistence_contract',
        'telemetry_availability_contract')}
    cfg.update(parameters,inputs=inputs,schema=SCHEMA,readiness='prepared_not_authorized',
        client_count=1,required_rewrites=1,action_policy='fixed_time',
        boundary='drain_queries_and_rewrite_then_terminal_archive_v1',primary_metric='full_cohort_mean_response_seconds',
        horizon_ns=mapping['horizon_ns'],arrival_count=mapping['arrival_count'],
        source_start_utc=mapping['source_interval_start_utc'],source_end_utc=mapping['source_interval_end_utc'],
        source_role='engineering_development_not_confirmatory',model_training_allowed=False,promotion_allowed=False,
        rewrite_sql_options={'partial-progress.enabled':'false'})
    require(mapping['source_family']['id']==cfg['source_family'],'Source family identity differs')
    cfg['code_sha256']={name:sha(ROOT/name) for name in sorted(source_files())}
    digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    cfg['query_suite_sha256']=digest(cfg['query_suite'])
    cfg['observer_contract_sha256']=digest({key:cfg[key] for key in ('telemetry','three_model_capture',
        'archive_interval_seconds','direct_archive','terminal_engine_archive_contract',
        'telemetry_acquisition_contract','telemetry_lifecycle_contract','code_sha256')})
    cfg['study_registration']=None if study is None else dict(path=str(study.resolve()),sha256=sha(study))
    validate(dict(cfg,readiness='registered_for_remote_validation'),require_study=False)
    if remote_ready:
        require(ROOT==WORKER,'Bind launch-ready registration only after actual worker inspection')
        verify_inputs(cfg)
        cfg['readiness']='registered_for_remote_validation'
        validate(cfg)
    write_new(output,cfg)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--parameters',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--remote-ready',action='store_true')
    p.add_argument('--study',type=Path)
    a=p.parse_args();prepare(a.inputs,a.parameters,a.output,a.remote_ready,a.study)
