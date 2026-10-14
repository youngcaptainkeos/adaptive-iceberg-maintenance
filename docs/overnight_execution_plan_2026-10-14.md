# Overnight execution queue

Authorized deadline: 2026-10-14 07:00 Asia/Kolkata. Started 00:07 IST.
Preserve machines, services, processes, tables and data. Never force cancellation,
restart or shutdown. No new physical operation after 06:15; report any operation
still running at cutoff. A same-chat 15-minute continuation is configured.

## Audit loop

Implement one bounded unit, inspect its diff, validate against real artifacts or
physical execution, fix blocking defects, then commit/push/sync/hash-verify intended
files. Preserve unrelated changes and the local-only handover archive. Do not
publish that archive without the outstanding explicit authorization.

Reorder the queue when an audit finds a dependency or failure. Never relax gates
after seeing results. Record failed/blocked/deferred work and evidence in the review.
No dummy data, fake runs, invented results or unexplained policy constants.

## Queue and gates

1. Persistent event logger: UTC and monotonic request/fetch timings, IDs, raw
   results/errors, and Spark REST evidence. Client overlap alone cannot label
   engine overlap. Maintenance results must prove useful rewritten files.
2. Independent telemetry cadence: measured counter deltas, time-weighted windows,
   coverage/gaps/freshness/warmup. No future features or zero-value failure fallback.
3. Explicit physical-correctness manifest/interface, separate from publication
   trace replay. Verify source TPC-H files, generator provenance, engine and source
   snapshot. Own uniquely named SF1 validation tables; no existing-table reset.
4. Bounded physical correctness pilot: four existing query templates, canonical
   control/concurrent result comparison, metadata/row preservation and actual
   rewrite output. Correlate SQL marker with Spark jobs/stages before overlap labels.
   Keep every raw event and table. If correlation fails, reject labels and repair.
5. Next ready work: validate Alibaba archive member schemas/times/missing values;
   review observed task-arrival mapping without claiming SQL arrivals. Independently
   verify SF100 source hashes/cardinality when it cannot interfere with a pilot.
6. Only after pilot gates: preregister bounded collection. No model training unless
   sufficient independent train/calibration/test experiment blocks exist.
7. Final audit, review and synchronization before 07:00. Include process/table state,
   failures, resource gaps, commits and next ready task. Pause continuation at cutoff.

## Approximate allocation (adaptive, not acceptance deadlines)

00:07–00:30 foundations; 00:30–02:15 logger/telemetry; 02:15–03:30 physical
correctness; 03:30–05:45 next ready validation/collection; 05:45–06:15 audit;
06:15–07:00 documentation/sync. A failed gate takes precedence over this schedule.

Legacy collector/evaluator/reset/launchers remain blocked until explicitly repaired.
No publication-readiness or forecasting claim follows from a correctness pilot.

## Current queue state (05:51 IST)

- Completed bounded event/telemetry primitives and real 60-second pre-query windows.
- Completed isolated verified SF1 source preparation and repaired query/rewrite pilot.
  Exact row multiset and query results preserved; all four queries had task overlap.
- Completed strict full Alibaba member audit and explicit container serialization review.
- Preserved positive reported task creations as a candidate only; no SQL workload mapping.
- Completed: full SF100 source hash/count agreement across both machines; actual
  60/300-second windows pass declared coverage/gap/freshness tolerances. Both source
  scans ended naturally. Fixed observer deadline drift found in the audit.
- Completed repaired observer cadence and actual client timing-boundary validation.
- Completed Snowset bytes recovery naturally: 7,823 ranges / 8,202,394,513 bytes.
  Retained parts keep the missing-original-receipt limitation. No accepted source yet.
- Corrected full Snowset validator passed: 69,182,074 unique query arrivals,
  2,051 warehouses, 2,000 regular files, gzip/tar/full values and required null gates.
  Original failed duplicate-input reader remains preserved. Accepted arrival source
  only; no SQL mapping/replay/training claim.
- Original cohort extraction failed DuckDB mixed query/filename COPY binding;
  partial raw-arrival export preserved and not accepted. Same training-only selection
  protocol retained. Repaired extraction completed naturally: 2,760,971 actual
  arrivals, 2,760,925 complete-bin arrivals plus 46 retained partial-tail arrivals.
  `datasets/snowset/arrival_cohort_export_repair_20261014/`, execution404dd8b.
  Independent Python original-time/identity/bin audit passed; package mirrored,
  all hashes equal.
- Completed raw statement/monotonic training timing binding; historical pilot
  timings remain rejected. Completed independent raw Spark task/rewrite label
  binding. Next repair: measured feature/layout and engine-session/confounder
  export binding before any training.
