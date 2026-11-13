"""Replay new accounting against pinned genuine completed evidence, with no SQL.

This is a supplementary code regression. Historical scientific acceptance is
unchanged, and a successful regression does not accept a new physical campaign.
"""
import argparse
import ast
import traceback
from pathlib import Path
from .common import checked, now, read, require, sha, write_new
from .accounting import reconstruct
from .comparison import compare
from .design import budget, enumerate_design, overlap_families, validate_program


def run(root, registration, output):
    root, registration, output = Path(root).resolve(), Path(registration).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    cfg = read(registration)
    report = {'status': 'running', 'started_utc': now(), 'registration_sha256': sha(registration),
              'purpose': 'supplementary code regression on pinned real saved evidence',
              'new_SQL_executed': False, 'model_fit_performed': False, 'original_statuses_changed': False,
              'execution_location': cfg['execution_location'], 'checks': []}
    source = {str(p.relative_to(root)): sha(p) for p in (root / 'three_model_maintenance/research').glob('*.py')}
    write_new(output / 'registration.json', {'input_registration': cfg, 'code_sha256': source})
    try:
        require(cfg['schema'] == 'research_saved_evidence_validation_v1', 'Unknown regression registration')
        for path in source:
            ast.parse((root / path).read_text(), filename=path)
        program_path = checked(root, cfg['program'])
        program = validate_program(read(program_path))
        for name in ('null_repeatability', 'layout_curve', 'timing', 'interaction_screen', 'policy_ablation', 'uncertainty_ablation'):
            design = enumerate_design(program, name, cfg['planning_block_slots'])
            write_new(output / (name + '_PLAN_NOT_RUN.json'), design)
        try:
            enumerate_design(program, 'scope_cartesian_upper_bound', 1)
        except ValueError as exc:
            require('exceed limit' in str(exc), 'Unexpected plan-bound rejection')
        else:
            raise ValueError('Unbounded scope design was not rejected')
        report['checks'].append({'check': 'oversized_real_programme_plan_rejected_before_allocation',
                                 'meaning': 'Design guard only; no physical or simulated experiment'})
        report['checks'].append({'check': 'source_syntax_and_design_registry', 'experiments': len(program['experiments']),
                                 'meaning': 'Plan generation only; no simulated or physical observations'})
        accounting = {}
        windows = []
        for item in cfg['episodes']:
            directory = (root / item['directory']).resolve()
            require(directory.is_relative_to(root), 'Episode escapes repository')
            actual = reconstruct(directory, item['files'])
            require(actual['experiment_id'] == item['experiment_id'], 'Registered episode identity differs')
            accounting[actual['experiment_id']] = actual
            write_new(output / (actual['experiment_id'] + '_accounting.json'), actual)
            windows.append({'id': actual['experiment_id'], 'dataset_id': cfg['dataset_id'],
                            'warehouse_id': cfg['warehouse_id'], 'start_utc': actual['source_start_utc'],
                            'history_start_utc': item['history_start_utc'], 'end_utc': actual['source_end_utc']})
            print('reconstructed actual episode ' + actual['experiment_id'], flush=True)
        grouped = overlap_families(windows)
        require(len(grouped['overlap_components']) == cfg['expected_overlap_components'], 'Actual family grouping differs')
        write_new(output / 'actual_source_overlap_groups.json', grouped)
        measured_minutes = sum(r['last_query_result_after_start_seconds'] for r in accounting.values()) / len(accounting) / 60
        estimate = budget(program, 'scope_cartesian_upper_bound', 1, measured_minutes, 0)
        estimate['duration_basis'] = 'mean actual cohort-through-last-query duration of four pinned historical episodes'
        estimate['setup_assumption'] = 'zero counted: setup, maintenance, auditing and recovery are unmeasured here; this is an illustrative lower accounting boundary, not an SF10 forecast'
        write_new(output / 'scope_budget_illustration_NOT_A_CAMPAIGN.json', estimate)
        comparison = compare(cfg['comparison'], accounting)
        previous = read(checked(root, cfg['historical_comparison']))
        expected = {(p['evidence_disk'], p['system_disk']): p['fraction_lower_total_response'] for p in previous['contrasts']}
        for contrast in comparison['contrasts']:
            value = expected[(contrast['baseline'], contrast['treatment'])]
            require(abs(contrast['fraction_reduction'] - value) <= cfg['floating_absolute_tolerance'],
                    'Historical engineering contrast differs')
        write_new(output / 'historical_comparison_reconstruction.json', comparison)
        failure = read(checked(root, cfg['failed_campaign']))
        require(failure['passed_episodes'] == 0 and failure['failed_episodes'] == 1 and
                failure['unattempted_episodes'] == 1 and failure['model_fit_performed'] is False,
                'Historical failure evidence changed')
        report['checks'].append({'check': 'actual_raw_full_drain_accounting', 'episodes': len(accounting),
                                 'query_rows': sum(r['completed'] for r in accounting.values()),
                                 'exact_integer_response_and_area_reconstruction': True})
        report['checks'].append({'check': 'historical_matched_engineering_contrasts', 'pairs': len(comparison['contrasts']),
                                 'overlap_components': len(grouped['overlap_components']),
                                 'policy_benefit_established': False})
        report['checks'].append({'check': 'preserved_failed_campaign', 'passed': 0, 'failed': 1, 'unattempted': 1})
        require(all(sha(root / p) == h for p, h in source.items()), 'Code changed while regression ran')
        require(sha(registration) == report['registration_sha256'] and sha(program_path) == cfg['program']['sha256'],
                'Registration/program changed while regression ran')
        report.update(status='passed_supplementary_saved_evidence_regression_only',
                      limitations=['No new physical experiment, model fit, attribution repair acceptance or scheduler validation.',
                                   'Source-family independence is not established; four historical runs share one overlap component.',
                                   'The new exact SQL binding function is syntax-reviewed only here: its original SQL inventory is not mirrored locally.',
                                   'Concurrency, prospective physical launch, CPU/I/O reconstruction and confirmatory inference remain future implementation.'])
    except Exception as exc:
        report.update(status='failed_preserved', error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        report['ended_utc'] = now()
        write_new(output / 'result.json', report)
        print(report['status'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository', type=Path, required=True)
    p.add_argument('--registration', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run(a.repository, a.registration, a.output)
