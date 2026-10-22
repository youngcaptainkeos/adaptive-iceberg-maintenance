"""Strict candidate predictor boundaries, independent of queue-planner ownership."""
import math
import re
from datetime import datetime

QUERY_FEATURES = frozenset(('query_id','file_count','record_count','total_bytes',
    'maintenance_client_pending_at_feature_time','queue_depth_at_feature_time') +
    tuple(f'{field}_{seconds}s' for seconds in (60,300) for field in
          ('cpu_busy_fraction','memory_used_fraction','read_bytes_per_second','write_bytes_per_second')))
ROLE_UNITS = {'A':'milliseconds','B':'milliseconds','C':'offered_queries','rewrite':'milliseconds'}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def timestamp(value):
    result = datetime.fromisoformat(value)
    require(result.tzinfo is not None and result.utcoffset() is not None, 'Timezone required')
    return result

def finite(value):
    require(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value),
            'Finite numeric prediction required')
    return value

def validate_model_card(card):
    require(card['schema_version']=='three_model_candidate_card_v1','Unknown model card')
    require(card['role'] in ROLE_UNITS and card['units']==ROLE_UNITS[card['role']], 'Role/unit mismatch')
    require(card['status']=='candidate_uncalibrated' and card['scheduler_authorized'] is False,
            'This interface cannot promote a scheduler or calibrated model')
    require(card['uncertainty_status']=='not_calibrated','Calibration requires a separate reviewed contract')
    require(card['feature_names'] and len(set(card['feature_names']))==len(card['feature_names']),
            'Missing/duplicate feature contract')
    if card['role'] in ('A','B'):
        require(set(card['feature_names'])<=QUERY_FEATURES,'Unsupported or post-decision query predictor')
        require(card['condition']==('client_pending' if card['role']=='A' else 'client_not_pending'),
                'Do not relabel client pending as engine-active or causal exposure')
    if card['role']=='C':
        require(card['target_scope'] in ('aggregate_arrival_count','mapped_benchmark_query_mix'),
                'No original SQL mix or ingestion prediction without source evidence')
        require(card['horizons_seconds'] and all(isinstance(h,int) and not isinstance(h,bool) and h>0
                for h in card['horizons_seconds']), 'Registered positive forecast horizons required')
    groups=[set(card['source_families'][name]) for name in ('train','validation','calibration','test')]
    require(groups[0] and all(not(a&b) for i,a in enumerate(groups) for b in groups[i+1:]),
            'Missing training family or cross-split source-family overlap')
    require(card['evidence_sha256'] and all(re.fullmatch('[0-9a-f]{64}',h)
            for h in card['evidence_sha256'].values()), 'Evidence hashes required')
    require(re.fullmatch('[0-9a-f]{64}',card['model_artifact_sha256']), 'Bound model artifact required')
    timestamp(card['artifact_available_at_utc'])
    return card

def validate_prediction(record, card):
    """Unsupported/OOD requests return no value; never invent a fallback or interval."""
    validate_model_card(card)
    require(record['schema_version']=='three_model_prediction_v1','Unknown prediction')
    require(record['role']==card['role'] and record['units']==card['units'],'Prediction role/units differ')
    require(record['model_artifact_sha256']==card['model_artifact_sha256'],'Prediction/model artifact mismatch')
    if card['role'] in ('A','B'):
        require(record['condition']==card['condition'],'Requested observed condition differs')
    decision=timestamp(record['decision_at_utc'])
    require(timestamp(card['artifact_available_at_utc'])<=decision,'Model unavailable at decision time')
    require(record['feature_available_at_utc'] and set(record['feature_available_at_utc'])==set(card['feature_names']),
            'Every feature needs actual availability evidence')
    require(all(timestamp(t)<=decision for t in record['feature_available_at_utc'].values()),
            'Feature from future or mixed clock; source/runtime mapping must be explicit')
    require(record['support_status'] in ('supported','unsupported'),'Explicit support required')
    require(record['uncertainty_status']=='not_calibrated' and record.get('interval') is None,
            'Do not manufacture uncertainty intervals')
    if card['role']=='C':
        require(record['horizon_seconds'] in card['horizons_seconds'],'Unsupported forecast horizon')
    if record['support_status']=='unsupported':
        require(record['value'] is None and record['reasons'],'Unsupported state needs reasons and no value')
    else:
        value=finite(record['value'])
        require(value>=0 if card['role']=='C' else value>0,'Invalid nonpositive service/count prediction')
    return record
