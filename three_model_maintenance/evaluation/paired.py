"""Report all-row coverage plus common-ID equal-episode MAE without survivor concealment."""
import math
from collections import defaultdict
from three_model_maintenance.contracts import require


def compare(rows, predictions):
    require(rows and predictions, 'No actual evaluation records')
    methods = set(next(iter(predictions.values())))
    require(methods, 'No named candidate predictions')
    ids = {(r['experiment_id'], r['measurement_id']) for r in rows}
    require(len(ids) == len(rows) and ids == set(predictions), 'Missing/duplicate evaluation identities')
    require(all(set(p) == methods for p in predictions.values()), 'Comparator set differs by observation')
    common = set()
    for row in rows:
        key = (row['experiment_id'], row['measurement_id'])
        require(math.isfinite(float(row['service_target_ms'])) and float(row['service_target_ms']) > 0, 'Invalid actual target')
        supported = []
        for method in methods:
            p = predictions[key][method]
            require(p['support_status'] in ('supported', 'unsupported'), 'Unknown prediction support')
            if p['support_status'] == 'supported':
                require(math.isfinite(p['value_ms']) and p['value_ms'] > 0 and not p['reasons'], 'Invalid prediction')
                supported.append(method)
            else:
                require(p['value_ms'] is None and p['reasons'], 'Missing prediction must remain missing')
        if len(supported) == len(methods):
            common.add(key)
    output = {'offered_evaluation_rows': len(rows), 'common_supported_rows': len(common),
              'common_supported_ids': sorted(common), 'methods': {}, 'uncertainty_status': 'not_calibrated',
              'limitations': ['Common-support scores do not represent unsupported rows.',
                              'Equal-episode MAE is descriptive; no confidence interval or causal benefit inferred.']}
    for method in sorted(methods):
        supported_errors = defaultdict(list); common_errors = defaultdict(list); unsupported = []
        for row in rows:
            key = (row['experiment_id'], row['measurement_id']); p = predictions[key][method]
            if p['support_status'] != 'supported':
                unsupported.append({'experiment_id': key[0], 'measurement_id': key[1], 'reasons': p['reasons']})
                continue
            error = abs(p['value_ms'] - float(row['service_target_ms']))
            supported_errors[key[0]].append(error)
            if key in common:
                common_errors[key[0]].append(error)
        per_episode = {e: sum(v) / len(v) for e, v in common_errors.items()}
        output['methods'][method] = {'supported_rows': sum(map(len, supported_errors.values())),
                                     'unsupported_rows': unsupported, 'common_per_episode_mae_ms': per_episode,
                                     'common_equal_episode_mae_ms': sum(per_episode.values()) / len(per_episode) if per_episode else None}
    return output
