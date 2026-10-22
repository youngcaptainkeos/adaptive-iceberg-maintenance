# Queue / three-model research handover — 22 October 2026

## User-directed ownership

The user explicitly split the work between two existing chats: **exploring novelty** owns the queue-aware implementation; **Main** owns restoring the three-model implementation correctly. Neither architecture is presumed superior. A later hybrid is conditional on independent predictive and physical decision evidence. The user authorized this handover to Main and asked for copyable Antigravity prompts for bounded repetitive/code-support work, rather than implicit access to Antigravity.

## Shared environment and operating rules

- Laptop repository: `/media/shashank/Data1/PDocuments/Capstone/implementation`.
- Worker3: `ccbd@10.10.3.232`; canonical repository `/mnt/nfs-storage/shashank_prafullathta/implementation`.
- Pre-handover synchronized HEAD: `86632276ba1b1a0e11f1416daf21300bf5812467`. Recheck HEAD/status before edits; both chats share the same checkout. Never reset/stash another chat's changes or stage broad unrelated edits.
- All real validation, fitting and physical work: worker3, detached nohup, explicit unique label/log/output/receipt through `scripts/phase6-live-evaluation/run_with_failure_alert.py`. Failure ntfy authorized at `https://ntfy.sh/shashank_capstone_alerts`. Inspect actual processes and resource locks before launch; old PIDs are not current-state proof.
- No killing/restarting/cancelling services/processes, deleting tables/data, dummy runs/data, synthetic demand fallback, fabricated counterfactual labels, imputation of missing evidence or weakened gates. Preserve original failures/unattempted counts and frozen worktrees. No retries selected for favorable outcomes.
- Append both `docs/methodology_working_doc.md` and `docs/updated_methodology_working_doc.md` after major units. Read both tails immediately before appending and stage exact intended paths. Targeted commit/push, canonical worker3 fast-forward and intended SHA checks. The earlier deferred-push exception concerned the completed timing study; it is not a general publication waiver.
- Queue physical studies have first claim on the existing measurement runner during registered reservations. Main must not launch competing SQL/physical collection or heavy fitting during a queue measurement. Coordinate through visible run registrations/actual locks and the user; no implicit permission for cross-chat replies is created by receiving a task message. Main can prepare source/export/model audits without physical launch.
- Keep new three-model code in a separate owned area such as `three_model_maintenance/`; queue code is read-only to Main unless an explicit integration change is agreed. Legacy data/instrumentation can be reused with provenance checks, not silently rewritten. This is a shared checkout, not isolated branches/worktrees.

## Queue implementation now

Start with `queue_aware_maintenance/README.md` and `layout_manifest.json`. Organized packages: core, models, policies, runtime, preparation, observability, audits, analysis; frozen measurement primitives in instrumentation; historical JSON registrations in protocols; guides/plans/reviews/operations under package docs. Both direct-script and `python -m` entry points are supported. The reorganization changed source hashes/imports: future physical protocols/proofs must be newly registered; old registrations reproduce from their frozen Git revisions, not current main.

The controller observes actual FIFO backlog/layout/maintenance state and past-only forecasts. Candidate start/wait/no-action decisions use empirical query/rewrite estimates and a snapshot-aware whole-call queue simulator. Queries pin a snapshot; compaction cannot retroactively accelerate a query already using the prior snapshot. New layout is available after observed completion/publication. The old fractional/fluid simulator failed its semantics audit and is retained as rejected historical evidence.

The runner uses real independently released arrival offsets, one serial foreground query client, a separate real maintenance client, full queue drain, actual SQL/result/snapshot/task/telemetry evidence, correctness checks and exact integer response-area accounting. The objective is all original scheduled-arrival-to-result responses, not only early survivors; preparation and observation delays remain included. Resource use, rewrite duration and terminal layout are separate outcomes. No arbitrary SLA/debt scalar or implied future layout benefit is invented.

## Completed evidence and negative results

