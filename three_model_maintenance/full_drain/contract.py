"""Explicit inputs and boundaries for a single fixed-time, equal-work arm."""
from pathlib import Path
import re
import hashlib
import json
import subprocess
from three_model_maintenance.research.common import integer, number, require, utc, sha, read

SCHEMA = 'sf10_full_drain_fixed_rewrite_v1'
ROOT = Path(__file__).resolve().parents[2]
WORKER = Path('/mnt/nfs-storage/shashank_prafullathta/implementation')


def checked(spec):
    p = Path(spec['path']).resolve()
    require(p.is_file() and sha(p) == spec['sha256'], 'Missing/changed registered input: '+str(p))
    return p


def source_files():
    names=subprocess.check_output(['git','ls-files','--','three_model_maintenance',
        'scripts/phase6-live-evaluation'],cwd=ROOT,text=True).splitlines()
    return {n for n in names if n.endswith('.py')} | {
        'scripts/launch_sf10_full_drain.py','docs/experiment_protocols/failure_notifications.json'}


def verify_committed(protocol,cfg,head):
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==head,'Wrong intended HEAD')
    for path in (Path(protocol).resolve(),checked(cfg['study_registration'])):
        require(path.is_relative_to(ROOT),'Registration must be in repository')
        data=subprocess.check_output(['git','show',head+':'+str(path.relative_to(ROOT))],cwd=ROOT)
        require(data==path.read_bytes(),'Registration is not committed at intended HEAD')
    for name,digest in cfg['code_sha256'].items():
        data=subprocess.check_output(['git','show',head+':'+name],cwd=ROOT)
        require(hashlib.sha256(data).hexdigest()==digest==sha(ROOT/name),'Uncommitted/changed source: '+name)


