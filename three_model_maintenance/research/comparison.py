"""Matched descriptive contrasts with explicit population and maintenance scope."""
from collections import defaultdict
from statistics import mean
from .common import require


def compare(manifest, reports):
    require(manifest['schema'] == 'research_matched_comparison_v1', 'Unknown comparison contract')
    scope = manifest['scope']
    require(scope in ('observer_engineering', 'equal_obligation_timing'), 'Unregistered objective scope')
    require(manifest['primary_metric'] == 'full_cohort_mean_response_seconds', 'Metric switching prohibited')
    expected_ids = manifest['expected_episode_ids']
    require(len(set(expected_ids)) == len(expected_ids) and set(expected_ids) == set(reports),
            'Every registered episode is required; no survivor-only comparison')
    require(manifest['family_basis'].strip() and manifest['changed_factor'].strip(), 'Missing design rationale')
    contrasts, used, component_family = [], set(), {}
    for pair in manifest['pairs']:
        b, t = reports[pair['baseline']], reports[pair['treatment']]
        require(pair['baseline'] != pair['treatment'], 'An episode cannot be its own comparison')
        require(not ({pair['baseline'], pair['treatment']} & used), 'Episode reused as independent contrast')
        used.update((pair['baseline'], pair['treatment']))
        for r in (b, t):
            require(r['status'] == 'supplementary_full_drain_accounting_only' and
                    r['offered'] == r['completed'] > 0 and r['failed'] == r['residual_queries'] == 0,
                    'Incomplete full-cohort comparison')
        for key in ('mapping_sha256', 'initial_layout_signature', 'initial_file_state',
                    'offered', 'arrival_horizon_seconds', 'source_start_utc', 'source_end_utc'):
            require(b[key] == t[key], 'Unmatched ' + key)
        family = pair['source_family']
        require(isinstance(family, str) and family, 'Missing source family')
        signature = (b['mapping_sha256'], b['source_start_utc'], b['source_end_utc'])
        require(signature not in component_family or component_family[signature] == family,
                'Identical source cannot be relabelled as independent families')
        component_family[signature] = family
        # Intersecting actual source windows cannot be separated into families.
        # This also conservatively groups same-time windows with different mappings.
        from .common import utc
        for old in contrasts:
            overlap = max(utc(b['source_start_utc']), utc(old['source_start_utc'])) < min(
                utc(b['source_end_utc']), utc(old['source_end_utc']))
            require(not overlap or family == old['source_family'], 'Overlapping windows split across families')
        if scope == 'observer_engineering':
            require(b['maintenance_count'] == t['maintenance_count'] == 0, 'Observer null study must have zero maintenance')
            require(b['initial_file_state'] == b['final_file_state'] == t['final_file_state'], 'Null layout changed')
        else:
            require(manifest['required_successful_rewrites'] == b['maintenance_count'] == t['maintenance_count'] > 0,
                    'Maintenance obligation differs; no-maintenance is diagnostic only')
            require(b['final_file_state'] == t['final_file_state'],
                    'Unequal terminal state: needs separate preregistered equivalence audit, not a silent tolerance')
        baseline, treatment = b['mean_response_seconds'], t['mean_response_seconds']
        require(baseline > 0 and treatment > 0, 'Invalid measured response')
        contrasts.append({'baseline': pair['baseline'], 'treatment': pair['treatment'],
                          'source_family': family, 'source_start_utc': b['source_start_utc'],
                          'source_end_utc': b['source_end_utc'],
                          'baseline_mean_response_seconds': baseline, 'treatment_mean_response_seconds': treatment,
                          'treatment_minus_baseline_seconds': treatment - baseline,
                          'fraction_reduction': (baseline - treatment) / baseline})
    require(used == set(expected_ids), 'Unpaired registered episodes')
    grouped = defaultdict(list)
    for row in contrasts:
        grouped[row['source_family']].append(row['treatment_minus_baseline_seconds'])
    return {'status': 'descriptive_matched_comparison_only', 'scope': scope,
            'changed_factor': manifest['changed_factor'], 'contrasts': contrasts,
            'per_family_mean_difference_seconds': {k: mean(v) for k, v in grouped.items()},
            'equal_family_mean_difference_seconds': mean(mean(v) for v in grouped.values()),
            'source_family_count': len(grouped), 'confidence_interval': None, 'p_value': None,
            'policy_benefit_established': False, 'physical_acceptance_changed': False,
            'limitations': ['Families are registered dependence groups, not proof of statistical independence.',
                           'No precision design or confirmatory interval is inferred from descriptive pairs.',
                           'Historical engineering contrasts do not establish learned scheduling benefit.']}