1. Earliest19October cohort: 0 passed /1 failed /7 unattempted. Original repair cohort: 0 passed /1 explicitly human-authorized aborted /7 unattempted. That one scoped stop authorization does not authorize future cancellations.
2. Corrected19October snapshot/publication cohort: **7 passed /0 failed /1 unattempted**, 21,940 query executions. Missing final arm was excluded by cutoff; never relabel this as a complete eight-arm comparison. Frozen runtime `/tmp/capstone_queue_aware_20261019_snapshot_publication`, revision `d5e7c4002f49c409ae0b1e01863ceea40368d39a`. Historical source/model/observer proofs and model-only headroom diagnostics do not establish calibrated physical interference.
3.20October read-only continuation: historical-model perfect-arrival diagnostic preferred immediate compaction on both development windows, giving zero model-estimated timing headroom over immediate. This is not measured physical counterfactual proof. Queue-only/forecast-only ablations exercised recorded real states, not yet independently proven physical policies.
4. Submission-overhead probe: first attempt failed on a timing-field interface error; failure retained. Fresh repaired21October probe passed68 real queries (4 warmup/64 measured). Template-specific full-minus-minimal median overhead ~34.03/1.31/48.09/42.96ms, not pure causal observer cost because SQL calls/background sampling also vary. Minimal-mode probe data are ineligible for policy training/benefit comparison. See `queue_aware_maintenance/docs/reviews/SUBMISSION_PROBE_RESULTS_2026-10-21.md`.
5. **Complete timing experiment21–22October:8 passed /0 failed /0 unattempted;24,752 queries.** Four fixed interventions at first opportunity after0/60/600seconds or no action, each repeated in reversed order on the same known3094-arrival development window. Actual600s/60s submissions retain lateness. All physical/raw gates and terminal re-audit passed; terminal review completed22October01:13UTC. Frozen runtime `/tmp/capstone_timing_20261021_v2`, revision `790f4f89d1d8cbe821903af79392134bfb1c6bbb`; registration `queue_aware_maintenance/protocols/timing_headroom_development_deferred_push_20261021.json`, SHA `dbfab850c4eb100caff416515f58756451ebca0d574023ae96289e03c463d102`.

| Response reduction versus immediate | Repeat0 | Repeat1 |
|---|---:|---:|
|60second delay|0.4877%|0.2007%|
|600second delay|7.3710%|-0.9811%|
|No action|10.2373%|-1.3396%|

These are descriptive differences, not significance or causal benefit. Immediate mean response itself changed1346.657→1179.607seconds across repeats; sustained serial overload, time/cache drift and instrumentation complicate interpretation. No-action ends with different layout; future workloads were not observed. Only one source window/two repeats; no untouched-day/generalization/calibration/novelty acceptance. The fixed-time study did not train or compare the full queue-aware controller.

Canonical outputs: `results/queue_aware_timing_20261021/repeated_window0/analysis/report.md` and `result.json` (SHA `2502ecf5a65961700bad880d43d47677c71c41c148582fa46c53904ff2d52ba3`). Raw experiment evidence ~2.5GB on worker3; laptop bulk transfer was started but full checksum verification is not yet claimed. Inspect existing rsync before duplicating transport. Both methodology histories have been synced/pushed.

## Fresh trace / TPC-H accuracy audit

`queue_aware_maintenance/docs/reviews/TRACE_DATASET_AUDIT_2026-10-22.md`; results `results/trace_dataset_binding_20261022/audit/result.json`, SHA `b3358b7c4f652d2397f874fdbe53e81f1aa14472b12a478319ca97efbf23576b`.

- Selected-warehouse CSV2,760,971 arrivals; upstream historical archive review69,182,074 rows/2,000Parquet files. Fresh audit rechecked CSV and receipt hashes, not a new raw-archive decoding/authenticity proof.
- All3094 arrivals in27February2018 20:40:00.286–21:00:00.286UTC match source IDs, warehouse, order and unscaled offsets. Assigned template counts774/774/773/773. All24,752 actual SQL/table/snapshot/FIFO bindings match.
- Current original TPC-H SF1 `lineitem.tbl` and manifest checksums match registered ingestion:6,001,215 generated benchmark rows. Four **custom** lineitem queries, not full official TPC-H or original Snowset SQL/cost/query-type correlations. Generator provenance recorded, not rebuilt independently.
- Scheduled targets exact; observed release lateness per-run median3.389–31.960ms, p99 253.747–508.956ms, maximum1.163s. Included in response, not subtracted. Serial foreground and observer conditions limit realism.
- Package reorganization validation passed41 imports,27 entrypoints in both forms and full recorded trace binding. Results `results/queue_package_layout_20261022/validation/result.json`, SHA `d81305b7772b7dc173c807c350f9283d0108e9e2acb309d5520084f838981705`.

