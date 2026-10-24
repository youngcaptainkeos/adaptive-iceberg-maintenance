# Queue-aware Iceberg maintenance

Research code for trace-driven maintenance timing. Start here rather than selecting an old experiment script or registration at random. Current evidence supports a working audited pipeline; it does not establish a reliable scheduler benefit or novelty.

## Folder map

```text
queue_aware_maintenance/
├── core/              Shared contracts, evidence utilities and FIFO ledger
├── models/            Empirical costs, demand forecast and simulators
├── policies/          Queue/forecast policies, ablations and fixed-time controls
├── runtime/           Physical episode/cohort runners, completion follower, admission
├── preparation/       Workload/model preparation, preflight, comparison registration
├── observability/     Telemetry publication, sampler selection and engine evidence
├── audits/            Correctness, provenance, source and implementation checks
├── analysis/          Comparisons, diagnostics and submission-overhead investigation
├── instrumentation/   Preserved measurement primitives copied from earlier work
├── protocols/         Immutable historical experiment registrations
├── docs/
│   ├── guides/        Plain-language implementation walkthrough
│   ├── plans/         Study designs and execution plans
│   ├── reviews/       Audit findings, results and feasibility limitations
│   └── operations/    Handover and explicitly historical operating instructions
├── paths.py           Central source/repository path resolution
└── layout_manifest.json  Exact old → new file mapping
```

Raw experiments remain under the repository's `results/`; source datasets remain under `datasets/`. The two append-only methodology documents remain in the repository's top-level `docs/`. They are not duplicated into this package.

## Where to start

- [Implementation explained](docs/guides/IMPLEMENTATION_WALKTHROUGH_2026-10-21.md): research question, request pipeline, files and functions. Its original filenames can be located through the map above or `layout_manifest.json`.
- [Trace/data accuracy audit](docs/reviews/TRACE_DATASET_AUDIT_2026-10-22.md): what is preserved from Snowset and what the custom TPC-H-based workload does not reproduce.
- [Repeated timing study](docs/plans/TIMING_STUDY_PLAN_2026-10-21.md): eight-arm design and its limits.
- [Operations history](docs/operations/OVERNIGHT_HANDOVER.md): past runs and frozen revisions; dated entries are historical evidence, not permission to relaunch them.
- `results/queue_aware_timing_20261021/repeated_window0/analysis/report.md`: latest completed timing-study report, relative to the repository root.

## Running code

From the repository root, both styles work:

```bash
python3 -B -m queue_aware_maintenance.runtime.run_episode --help
python3 -B queue_aware_maintenance/runtime/run_episode.py --help
```

Actual tests and jobs must run detached on worker3 through `scripts/phase6-live-evaluation/run_with_failure_alert.py`, with an explicit label, unique receipt/output/log and a registered real command. `--help` alone does not establish scientific correctness or authorize a physical experiment.

## Historical reproducibility

This organization changes source locations and imports. It does **not** modify historical protocol JSON, raw results, frozen worktrees, tables or datasets. Old commands and source hashes in historical documents remain evidence of their original revision; use that frozen revision to reproduce them. Do not rewrite an old registration to fit this tree. A future physical study requires newly reviewed code hashes, paths and proofs.

`paths.source_file()` supports explicit grouped source names and lookup of older flat names. It does not bypass hash checks or make old proofs valid for changed code. New cohort manifests record grouped relative paths and preserve the full package in evidence archives.


## Registered storage comparison — 24 October 2026

See [matched real-SQL storage plan](docs/plans/MATCHED_SQL_STORAGE_2026-10-24.md) and `protocols/matched_sql_storage_20261024.json`. It uses four full-drain null-maintenance arms with unchanged proven physical runtime and ABBA evidence-device order. Real-source preflight passed; VPN dropped before confirmed physical launch. Inspect actual remote progress before any launch. Current status and limitations remain in the two methodology documents.
