# Recovery, overhead and feasibility review — 1 November 2026

## Scope

Completed the user-authorized recovery/analysis queue without changing model/policy/collector source, scientific objectives or acceptance gates. No SQL, fitting, physical retry, service restart/cancellation or data deletion. Helper scripts and outputs are isolated diagnostic artifacts, not deployed pipeline changes. Main and exploring novelty worked in parallel; Main alone wrote shared documentation and synchronized Git.

## Actual diagnostic jobs

All ran on worker3 under nohup via scripts/phase6-live-evaluation/run_with_failure_alert.py with unique labels/logs/receipts and authorized ntfy failures. They are terminal, not currently running.

| Diagnostic | Actual PID | Output | Result SHA256 |
|---|---:|---|---|
| Saved evidence inventory |423255|results/recovery_diagnostic_20261101_01|b9f999366497cfb7cd01ab393ce66f375778c20f8b2b64da4b36de7f5f5a4478|
| Terminal-frame chronology |424291|results/recovery_terminal_frames_20261101_01|4a3485f5de17e3b344b02ab3774542a7309ebf71adc5cbfa3acee388beef78df|
| Actual-input inference and saved timer inventory |425909|results/recovery_overhead_20261101_01|99ee5c8bc7ca6c09c6af3f547e853a0351d0eba66e8c430240499396cdc540c2|

Each output directory has registration.json with script/input hashes; sibling *_launch/run.log records actual execution. diagnostic_code.py copies are mirrored beside results. Raw timing samples are timings.jsonl for the overhead unit. Server originals retained; local checksum transport verification is separate from scientific acceptance. Output values reported here are directly from terminal diagnostics, not predicted measurements.

## SF10 failure localized

Campaign02 remains **0passed/1failed/5unattempted/no fit**. It completed470client query calls, not an accepted training episode.

The gate rejected a merged job record1080 marked RUNNING. The only job snapshot containing it was26Oct16:26:47.901UTC; the query4 client fetched its result16:26:49.273UTC. The only stage2080 frame is ACTIVE; no task-list frame was archived. Final job snapshot17:09:13.876UTC includes jobIDs1100–2040 and omits1080. Two exact multiset scans occurred16:36:49–17:09:13 before that final capture. The merge correctly cannot invent a missing terminal status and retains RUNNING.

This is evidence of a terminal-capture gap; the generic 'failed/retried' message is not proof an actual Spark task failed. Exact historical retention configuration or another surviving event-log source is not established. Client completion is not a task certificate. No retrospective promotion or weaker gate was applied.

**Prospective repair to review:** archive complete final query/maintenance task evidence before expensive full-table validation and before measured retention churn can evict it. Use bounded periodic/completion checkpoints based on actual job churn and overhead. Preserve failed/retried states and independent final audits. This change is not implemented or exercised by this recovery work.

## Frozen-model overhead — measured, limited scope

Overhead unit started1Nov13:32:54UTC, ended13:33:18UTC. It used original335eligible development rows (16A/319B), frozen original logRidge and shallow-tree bundles,14features and original offline authorization. All own-development predictions reconstructed exactly against saved artifacts before timing; all inputs/model bytes remained unchanged. Runtime acceptance/calibration/scheduler flags remain false. No validation/test scoring or model selection occurred.

Registration preceded measurements:5passes in original row order, all335eligible rows,1computational thread, one disclosed genuine-first-row warmup per callable/bundle.23,450timed calls across14model/path combinations. Repeated calls are descriptive microbenchmarks, not independent research blocks or confidence intervals. One-time import/load measurements do not establish OS cold-cache performance.

| Measured path | Ridge median wall ms | Tree median wall ms |
|---|---:|---:|
| Feature-vector parsing only |0.021599|0.021720|
| Trained preprocessing transform only |0.797096|0.802840|
| Shared estimator pipeline predict, prebuilt feature vector |1.157004|1.007548|
| Conditional A/B pipeline predict, prebuilt feature vector |1.147311|1.004048|
| Core estimator only, pretransformed input |0.105508|0.137008|
| State-aware median lookup including cell parsing |0.011726|0.011941|
| Whole bound diagnostic computing shared+conditional+3medians |2.354256|2.062357|

Shared-pipeline p95wall1.293940msRidge/1.139026msTree; median processCPU1.154631ms/1.005117ms. Framework import once1.431898417swall/0.951418482sCPU. Deserialization once121.863845msRidge/54.508965msTree (already warm filesystem from hashes). Preprocessing/core/pipeline timers are nested alternatives and must not be added. CoreRidge excludes inverse-log transformation; whole-bound path evaluates multiple comparators rather than one deployed choice.

