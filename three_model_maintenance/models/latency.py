"""Separate A/B, shared conditional, and standalone empirical candidates.

No training CLI: a future orchestrator must supply independently verified training
permission and raw-eligible rows. Old consumed history has no such permission.
"""
import math
import hashlib
import json
from collections import defaultdict
from statistics import median
from three_model_maintenance.contracts import QUERY_FEATURES, require

STATE = 'maintenance_client_pending_at_feature_time'
CELL = ('query_id', 'file_count', STATE)


def boolean(value):
    require(type(value) is bool or (isinstance(value, str) and value in ('True', 'False')), 'Missing/invalid pending state')
    return value is True or value == 'True'


def feature_vector(row, names):
    require(names and len(set(names)) == len(names) and set(names) <= QUERY_FEATURES, 'Unknown/duplicate predictors')
    result = []
    for name in names:
        require(name in row and row[name] != '', 'Missing feature ' + name)
        value = float(boolean(row[name])) if name == STATE else float(row[name])
        require(math.isfinite(value), 'Nonfinite feature ' + name)
        result.append(value)
    return result


def cell(row):
    values = feature_vector(row, CELL)
    require(values[0].is_integer() and values[1].is_integer() and values[1] > 0, 'Invalid SQL/layout identity')
    return tuple(values)


def admission(row, evidence):
    """Historical captures are not promoted by turning an eligibility flag on."""
    reasons = []
    if evidence.get('schema_version') != 'three_model_live_feature_receipt_v1':
        reasons.append('no_live_feature_publication_receipt')
    if evidence.get('measurement_id') != row.get('measurement_id'):
        reasons.append('measurement_identity_mismatch')
    if evidence.get('runtime_adapter_accepted') is not True:
        reasons.append('runtime_evidence_not_accepted')
    if evidence.get('candidate_binding_issues'):
        reasons.extend(evidence['candidate_binding_issues'])
    for seconds in (60, 300):
        if row.get(f'offered_history_complete_{seconds}s') not in (True, 'True'):
            reasons.append(f'incomplete_offered_history_{seconds}s')
    if evidence.get('schema_version') == 'three_model_live_feature_receipt_v1':
        from three_model_maintenance.runtime.publication import validate_publication
        validate_publication(evidence)
        if evidence['experiment_id'] != row.get('experiment_id'):
            reasons.append('experiment_identity_mismatch')
        published_names = tuple(evidence['feature_values'])
        require(set(published_names) <= QUERY_FEATURES, 'Publication contains an unregistered predictor')
        if feature_vector(row, published_names) != feature_vector(evidence['feature_values'], published_names):
            reasons.append('published_feature_values_differ')
    return reasons


def content_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


