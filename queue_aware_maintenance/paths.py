"""Explicit source locations; historical registered paths/hashes are not rewritten."""
from pathlib import Path
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parent
SOURCE_MODULES = {'ablation_policy': 'policies/ablation_policy.py',
 'audit_episode': 'audits/audit_episode.py',
 'audit_failed_submission_probe': 'audits/audit_failed_submission_probe.py',
 'audit_preserved_cohort': 'audits/audit_preserved_cohort.py',
 'audit_publication_sampler': 'audits/audit_publication_sampler.py',
 'audit_schedule_constraints': 'audits/audit_schedule_constraints.py',
 'audit_simulator_semantics': 'audits/audit_simulator_semantics.py',
 'audit_trace_dataset_binding': 'audits/audit_trace_dataset_binding.py',
 'common': 'core/common.py',
 'compare_study': 'analysis/compare_study.py',
 'compare_timing_study': 'analysis/compare_timing_study.py',
 'continue_research': 'analysis/continue_research.py',
 'controller_factory': 'policies/controller_factory.py',
 'costs': 'models/costs.py',
 'diagnose_completed_arm': 'analysis/diagnose_completed_arm.py',
 'engine_evidence': 'observability/engine_evidence.py',
 'fixed_start_policy': 'policies/fixed_start_policy.py',
 'follow_terminal_study': 'runtime/follow_terminal_study.py',
 'forecast': 'models/forecast.py',
 'inspect_evidence': 'analysis/inspect_evidence.py',
 'inspect_runtime_budget': 'analysis/inspect_runtime_budget.py',
 'ledger': 'core/ledger.py',
 'policy': 'policies/policy.py',
 'preflight_timing_study': 'preparation/preflight_timing_study.py',
 'prepare_and_verify': 'preparation/prepare_and_verify.py',
 'probe_submission_overhead': 'analysis/probe_submission_overhead.py',
 'publication_sampler': 'observability/publication_sampler.py',
 'register_comparison': 'preparation/register_comparison.py',
 'resource_admission': 'runtime/resource_admission.py',
 'run_episode': 'runtime/run_episode.py',
 'run_study': 'runtime/run_study.py',
 'run_timing_study': 'runtime/run_timing_study.py',
 'sampler_factory': 'observability/sampler_factory.py',
 'simulator': 'models/simulator.py',
 'snapshot_policy': 'policies/snapshot_policy.py',
 'snapshot_simulator': 'models/snapshot_simulator.py',
 'verify_controller_wiring': 'audits/verify_controller_wiring.py',
 'verify_multiset_repair': 'audits/verify_multiset_repair.py',
 'verify_publication_sampler': 'audits/verify_publication_sampler.py',
 'verify_runtime': 'audits/verify_runtime.py',
 'verify_snapshot_model': 'audits/verify_snapshot_model.py'}

def source_file(name, *, repository=None):
    """Resolve registered relative source names, including old frozen checkouts."""
    base = PACKAGE_ROOT if repository is None else Path(repository)/"queue_aware_maintenance"
    candidate = base/name
    if candidate.is_file():
        return candidate
    if name.endswith(".py") and "/" not in name and name[:-3] in SOURCE_MODULES:
        return base/SOURCE_MODULES[name[:-3]]
    return candidate


def frozen_source_hash(hashes, basename):
    """Read a unique bound source hash from flat or grouped evidence manifests."""
    matches = [value for key, value in hashes.items() if Path(key).name == basename]
    if len(matches) != 1:
        raise ValueError("Missing or ambiguous bound source: " + basename)
    return matches[0]