def validate(cfg, *, require_study=True):
    require(cfg['schema'] == SCHEMA, 'Unknown full-drain contract')
    require(cfg['readiness'] == 'registered_for_remote_validation', 'Plan is not a physical registration')
    require(cfg['client_count'] == 1 and cfg['required_rewrites'] == 1,
            'Only serial FIFO with exactly one completed rewrite is implemented')
    require(cfg['boundary'] == 'drain_queries_and_rewrite_then_terminal_archive_v1', 'Wrong completion boundary')
    require(cfg['action_policy'] == 'fixed_time' and cfg['primary_metric'] == 'full_cohort_mean_response_seconds',
            'Initial adapter supports registered fixed timing only')
    for name in ('experiment_id','comparison_id','block_id','source_family'):
        require(type(cfg[name]) is str and re.fullmatch(r'[a-z0-9_]+',cfg[name]), 'Explicit identity required: '+name)
    require(re.fullmatch(r'local\.experiment\.full_drain_[a-z0-9_]+',cfg['destination_table']), 'Fresh isolated table name required')
    integer(cfg['horizon_ns'],'arrival horizon',1);integer(cfg['action_offset_ns'],'action offset')
    integer(cfg['latest_action_offset_ns'],'last permissible action offset')
    require(cfg['action_offset_ns'] <= cfg['latest_action_offset_ns'], 'Action outside registered start window')
    require(cfg['action_window_rationale'].strip() and cfg['parameter_rationale'].strip(), 'Missing parameter rationale')
    integer(cfg['arrival_count'],'offered count',1);integer(cfg['initial_file_count'],'initial files',2)
    require(type(cfg['expected_spark_properties']) is dict and
            {'spark.master','spark.driver.memory'}<=set(cfg['expected_spark_properties']),
            'Register actual master/memory and any additional held-fixed engine properties')
    require(cfg['expected_spark_properties']['spark.master']==cfg['expected_spark_master'],
            'Master contracts disagree')
    number(cfg['archive_interval_seconds'],'archive cadence',1)
    integer(cfg['minimum_free_bytes'],'capacity floor',1)
    integer(cfg['minimum_drain_admission_ns'],'minimum drain admission budget',1)
    for key in ('page_length','max_pages','max_requests_per_checkpoint'):
        integer(cfg['direct_archive'][key],key,1)
    require(number(cfg['direct_archive']['timeout_seconds'],'REST timeout',0)>0,'Positive timeout required')
    number(cfg['idle_poll_seconds'],'idle polling',0)
    require(cfg['idle_poll_seconds'] > 0, 'Positive polling interval required')
    require(utc(cfg['no_new_episode_after_utc']) <= utc(cfg['no_new_operation_after_utc']), 'Cutoffs reversed')
    require(utc(cfg['source_start_utc']) < utc(cfg['source_end_utc']), 'Source interval reversed')
    require((utc(cfg['source_end_utc'])-utc(cfg['source_start_utc'])).total_seconds()*1e9 == cfg['horizon_ns'], 'Source horizon differs')
    # Preserve the currently registered acquisition/freshness bounds.
    t=cfg['telemetry']
    require(t['interval_seconds']==1 and t['window_seconds']==[60,300] and t['warmup_seconds']==305
            and t['max_interval_seconds']==2 and t['max_age_seconds']==2
            and t['minimum_coverage_fraction']==0.95, 'Original telemetry gates changed')
    require(cfg['metadata_max_age_seconds']==2, 'Original action metadata freshness changed')
    require(cfg['terminal_engine_archive_contract']=='completed_calls_before_final_validation_v1'
            and cfg['telemetry_acquisition_contract']=='subprocess_counter_journal_v1'
            and cfg['telemetry_lifecycle_contract']=='workload_and_terminal_archive_then_cooperative_finish_v1',
            'Original terminal acquisition lifecycle required')
    require(cfg['three_model_capture']['admission_max_sample_age_seconds']==1, 'Original sample admission age changed')
    require(cfg['three_model_capture']['max_feature_age_ns']==2_000_000_000,
            'Original publication freshness changed')
    require(cfg['rewrite_sql_options']=={'partial-progress.enabled':'false'}, 'Unregistered rewrite options')
    require(cfg['source_role']=='engineering_development_not_confirmatory', 'First adapter is development validation only')
    require(cfg['model_training_allowed'] is False and cfg['promotion_allowed'] is False, 'No model/policy promotion in this unit')
    require(len(cfg['query_suite'])==6 and {q['query_id'] for q in cfg['query_suite']}==set(range(6)), 'Six verified SQL identities required')
    digest=lambda value: hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(cfg['query_suite_sha256']==digest(cfg['query_suite']), 'Query suite digest differs')
    observed={key:cfg[key] for key in ('telemetry','three_model_capture','archive_interval_seconds',
        'direct_archive','terminal_engine_archive_contract','telemetry_acquisition_contract',
        'telemetry_lifecycle_contract','code_sha256')}
    require(cfg['observer_contract_sha256']==digest(observed), 'Observer contract digest differs')
    if require_study:
        from .study import verify_study
        verify_study(cfg)
    return cfg


def verify_inputs(cfg):
    for spec in cfg['inputs'].values(): checked(spec)
    checked(cfg['typed_reference'])
    required=source_files()
    require(required <= set(cfg['code_sha256']), 'Incomplete runner/observer/source pin set')
    for name,digest in cfg['code_sha256'].items():
        p=ROOT/name
        require(p.resolve().is_relative_to(ROOT) and p.is_file() and sha(p)==digest, 'Changed source: '+name)
    require(read(checked(cfg['inputs']['source_capability']))['status']=='passed_saved_sf10_typed_capability_audit_only',
            'Typed SF10 source capability is not passed')
    gate=read(checked(cfg['inputs']['executed_work_gate']))
    require(gate['status']=='passed_saved_raw_executed_work_only'
            and gate['dependency_inventory_complete'] is True, 'Complete capture prerequisite not passed')
    mapping_audit=read(checked(cfg['inputs']['mapping_audit']))
    require(mapping_audit['status']=='audited_complete_real_arrival_benchmark_mapping_only'
            and mapping_audit['mapping_record_sha256']==cfg['inputs']['mapping_record']['sha256'],
            'Unaudited/changed real arrival mapping')
    # The saved diagnostic is an admission prerequisite, never physical acceptance.