**Interpretation:** these existing small estimators predict in about1ms under this diagnostic, with appreciable preprocessing overhead relative to a dictionary median. Loading per query/decision is avoidable in a prospective persistent controller. This does not establish cost for untrained SF10boosting, feature acquisition, live runtime admission, forecasting, planning or concurrent production load. It neither proves nor disproves net learned-policy benefit.

## Saved physical timing inventory

From failedSF10raw, partial client-side wall intervals only:

| Interval | Count | Median ms | Sum seconds |
|---|---:|---:|---:|
| EXPLAIN client execute-to-fetch |12|56.569484|0.707500767|
| Query client execute-to-fetch |470|2565.544081|1181.958524607|
| Durable intent-to-execute boundary |470|2.070320|1.301564327|
| Publication capture-to-receipt-persisted-observed |470|4.940380|3.034073310|
| REST request-to-response |780|7.4222455|8.969361279|
| All metadata-labelled client statements |16|78.5868295|2032.660081703|

Metadata includes CTAS and the two expensive exact multiset validations; it is not pure metadataRPC overhead. The two multiset scans occupied approximately32.4minutes after replay and contribute to delayed final evidence capture. Plan capture is cached by exact SQL/snapshot;12EXPLAINcalls are not12perquery. Publication intervals include durable writes/scheduling and do not isolate fsyncCPU. Request-to-execute excludes earlier feature preparation; REST timers exclude parts of logging. Several timers overlap/run concurrently: no summed 'total observer overhead' is established. Six raw availability-wait events are retained in result.json rather than imputed.

No attributable controller/Spark processCPU, energy, full planner/forecast lifecycle time or deployment amortization was measured. Host counters and taskCPU do not fill those gaps; do not invent them or subtract guessed overhead from reported outcomes.

## Joint feasibility recommendation

Read-only exploring novelty review completed in chat01a15435-fab8-77c1-bed6-820b7c4f8bdd. Its confirmed queue complexity result:2passed/6188queries; response852.167scontrol vs853.313sfixed600s; one15.113srewrite and14pending observations. No demonstrated scheduling improvement. The stronger historical31.1–41.9%observer-storage result remains engineering evidence, not ML superiority.

Candidate primary objectives require prospective review: preserve full-cohort response as primary with CPU/I/O secondary, or explicitly register CPUcoreseconds as a new primary under a foreground-regression guardrail. Equal offered/completed work, maintenance obligation and final debt/layout are essential. Low CPU% alone can merely mean idle time or less work. Process/JVM totals and task breakdowns cannot be double-counted. Energy/cloud-cost/SLA conversions require actual evidence.

[Feasibility decision proposal](feasibility_decision_proposal_2026-11-01.md) specifies staged48–72h gates, strong simple comparators, invocation/observer accounting, independent source-family blocks and stop/pivot criteria. AutoComp/NoisePage/SOPHIA already overlap forecasting/resource/timing concepts. Adding CPU or plan counts alone is not a novelty claim. A viable contribution remains conditional on measured net benefit beyond cheap baselines.

## Completion audit and next gate

| Recovery objective | Evidence / outcome |
|---|---|
| Reconcile both chats and implementation plan | Read Main master/SF10plans, secondary chat turns, queue terminal receipts and SF10terminal raw; preserved conflicting histories in additive Git merge |
| Assess model overhead | Actual frozen-input worker3 diagnostic plus explicit unmeasured live components above |
| Assess defensible metrics | Parallel primary-source review and prospective metric/guardrail proposal; no objective changed |
| Coordinate parallel tasks | Secondary chat authorized/read-only review completed; Main sole execution/Git owner |
| Schedule next gated work | Existing heartbeat reactivated20min with2Nov19:00IST checkpoint; authorized ready diagnostics finished early |
| Preserve scientific boundaries | No source/model/policy change, SQL, fitting, retry, fabricated label, weakened gate or acceptance promotion |
| Preserve/document evidence | Unique registrations/results/logs, original failed counts, both methodology appends and mirrored completed diagnostics |

Ready authorized recovery work is now complete; the schedule should pause rather than launch unreviewed experiments or repeat diagnostics. The active goal's recovery/setup objective can complete after final Git/HEAD/hash and mirror verification. This is not completion of the paper, learned scheduler or scientific feasibility hypothesis.

**Next human review:** choose the prospective primary metric and practical effect/regression boundaries, then approve a fresh registered evidence-capture repair/physical feasibility block. Until then there is no authorized physical work to launch. No service is stopped by completing this queue.
