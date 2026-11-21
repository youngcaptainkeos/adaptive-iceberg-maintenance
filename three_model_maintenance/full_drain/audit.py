"""Reconstruct full-drain engineering gates from raw records, not pass flags."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/phase6-live-evaluation'))
from three_model_maintenance.research.common import read,require,sha
from three_model_maintenance.research.executed_work_audit import audit as executed_audit
from three_model_maintenance.runtime.sf10_contract import references,canonical_result
from three_model_maintenance.runtime.sf10_observation import verify_observations
from three_model_maintenance.runtime.collector_bridge import audit_publications
from three_model_maintenance.runtime.terminal_archive import audit_terminal_archive
from three_model_maintenance.audits.counter_acquisition import audit as acquisition_audit
from .accounting import reconstruct
from .contract import validate,verify_inputs
from .engine_scope import audit_observed_scope


def audit_saved(directory):
    directory=Path(directory).resolve();cfg=validate(read(directory/'config.json'));verify_inputs(cfg)
    for name,digest in cfg['code_sha256'].items():require(sha(directory/'code'/name)==digest,'Frozen code copy differs')
    for name,spec in cfg['inputs'].items():require(sha(directory/'inputs'/name)==spec['sha256'],'Frozen input copy differs')
    for name in ('typed_reference','study_registration'):
        require(sha(directory/'inputs'/name)==cfg[name]['sha256'],'Frozen reference/registration differs')
    rows=[json.loads(s) for s in (directory/'events.jsonl').read_text().splitlines()]
    result=reconstruct(directory)
    expected=references(cfg)
    for event in rows:
        if event['kind']=='statement_completed' and event['role']=='trace_query':
            require(canonical_result(event['rows'],event['query_id'],cfg)==expected[str(event['query_id'])],
                    'Raw typed query result differs')
    query_windows=verify_observations(rows,cfg)
    action_windows=verify_observations(rows,cfg,kind='maintenance_decision_observation')
    terminal=audit_terminal_archive(rows,cfg)
    acquisition=acquisition_audit(directory,cfg['telemetry'],expected_until=cfg['no_new_operation_after_utc'],
        expected_journal=directory/'telemetry_acquisition.jsonl',expected_lifecycle=cfg['telemetry_lifecycle_contract'])
    publication=audit_publications(directory)
    requests={r['measurement_id']:r for r in rows if r['kind']=='statement_requested'}
    calls={r['measurement_id']:r for r in rows if r['kind']=='statement_completed'}
    states=[next(r for r in rows if r['kind']==kind) for kind in ('full_drain_initial_state','full_drain_final_state')]
    source=read(Path(cfg['inputs']['source_preparation']['path']));table=cfg['destination_table']
    checks=[r for r in rows if r['kind']=='full_drain_multiset']
    phase=next(r for r in rows if r['kind']=='telemetry_acquisition_phase_complete')
    for state in states:
        snapshot=state['snapshot_id'];check=next(r for r in checks if r['snapshot_id']==snapshot)
        actual_sql=requests[check['measurement_id']]['sql']
        expected_sql=f"SELECT count(*) FROM ((SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']} EXCEPT ALL SELECT * FROM {table} VERSION AS OF {snapshot}) UNION ALL (SELECT * FROM {table} VERSION AS OF {snapshot} EXCEPT ALL SELECT * FROM {source['table']} VERSION AS OF {source['snapshot_id']})) AS differences"
        require(actual_sql==expected_sql and calls[check['measurement_id']]['rows']==[[0]],'Actual full multiset SQL/result differs')
    require(states[0]['snapshot_id']!=states[1]['snapshot_id'],'Rewrite did not publish a new snapshot')
    require(states[0]['file_state']['record_count']==states[1]['file_state']['record_count']==source['record_count'],'Source row population differs')
    final_check=next(r for r in checks if r['snapshot_id']==states[1]['snapshot_id'])
    require(phase['recorded']['monotonic_ns']<=requests[final_check['measurement_id']]['request_start']['monotonic_ns'],
            'Final validation SQL started before cooperative observer completion')
    action=next(c for c in calls.values() if c['role']=='maintenance')
    rewrite_sql=f"CALL local.system.rewrite_data_files(table => '{table.removeprefix('local.')}', strategy => 'binpack', options => map('partial-progress.enabled','false'))"
    require(requests[action['measurement_id']]['sql']==rewrite_sql,'Rewrite target/options differ')
    require(len(action['rows'])==1 and len(action['rows'][0])>=3 and
            all(type(v) is int and v>0 for v in action['rows'][0][:3]),'No-op/invalid rewrite obligation')
    pins=read(directory/'engine_audit_inputs.json')
    require(pins['episode']==str(directory.relative_to(ROOT)) and pins['expected_completed_calls']==cfg['arrival_count'],
            'Independent engine audit population differs')
    require(pins['application_url']==cfg['spark_rest_url'].rstrip('/')+'/api/v1/applications/'+cfg['spark_app_id'],
            'Independent engine application differs')
    for name,digest in pins['inputs'].items():require(sha(ROOT/name)==digest,'Changed independent engine input')
    engine=executed_audit(pins)
    require(engine['dependency_inventory_complete'] is True,'Incomplete dependency inventory remains failed')
    scope=audit_observed_scope(directory,rows,engine,table)
    # Explicit presence gates for observed maintenance histories supplement the
    # legacy terminal audit, whose helper alone can default absent counters.
    rewrite_jobs=set()
    for event in rows:
        if event['kind']!='spark_rest' or event['resource']!='jobs':continue
        for job in event['payload']:
            description=job.get('description') or ''
            if description.startswith('Rewriting ') and description.endswith(' in '+table):
                rewrite_jobs.add(job['jobId'])
                for name in ('numFailedTasks','numKilledTasks','numFailedStages'):
                    require(type(job[name]) is int and job[name]==0,'Missing/adverse explicit rewrite job counter')
    require(rewrite_jobs,'No observed attributed rewrite jobs')
    rewrite_stages=set()
    for event in rows:
        if event['kind']=='spark_rest' and event['resource']=='jobs':
            for job in event['payload']:
                if job['jobId'] in rewrite_jobs:rewrite_stages.update(job['stageIds'])
    observed=set()
    for event in rows:
        if event['kind']=='spark_rest' and event['resource']=='stages':
            for stage in event['payload']:
                if stage['stageId'] in rewrite_stages:
                    observed.add(stage['stageId'])
                    require(type(stage['attemptId']) is int and stage['attemptId']==0,'Retried rewrite stage')
                    for name in ('numFailedTasks','numKilledTasks'):
                        require(type(stage[name]) is int and stage[name]==0,'Missing/adverse explicit rewrite stage counter')
    require(observed==rewrite_stages,'Missing rewrite dependency stage inventory')
    for name,digest in pins['inputs'].items():require(sha(ROOT/name)==digest,'Engine inputs changed while auditing')
    verify_inputs(cfg)
    return dict(response_accounting=result,engine_audit=engine,terminal_archive_audit=terminal,
                observed_engine_scope_audit=scope,
                counter_acquisition_audit=acquisition,publication_audit=publication,
                observed_query_windows=len(query_windows),observed_maintenance_windows=len(action_windows))
