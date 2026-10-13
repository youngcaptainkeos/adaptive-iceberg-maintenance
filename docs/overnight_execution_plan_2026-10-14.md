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

## Current queue state (01:45 IST)

- Completed bounded event/telemetry primitives and real 60-second pre-query windows.
- Completed isolated verified SF1 source preparation and repaired query/rewrite pilot.
  Exact row multiset and query results preserved; all four queries had task overlap.
- Completed strict full Alibaba member audit and explicit container serialization review.
- Preserved positive reported task creations as a candidate only; no SQL workload mapping.
- Completed: full SF100 source hash/count agreement across both machines; actual
  60/300-second windows pass declared coverage/gap/freshness tolerances. Both source
  scans ended naturally. Fixed observer deadline drift found in the audit.
- Completed repaired observer cadence and actual client timing-boundary validation.
- Running: provenance-checked Snowset range acquisition on worker3 after monolithic
  transfer failure. No accepted arrival dataset until full archive/schema validation.
- Next: identifiable matched collection protocol/offered-load repair; then real
  arrival inspection/forecasting when source integrity gates pass. Do not train cost
  models on this correctness pilot or silently use partial/cluster data as SQL demand.
- Still blocked: publication replay/collector/evaluator, accepted independent training
  data, forecast-aware scheduling. Remaining legacy code has not been re-enabled.
