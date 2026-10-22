"""Read-only implementation checks on actual evidence; never fit consumed data.

Exercises real feature decoding, admission rejection, old-clock receipt rejection,
blocked fit entry and unsupported coverage reporting. New estimator fitting and
new journal/cursor operation remain unvalidated until a genuine registered job.
"""
import argparse
import ast
import csv
import importlib
import json
import platform
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from three_model_maintenance.contracts import require
from three_model_maintenance.models.latency import LatencyCandidates, admission, feature_vector
from three_model_maintenance.runtime.publication import clock_order, validate_publication
from three_model_maintenance.evaluation.paired import compare
from three_model_maintenance.preparation.fit_registration import sha


def run(config):
    cfg = json.loads(config.read_text())
    require(cfg['schema_version'] == 'three_model_implementation_audit_v1', 'Unknown audit registration')
    out = (config.parent / cfg['output_directory']).resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'model_fit_performed': False, 'model_inference_performed': False,
              'old_test_scored': False, 'sql_submitted': False, 'new_journal_runtime_accepted': False}
    try:
        paths = {}
        for name, spec in cfg['inputs'].items():
            path = (config.parent / spec['path']).resolve()
            require(sha(path) == spec['sha256'], 'Registered evidence changed: ' + name)
            paths[name] = path
        for spec in cfg['sources']:
            path = (config.parent / spec['path']).resolve()
            require(sha(path) == spec['sha256'], 'Registered code changed')
            ast.parse(path.read_text(), filename=str(path))
        for name in cfg['import_modules']:
            importlib.import_module(name)
        export = json.loads(paths['export'].read_text())
        raw = json.loads(paths['raw_binding'].read_text())
        inventory = json.loads(paths['consumed_inventory'].read_text())
        require(inventory['fit_authorized'] is False and inventory['status'] == 'completed_consumed_inventory_not_fit_authorization', 'Unexpected fit grant')
        require(sha(paths['bound_features']) == raw['bound_features_sha256'], 'Raw feature binding changed')
        query_path = paths['export'].parent / 'queries.csv'
        require(sha(query_path) == export['artifact_sha256']['queries.csv'], 'Query CSV changed')
        with query_path.open() as stream:
            rows = list(csv.DictReader(stream))
        with paths['bound_features'].open() as stream:
            bound_rows = [json.loads(line) for line in stream]
        evidence = {(r['experiment_id'], r['measurement_id']): r for r in bound_rows}
        require(len(evidence) == len(bound_rows) == len(rows) == export['query_rows'], 'Evidence count/identity differs')
        reasons = Counter(); unsupported = {}; legacy_rejected = 0; quarantined = []
        methods = ('shared', 'separate_A_B', 'query_median', 'query_layout_median', 'query_layout_state_median')
        for row in rows:
            key = (row['experiment_id'], row['measurement_id']); e = evidence[key]
            feature_vector(row, cfg['feature_names'])
            clock_order(e['observation_capture'], e['intent'], e['query_client_call_start'])
            why = admission(row, e)
            require('no_live_feature_publication_receipt' in why and 'runtime_evidence_not_accepted' in why, 'Historical evidence was promoted')
            reasons.update(why)
            if e['candidate_binding_issues']:
                quarantined.append({'experiment_id': key[0], 'measurement_id': key[1], 'reasons': e['candidate_binding_issues']})
            try:
                validate_publication(e)
            except ValueError:
                legacy_rejected += 1
            else:
                raise ValueError('Old historical receipt accepted as live feature publication')
            unsupported[key] = {method: {'support_status': 'unsupported', 'value_ms': None,
                                        'reasons': why, 'uncertainty_status': 'not_calibrated'} for method in methods}
        require(sorted(quarantined, key=str) == sorted(raw['ambiguous_candidate_ids'], key=str), 'Quarantine changed')
        candidates = []
        for spec in cfg['estimator_specs']:
            bundle = LatencyCandidates(feature_names=cfg['feature_names'], estimator_spec=spec,
                                       support_policy=cfg['support_policy'])
            estimator = bundle._estimator()  # Constructor only; no .fit or .predict.
            try:
                bundle.fit(rows, evidence, authorization=inventory)
            except ValueError as exc:
                require('authorization required' in str(exc), 'Blocked for unexpected reason: ' + str(exc))
            else:
                raise ValueError('Consumed inventory allowed a fit')
            require(bundle.fitted is False, 'Blocked bundle marked fitted')
            candidates.append({'specification': spec, 'constructed_type': type(estimator).__name__,
                               'consumed_fit_entry': 'rejected_before_estimator_fit'})
        coverage = compare(rows, unsupported)
        require(coverage['common_supported_rows'] == 0 and
                all(m['supported_rows'] == 0 and m['common_equal_episode_mae_ms'] is None
                    for m in coverage['methods'].values()), 'Invented score for absent predictions')
        (out / 'admission_coverage.json').write_text(json.dumps(coverage, indent=2) + '\n')
        import sklearn
        report.update(status='passed_historical_admission_and_source_checks_only', rows=len(rows),
                      historical_receipts_rejected=legacy_rejected, admission_reasons=dict(reasons),
                      quarantined_measurements=quarantined, constructed_candidates=candidates,
                      python_version=platform.python_version(), sklearn_version=sklearn.__version__,
                      admission_coverage_sha256=sha(out / 'admission_coverage.json'),
                      limitations=['No new model was fitted or evaluated; constructor checks do not validate fitted estimators.',
                                   'No physical query or new journal publication was exercised. Atomic/freshness source is opt-in and requires registered real validation.',
                                   'Coverage records are actual evidence-admission failures, not learned predictions or a model accuracy comparison.',
                                   'Independent source identity, protocol freeze, physical state validation and deployment acceptance remain absent.'])
    except Exception as exc:
        report.update(status='failed_preserved', error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        report.update(ended_utc=datetime.now(timezone.utc).isoformat(), protocol_sha256=sha(config))
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k: v for k, v in report.items() if k != 'traceback'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    run(parser.parse_args().config.resolve())
