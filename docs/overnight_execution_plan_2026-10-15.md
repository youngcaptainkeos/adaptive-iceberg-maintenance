# Overnight learned-cost implementation queue —2026-10-15

Authorized2026-10-14 by user to work autonomously until06:00IST on2026-10-15
(2026-10-15T00:30:00Z). Existing same-chat15-minute heartbeat updated, no duplicate.
Read clock first each wake. At/after deadline stop work and pause automation;
leave all services/in-flight work running. No new physical episode after04:45IST;
no new Spark/SQL/maintenance operation after05:15IST. Reserve last45minutes for
read-only audit/mirror/documentation/sync; save morning review before06:00.

## Starting evidence

Seven successful physical arms yielded489query rows,4rewrite rows, one connected
source-time family, no fully observed300-second offered history. Candidate export
and independent raw round trip passed, not calibrated training. Prior longer
cohort remains1passed/1failed/7unattempted. Boundary preparation v1is implemented
and compilation/passed-arm regression passed; real opt-in branch still needs
registered recovery. No cost model accepted or scheduler deployed. No active
Spark/own physical run at overnight starting inspection.

## Larger job queue, with dependency gates

1. **Reliable diverse collection.** Register fresh tables and the boundary contract,
   full-window actual source arrivals and named initial layout candidates. Use
   immutable worker3 execution checkout/source so future trainer code edits cannot
   mutate active experiments. Keep six matched groups (three disjoint source-time
   windows × two initial physical file counts), all three arms per group, rotated
   order,18episodes maximum for first matrix. Original data/cases remain preserved.
   Initial layouts are controlled real repartitions of verified source rows,
   not natural ingestion or fabricated file-growth. Named16/32file candidates are
   baseline source count and two waves of existinglocal[16]parallelism, not policy
   predictions; actual row/byte layout measured and matched within each group.
2. **Demand-history exposure.** Register10-minute actual source windows:300seconds
   to expose real offered history plus300seconds to observe full-history query
   features. Count all600seconds in episode/debt outcomes; no free excluded work,
   time compression, thinning or fake warmup demand. The separate305-second host
   history warmup remains. Source-day indices0/1/2 use first nonempty complete
   windows before outcomes; one warehouse/custom SQL mix remains a limitation.
3. **Audit then export.** Every arm/raw audit passes before next; stop on failed
   gate, inspect and repair, never blind retry until desirable. Preserve failures,
   no-ops, unattempted counts and occupied tables. Re-audit matched groups; mirror
   complete raw packages/hashes, include all attempt inventories. Update candidate
   export/readiness using only successful complete packages, missing values intact.
4. **Exploratory new-schema trainer.** Implement shared and separate query latency
   estimators, per-query training-median and simple regression baselines, and a
   distinct measured rewrite-duration model. Predeclare features/parameters/seed,
   source-family/whole-episode chronological split and train-only preprocessing.
   No original query IDs/arm/outcomes/task-overlap in X. Use fully observed demand
   histories only when they exist; report excluded rows, never impute. Produce
   per-query/state/layout/episode metrics and saved actual predictions. No automatic
   winner or deployment. Mark bundle uncalibrated/diagnostic/no scheduler permission.
5. **Acceptance audit and next collection.** If data/fitting gates fail, report and
   repair or register necessary diversity, rather than inventing labels. Three
   source families are not enough for independent90%conformal calibration; refuse
   promotion. Register independent calibration/test and precision requirements
   when justified by observed evidence. Prioritize scientific blockers, not more
   identical pilots. No SF100physical run before unresolved provenance gates.
6. **Fallback and morning handover.** During no active physical query/rewrite,
   preserve needed new table bytes with unchanged-source hash checks and raw/code/
   model artifacts. Absolute metadata paths mean byte fallback is not a portable
   local catalog. Final review distinguishes done/running/failed/unvalidated,
   records hashes/log/PID/state, negative results, what to inspect next and limits.

## Dynamic audit rules

A repeated cutoff/logger/SQL/cache/schema/split issue takes priority over dependent
collection or fit. Do not weaken actual timing/freshness/row/task gates. No fabricated
CPU/intensity/small-file counts, fixed uncertainty, artificial data, counterfactual
penalty or post-hocSLA. All validation/model/physical runs on worker3 detached.
Avoid concurrent physical arms or heavy model fitting/backup during query windows.
Source/code/config must be immutable for active run. Compare layouts within named
matched groups; across groups intentionally different source/layout is metadata.

After each major job append methodology working ledger and updated-master pointer,
update this queue and overnight review. Targeted commit/push, worker3fast-forward,
HEAD/intended SHA256checks; preserve unrelated dirty/untracked archive/stashes.
Notify only meaningful completion/failure/human action and morning handover.
The local app/computer and campus/VPN connection must remain available for heartbeat
execution; detached server jobs persist across SSH disconnects. No promise of
calibration/publication just because overnight time is available.

## Dynamic priority at14:55UTC

Initial18matrix stopped0passed/1failed/17unattempted on task-retention retrieval.
Repair archive-first actual successful task-frame selection and validate raw
checkpoint/historical successful arm before fresh recovery IDs/runtime launch.
Do not upgrade failed original or use its497diagnostic rows for fitting. Trainer
implemented8de48a6, server syntax checked; actual fit still blocked by diversity.