class LatencyCandidates:
    """No model/output substitutes another. Support requires an observed joint cell.

    Numerical box support and empirical key support are training-only. Equal
    estimator specifications are used for shared and separate candidates; total
    fitted parameter counts can differ and must be reported, not called identical.
    """
    def __init__(self, *, feature_names, estimator_spec, support_policy):
        require(STATE in feature_names and 'query_id' in feature_names and 'file_count' in feature_names,
                'Shared and separate models need the same SQL/layout/state contract')
        require(set(feature_names) <= QUERY_FEATURES and len(set(feature_names)) == len(feature_names), 'Invalid predictor contract')
        require(support_policy == 'observed_joint_cell_and_training_numeric_box', 'Explicit support policy required')
        require(estimator_spec['kind'] in ('log_ridge', 'positive_leaf_tree'), 'Unregistered estimator')
        # No implicit sklearn tuning/default budget supplied by this module.
        expected = {'kind', 'alpha', 'tol', 'max_iter'} if estimator_spec['kind'] == 'log_ridge' else {'kind', 'max_depth', 'min_samples_leaf', 'random_state'}
        require(set(estimator_spec) == expected, 'Incomplete/unregistered estimator parameters')
        if estimator_spec['kind'] == 'log_ridge':
            require(math.isfinite(estimator_spec['alpha']) and estimator_spec['alpha'] > 0 and
                    math.isfinite(estimator_spec['tol']) and estimator_spec['tol'] > 0 and
                    type(estimator_spec['max_iter']) is int and estimator_spec['max_iter'] > 0, 'Invalid ridge parameters')
        else:
            require(type(estimator_spec['max_depth']) is int and estimator_spec['max_depth'] > 0 and
                    type(estimator_spec['min_samples_leaf']) is int and estimator_spec['min_samples_leaf'] > 0 and
                    type(estimator_spec['random_state']) is int, 'Invalid tree parameters')
        self.feature_names = tuple(feature_names)
        self.spec = dict(estimator_spec)
        self.fitted = False

    def _estimator(self):
        from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
        from sklearn.pipeline import Pipeline
        import numpy as np
        query_column = self.feature_names.index('query_id')
        numeric = [i for i in range(len(self.feature_names)) if i != query_column]
        transform = ColumnTransformer([('query', OneHotEncoder(handle_unknown='error', sparse_output=False), [query_column]),
                                       ('numeric', StandardScaler(), numeric)], remainder='drop')
        if self.spec['kind'] == 'log_ridge':
            from sklearn.linear_model import Ridge
            estimator = Ridge(alpha=self.spec['alpha'], tol=self.spec['tol'], max_iter=self.spec['max_iter'], solver='svd')
            model = Pipeline([('features', transform), ('estimator', estimator)])
            return TransformedTargetRegressor(regressor=model, func=np.log, inverse_func=np.exp, check_inverse=True)
        from sklearn.tree import DecisionTreeRegressor
        estimator = DecisionTreeRegressor(criterion='squared_error', splitter='best', max_depth=self.spec['max_depth'],
                                          min_samples_leaf=self.spec['min_samples_leaf'], random_state=self.spec['random_state'])
        return Pipeline([('features', transform), ('estimator', estimator)])

    def fit(self, rows, evidence_by_id, *, authorization):
        require(not self.fitted, 'A candidate instance cannot be refitted')
        require(authorization.get('schema_version') == 'three_model_verified_fit_authorization_v1' and
                authorization.get('fit_authorized') is True and
                authorization.get('source_identity_verified') is True and
                authorization.get('raw_bounds_verified') is True and
                authorization.get('protocol_freeze_verified') is True,
                'Independent raw/source/freeze authorization required; no current inventory grants it')
        require(authorization['training_rows_sha256'] == content_sha256(rows), 'Actual training row content differs')
        evidence_content = [dict(identity=list(k), evidence=v) for k, v in sorted(evidence_by_id.items())]
        require(authorization['training_evidence_sha256'] == content_sha256(evidence_content), 'Actual training evidence differs')
        require(rows and set(authorization['training_episode_ids']) == {r['experiment_id'] for r in rows}, 'Training episode binding differs')
        require(authorization['feature_names'] == list(self.feature_names) and authorization['estimator_spec'] == self.spec,
                'Training specification differs from authorization')
        parsed = []
        ids = set()
        for row in rows:
            key = (row['experiment_id'], row['measurement_id'])
            require(key not in ids, 'Duplicate training observation')
            ids.add(key)
            require(set(self.feature_names) <= set(evidence_by_id[key].get('feature_values', {})), 'Unpublished training predictor')
            require(not admission(row, evidence_by_id[key]), 'Ineligible training evidence')
            target = float(row['service_target_ms'])
            require(math.isfinite(target) and target > 0, 'Invalid actual service label')
            parsed.append((row, feature_vector(row, self.feature_names), target))
        require({boolean(r[STATE]) for r, _, _ in parsed} == {True, False}, 'Both observed conditions required')
        models = {}; support = {}; bounds = {}
        for name, condition in [('shared', None), ('A', True), ('B', False)]:
            selected = [(r, x, y) for r, x, y in parsed if condition is None or boolean(r[STATE]) == condition]
            model = self._estimator()
            model.fit([x for _, x, _ in selected], [y for _, _, y in selected])
            models[name] = model
            support[name] = {cell(r) for r, _, _ in selected}
            bounds[name] = [(min(x[i] for _, x, _ in selected), max(x[i] for _, x, _ in selected)) for i in range(len(self.feature_names))]
        groups = {name: defaultdict(list) for name in ('query_median', 'query_layout_median', 'query_layout_state_median')}
        for row, _, target in parsed:
            q, f, s = cell(row)
            for name, key in [('query_median', (q,)), ('query_layout_median', (q, f)), ('query_layout_state_median', (q, f, s))]:
                groups[name][key].append(target)
        self.models, self.support, self.bounds = models, support, bounds
        self.medians = {name: {key: median(values) for key, values in entries.items()} for name, entries in groups.items()}
        self.fitted = True
        return self

    def predict(self, row, evidence):
        require(self.fitted, 'Candidate has no verified fitted artifacts')
        reasons = admission(row, evidence)
        if not set(self.feature_names) <= set(evidence.get('feature_values', {})):
            reasons.append('unpublished_prediction_feature')
        names = ('shared', 'separate_A_B', 'query_median', 'query_layout_median', 'query_layout_state_median')
        def unsupported(why):
            return {'support_status': 'unsupported', 'value_ms': None, 'reasons': why, 'uncertainty_status': 'not_calibrated'}
        if reasons:
            return {name: unsupported(reasons) for name in names}
        x = feature_vector(row, self.feature_names); q, f, s = key = cell(row)
        answers = {}
        for output_name, model_name in [('shared', 'shared'), ('separate_A_B', 'A' if s else 'B')]:
            if key not in self.support[model_name]:
                answers[output_name] = unsupported(['unobserved_joint_SQL_layout_state'])
            elif any(not low <= value <= high for value, (low, high) in zip(x, self.bounds[model_name])):
                answers[output_name] = unsupported(['outside_training_numeric_box'])
            else:
                value = float(self.models[model_name].predict([x])[0])
                answers[output_name] = ({'support_status': 'supported', 'value_ms': value, 'reasons': [], 'uncertainty_status': 'not_calibrated'}
                                        if math.isfinite(value) and value > 0 else unsupported(['invalid_learned_prediction']))
        for name, k in [('query_median', (q,)), ('query_layout_median', (q, f)), ('query_layout_state_median', key)]:
            answers[name] = ({'support_status': 'supported', 'value_ms': self.medians[name][k], 'reasons': [], 'uncertainty_status': 'not_calibrated'}
                             if k in self.medians[name] else unsupported(['unobserved_empirical_key']))
        return answers