## Main: three-model responsibilities and first steps

Original design: A predicts query latency under observed maintenance conditions; B predicts query latency without maintenance conditional on actual layout; C forecasts offered arrivals/query mix from past-only trace observations. Rewrite duration/transition still needs a separately evidenced estimate; it may initially be empirical. A−B is not an identified causal slowdown without matched comparable states. Arrival counts are not CPU load. Missing original query mix/ingestion evidence cannot be fabricated.

Read `docs/learned_cost_model_implementation_plan.md`, `docs/publication_goals_and_execution_plan.md`, `docs/execution_review_until_1800_2026-10-17.md`, legacy trainer/exporter and actual saved fit/evaluation receipts. Audit schema/feature timing/source-family eligibility before fitting or reusing artifacts. Candidate fits are not accepted models.

Prior corpus18physical episodes/3 source families/9,923query and12rewrite labels before history eligibility filters. Family0training,1validation,2one-time reserved test. The reserved family has already been evaluated and is development history for future design. Primary query/layout median held-out equal-episode MAE20.3430ms vs tree20.9283/logRidge21.5426ms; no learned-query improvement. Only4test rewrite labels, no reliability/calibration claim. `results/consistent_cost_development_20261017` and `results/consistent_reserved_evaluation_20261017` preserve saved predictions/model bytes/audits; do not rerun the test, refit from test outcomes or silently promote old `.joblib` files.

Main should begin with a read-only model/export/readiness audit and a concrete three-model implementation/collection plan, then implement the valid candidate-schema pipeline. Compare A/B against a shared conditional estimator and strong query/layout medians under the same whole-episode/source-family splits. No missing feature imputation or unsupported intervals/calibration. Identify genuinely missing labels/features/independent blocks before requesting collection. Preserve known poor/negative performance.

## Integration contract and gates

Do not combine unvalidated components merely to claim a hybrid. Shared future interface should bind: schema/version, units (seconds versus milliseconds), query/layout and maintenance-state support, feature/forecast availability timestamps, supported horizon, source and code hashes, training/calibration/evaluation family identities and measured uncertainty status. Models predict service/rewrite/arrivals; the queue controller owns waiting/full-drain planning. No post-decision outcomes in predictors and no hidden measured counterfactuals.

Compare the same frozen predictors with (i) simple three-model cost-benefit rule and (ii) explicit queue-aware planning; then compare learned predictors versus empirical baselines with planner fixed. New independent data and preregistered physical policy comparisons are required. A hybrid is justified only if added predictors/planning improve held-out decisions or outcomes beyond run variation; otherwise retain the simpler supported approach.

Queue next gates: measurement/repeatability and credible richer workloads; real quiet/busy source selection without outcome peeking; faithful reactive/quiet-window/planning baselines; sufficient independent blocks and full-drain/debt-compatible comparisons. No new large physical campaign was launched by this handover.

## Novelty boundary

AutoComp discusses off-peak scheduling and implements periodic resource-budgeted compaction. The reviewed sections did not locate an evaluated exact arrival-forecast/backlog optimizer, but this is not proof of global absence. NoisePage/SOPHIA overlap forecasting/cost/interference/planning; PTO main paper was subsequently obtained and visually reviewed, superseding its earlier access-unknown notes. Neither three models, waiting for quiet periods nor applying generic MPC alone establishes novelty. See latest append of `docs/novelty_comparison_2026-10-17.md`; exact Iceberg-specific mechanism and independent benefit remain research hypotheses.