- Failed exact-cutoff observer preserved and mirrored; independent audit found
  counter-measurement versus history-publication ambiguity. Explicit available
  sample frontier added without changing coverage/gap/freshness gates.
- Replacement observer PID379895 ended naturally and passed exact raw-counter
  reconstruction for 60/300-second windows. Package mirrored; all hashes match.
  Cross-Python sum differences repaired with explicit ordered additions while
  retaining exact equality and unchanged coverage/gap/freshness gates.
- Next feature/layout binding contract: `physical_feature_export_contract.md`.
- Local completed-source fallback mirror finished naturally: all 8,202,394,513 bytes
  and SHA256 matched worker3. Status `verified_bytes_only`; source acceptance still
  depends on repaired full validation. No second transfer needed.
- Complete source evidence pinned/mirrored as metadata. Warehouse selection uses
  only first-week reported arrivals; next three days reserved, remaining full bins
  held out. No partial source analysis, SQL mapping or forecasting yet.
- Completed first past-only learned-count vs persistence/day/week diagnostic.
  Learned count MAE lower on this one held-out warehouse; prediction/metric audit
  passed, no forecast uncertainty/scheduling/Model C acceptance claim.
- Q1 original-snapshot matched pilot passed, original16→compacted1 file, exact
  6,001,215 rows preserved, 2.63s treatment task overlap and all windows bound.
  Four measured query records exported/mirrored; missing pre-action decision
  features remain absent and Q1 is not controller-training data.
- Q0 passed real pre-action window binding and 0.304s task exposure; physical
  rows/results preserved and raw/export packages mirrored. Older immutable inventory
  stays distinct from fresh current-state proof.
- Q2 strengthened fresh pre-action pilot passed: refreshed current snapshot/file
  inventory, actual RPC metadata freshness, raw 60/300 windows, verified task
  overlap and exact row/result conservation. Raw/export mirrored, all hashes equal.
  Four measured query rows plus one decision context; still diagnostic-only.
- Q3 passed fresh pre-action/window/task/correctness gates; PID412112 ended
  naturally. Raw/export mirrored, all hashes equal. All four query templates
  now have measured matched diagnostic episodes, distinct action-context contracts.
- Strengthened raw SQL/result/multiset/file/row exporter passed all four episodes;
  audit packages mirrored/hash-verified. Common-horizon cost protocol drafted;
  no executable replay/model acceptance. Next ready resource gap: SF100 generator provenance/relational
  integrity; next research gate: registered variance and
  common-horizon costs. Preserve no-training and cutoff gates.
- Next after this gate: broaden independent matched episodes/queries/layouts and
  training export schema; one matched point is not a variance/training corpus. Do not train cost
  models on this correctness pilot or silently use partial/cluster data as SQL demand.
- Completed collector/evaluator dead-code retirement and matched physical design.
  AutoComp attribution/reproduction claim corrected; faithful baseline still pending.
- Still blocked: publication replay/collector/evaluator, accepted independent training
  data, forecast-aware scheduling. Remaining legacy code has not been re-enabled.

- Next bounded resource unit registered: `sf100_typed_source_audit_20261014.json`
  and `scripts/audit_tpch_typed_source.py`. Real full-field source-only scans, no
  engine/table writes, exact schema/cardinality/metadata gates, no new scan after
  06:15. Completed PID416658 naturally at 06:12:53, execution82466a5. All eight
  tables passed full-field checks; offline raw audit and artifact mirror hashes
  matched. Missing
  generator and relational integrity are not supplied by typed parsing.

- Completed strict retained SF1 attempt inventory: seven packages include the
  failed correctness attempt and distinct successful contracts; zero accepted
  training episodes. `physical_attempt_inventory_reviewed_2026-10-14.json`.
  Tool published/synced; independent remote execution matched all seven raw
  episode records and audit-code hash.

- Physical cutoff passed: launch no new physical operations/scans. All own pilots
  and SF100 auditor ended naturally; preserve services/tables/data. Remaining
  queue: offline final audit, resource/claim reconciliation, handover and Git
  verification. At 07:00 IST stop work and pause heartbeat.

- Retained-table fallback copy completed and verified: seven isolated SF1 tables,
  340 files / 2,139,848,623 bytes. `results/physical_warehouse_fallback_20261014/`.
  Exact file set/size/SHA256 and source rehash matched; six successful
  current snapshots bind results, failed table preserved. Metadata paths remain worker3-specific; do not claim
  portable catalog or silently rewrite them. Artifact sync only, no new engine run.
