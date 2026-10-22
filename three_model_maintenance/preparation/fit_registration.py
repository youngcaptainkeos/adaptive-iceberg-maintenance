"""Candidate fit gate. Never opens model weights, fits, or supplies predictions.

Fresh registration validation is source-interval based, not caller family labels.
The inventory command only binds real, already consumed evidence. It cannot
establish prospective preregistration, independent runtime clocks or calibration.
"""
import argparse
import csv
import hashlib
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from three_model_maintenance.contracts import QUERY_FEATURES, require, timestamp


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def intervals_overlap(a, b):
    # Half-open source-clock intervals; adjacency alone does not prove independence.
    return timestamp(a['start_utc']) < timestamp(b['end_utc']) and timestamp(b['start_utc']) < timestamp(a['end_utc'])


def check_interval(item):
    require(item['source_namespace'] and item['dependence_group'], 'Missing source/dependence identity')
    require(timestamp(item['start_utc']) < timestamp(item['end_utc']), 'Empty or reversed source interval')


def consumed_dependencies(source, registry):
    check_interval(source)
    return [prior['family_id'] for prior in registry['consumed_families']
            if source['source_namespace'] == prior['source_namespace'] and
            (source['dependence_group'] == prior['dependence_group'] or intervals_overlap(source, prior))]


def validate_fit_registration(registration, registry, registry_sha256):
    """Return a candidate-only gate decision, preserving every blocking reason.

    Every source interval must include all feature lookback and target horizon.
    The caller must independently bind these bounds to raw data before training.
    A pass is a structural registration check, not authorization to fit a model.
    """
    require(registration['schema_version'] == 'three_model_fit_registration_v1', 'Unknown fit registration')
    require(registry['schema_version'] == 'three_model_consumed_registry_v1', 'Unknown registry')
    require(registration['consumed_registry_sha256'] == registry_sha256, 'Registry hash differs')
    require(registration['status'] == 'candidate_uncalibrated' and registration['scheduler_authorized'] is False,
            'Cannot promote calibration or scheduler')
    require(registration['roles'] and set(registration['roles']) == {'train', 'validation', 'calibration', 'test'}, 'All source roles required')
    require(registration['roles']['train'] and registration['roles']['validation'] and registration['roles']['test'],
            'Independent training, validation and test sources required')
    require(registration['feature_names'] and set(registration['feature_names']) <= QUERY_FEATURES and
            len(registration['feature_names']) == len(set(registration['feature_names'])), 'Invalid query predictors')
    require(registration['comparison'] == ['separate_A_B', 'shared_conditional', 'empirical_competitors'],
            'Preserve registered comparison')
    require(registration['missing_prediction_policy'] == 'unsupported_no_substitution', 'No silent fallback')
    require(registration['split_unit'] == 'whole_source_overlap_family', 'Row/random split forbidden')
    blockers = []
    selected = []
    seen = set()
    for role, sources in registration['roles'].items():
        for source in sources:
            check_interval(source)
            require(source['family_id'] not in seen, 'Duplicate source family')
            seen.add(source['family_id'])
            require(source['bounds_include_feature_history_and_target'] is True, 'Incomplete source dependency interval')
            require(source['bound_manifest_sha256'] and len(source['bound_manifest_sha256']) == 64 and
                    all(c in '0123456789abcdef' for c in source['bound_manifest_sha256']), 'Missing actual source manifest hash')
            for prior_id in consumed_dependencies(source, registry):
                blockers.append({'family_id': source['family_id'], 'role': role,
                                 'reason': 'consumed_source_dependency', 'consumed_family_id': prior_id})
            for other_role, other in selected:
                if source['source_namespace'] == other['source_namespace'] and (
                        source['dependence_group'] == other['dependence_group'] or intervals_overlap(source, other)):
                    blockers.append({'family_id': source['family_id'], 'role': role,
                                     'reason': 'cross_role_source_dependency', 'other_family_id': other['family_id'], 'other_role': other_role})
            selected.append((role, source))
    return {'status': 'blocked' if blockers else 'structural_registration_only_pending_raw_and_freeze_audit',
            'blockers': blockers, 'fit_authorized': False, 'calibration_accepted': False,
            'scheduler_authorized': False,
            'remaining_gates': ['Independently verify raw manifest and expanded source bounds, namespace and dependence identities.',
                                'Verify immutable protocol freeze before new outcome inspection and collection.',
                                'Audit real per-row availability, exclusions, features and estimator budgets.']}


def inventory(config):
    cfg = json.loads(config.read_text())
    require(cfg['schema_version'] == 'three_model_consumed_inventory_v1', 'Unknown inventory registration')
    output = (config.parent / cfg['output_directory']).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'fit_performed': False, 'test_scored': False,
              'started_utc': datetime.now(timezone.utc).isoformat()}
    try:
        paths = {}
        for key, spec in cfg['inputs'].items():
            p = (config.parent / spec['path']).resolve()
            require(sha(p) == spec['sha256'], 'Changed evidence ' + key)
            paths[key] = p
        readiness = json.loads(paths['readiness'].read_text())
        raw = json.loads(paths['raw_binding'].read_text())
        export = json.loads(paths['export'].read_text())
        test = json.loads(paths['consumed_test'].read_text())
        require(readiness['status'] == 'completed_readiness_new_independent_data_required' and
                readiness['new_fitting_authorized'] is False, 'Unknown readiness state')
        require(raw['status'] == 'completed_historical_feature_binding_no_runtime_acceptance' and
                raw['fit_performed'] is False and raw['test_scored'] is False and
                raw['runtime_adapter_accepted'] is False, 'Unknown raw binding state')
        require(test['status'] == 'completed_single_reserved_family_evaluation_uncalibrated' and
                test['test_family_evaluated'] is True, 'Missing consumed test receipt')
        episodes_path = paths['export'].parent / 'episodes.csv'
        require(sha(episodes_path) == export['artifact_sha256']['episodes.csv'], 'Episode artifact changed')
        with episodes_path.open() as stream:
            episodes = list(csv.DictReader(stream))
        require(len(episodes) == export['episodes'], 'Episode count differs')
        ids = {r['experiment_id'] for r in episodes}
        require(len(ids) == len(episodes) and ids == {r['experiment_id'] for r in raw['episodes']}, 'Raw episode binding differs')
        require(sum(r['bound_queries'] for r in raw['episodes']) == raw['bound_queries'] == export['query_rows'], 'Query binding counts differ')
        require(raw['ambiguity_count'] == len(raw['ambiguous_candidate_ids']), 'Ambiguity census differs')
        test_ids = set(test['results']['query']['test_episodes'])
        require(test_ids <= ids, 'Unknown consumed test episode')
        families = []
        assigned = set()
        for family in readiness['families']:
            interval = {'start_utc': family['source_start_utc'], 'end_utc': family['source_end_utc'],
                        'source_namespace': cfg['source_namespace'], 'dependence_group': 'historical_family_' + str(family['index'])}
            check_interval(interval)
            members = sorted(r['experiment_id'] for r in episodes
                             if timestamp(interval['start_utc']) <= timestamp(r['source_interval_start_utc']) <
                             timestamp(r['source_interval_end_utc']) <= timestamp(interval['end_utc']))
            require(members and not (assigned & set(members)), 'Empty/overlapping family assignment')
            assigned.update(members)
            families.append(dict(interval, family_id='historical_family_' + str(family['index']),
                                 experiment_ids=members, consumed=True,
                                 previous_test=bool(test_ids & set(members)),
                                 allowed_new_independent_role=None))
        require(assigned == ids and len(families) == readiness['source_family_count'], 'Incomplete family partition')
        registry = {'schema_version': 'three_model_consumed_registry_v1', 'status': 'historical_sources_consumed',
                    'source_namespace_scope': cfg['source_namespace_rationale'],
                    'evidence_sha256': {k: sha(v) for k, v in paths.items()},
                    'consumed_families': families,
                    'quarantined_measurements': raw['ambiguous_candidate_ids'],
                    'exact_runtime_availability_verified': False,
                    'limitations': ['Historical complete-window bounds only: never infer independence of a new adjacent or same-warehouse window.',
                                    'New registrations must expand intervals to include history and target, and bind any wider dependency group.',
                                    'This registry is not comprehensive for every dataset in the repository. Uninventoried sources need independent audit.']}
        (output / 'consumed_registry.json').write_text(json.dumps(registry, indent=2) + '\n')
        historical_checks = [{'family_id': f['family_id'],
                              'consumed_dependencies': consumed_dependencies(f, registry)} for f in families]
        require(all(f['family_id'] in f['consumed_dependencies'] for f in historical_checks),
                'Actual consumed history escaped dependency guard')
        report.update(historical_dependency_checks=historical_checks,
                      status='completed_consumed_inventory_not_fit_authorization', family_count=len(families),
                      episode_count=len(ids), query_count=raw['bound_queries'],
                      quarantined_measurements=raw['ambiguous_candidate_ids'],
                      registry_sha256=sha(output / 'consumed_registry.json'), fit_authorized=False,
                      historical_role_decision='All inventoried families blocked as fresh independent data.',
                      prospective_validator_validation='Source implemented; no genuine new registration exists to exercise its prospective path.')
    except Exception as exc:
        report.update(status='failed_preserved', error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        report.update(ended_utc=datetime.now(timezone.utc).isoformat(), protocol_sha256=sha(config), source_sha256=sha(Path(__file__)))
        (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    inventory(parser.parse_args().config.resolve())
