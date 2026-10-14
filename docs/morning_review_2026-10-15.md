# Morning handover — 15 October 2026

Prepared around05:25IST. Overnight authorization ends06:00IST; automation remains
active until the cutoff. This summary supplements the append-only detailed ledger
in `methodology_working_doc.md` (Sections20–48) and `overnight_review_2026-10-15.md`.

## What actually finished

- Implemented measured candidate-schema shared latency, separate pending-state
  latency and rewrite-duration estimators, whole-source-family chronological splits,
  training-only scaling/SQL encoding/median baselines, missing-history exclusions,
  saved predictions/failure receipts, hashes and independent prediction audits.
- Fixed raw task retention: preserve actual query and rewrite task frames, read
  complete archived stage-attempt evidence instead of discarded Spark UI records.
- Added serialized durable submission, independent real counter sampling/durable
  persistence and real-sample availability waiting. Strict2s freshness/gap gates
  stayed unchanged. The final lock-expiry deferral branch was implemented and raw
  audited, but **was not exercised** in the three successful final episodes.
- Six successful ten-minute episodes yielded **3103queries/4rewrites**, across
  **three disjoint source families**. Independent raw roundtrip passed.1551early
  incomplete-history queries excluded from the primary demand-aware fit;1031train/
  521test queries remained. Sourcefamilies0/1train,2test; no calibration partition.
- A separate complete32-file baseline/now/later group passed all physical/frozen
  raw gates, yielding **1587queries/2rewrites**. Its existing source2window overlaps
  the fit test family, so it is diagnostic data, not a new independent test set.
  No model refit used these outcomes.

## Learned models: implemented and fitted, not accepted

| Candidate | Held-out MAE ms | Training-median MAE ms | Evidence limit |
| --- | ---: | ---: | --- |
| Shared latency |311.395|22.928|1031train/521test; only one held-out family |
| Separate, no pending maintenance |312.200|20.364|1020train/509test |
| Separate, pending maintenance |1033.551|48.999|11train/12test;9negative predictions |
| Rewrite duration |199.722|311.921|3train/1test; too small for accuracy claim |

Independent audit reconstructed actual targets, training medians, persisted model
predictions and hashes. Integrity success is not prediction acceptance. The latency
models substantially failed simple baselines, and sparse pending-state regression
produced negative predictions. Models remain **exploratory, uncalibrated and
unauthorized for scheduling**. No temporal-policy benefit or publication-level
result was established. Do not tune/retest against these held-out outcomes and
call the result independent validation.

## Physical results and failures retained

Final32-file group offered1501requests per arm. Ultimately completed baseline535,
now522,later530, leaving966/979/971queued respectively. Boundary observer lateness
89.500690/100.443621/77.118767ms was retained; census counts are not silently exact-
horizon counts. Single episodes do not establish a preferred timing policy.

| Cohort | Passed | Failed | Unattempted |
| --- | ---: | ---: | ---: |
| Historical longer nine-arm cohort |1|1|7|
| Initial overnight18 |0|1|17|
| Recovery1 |1|1|16|
| Recovery2 |0|1|17|
| Recovery3 |3|1|14|
| Recovery4 |1|1|10|
| Recovery5 |2|1|8|
| Final32-file matched group |3|0|0|

Failures concerned missing task retention, stale telemetry and actual sampling
interruptions. Each remained failed, occupied tables were not reused and failed
labels were excluded. Code repairs preceded fresh identities; no outcome-selected
retry or weakened gates. Earlier instrumentation varies across source families,
which confounds model/generalization claims. Most planned matrix cells remain
missing; a successful final32-file group does not complete the original18matrix.

## Saved evidence and fallback

- Three-family export: `results/physical_cost_candidates_three_family_20261015/`.
- Model bundle, predictions, fit record and independent audit:
  `results/candidate_cost_fit_three_family_20261015/`.
-32-file diagnostic export: `results/physical_cost_candidates_layout32_20261015/`.
- Accepted raw arms: recovery3_01..03, recovery4_01, recovery5_01..02 and
  sf1_layout32_validation_01..03 under `results/` with full dates in names.
- Six first raw packages:144files mirrored/hash matched. Final32candidate/cohort/
  three raw packages:117files mirrored/hash matched. Candidate first package20files
  and model bundle6files also hash matched. Failed packages/tables remain onworker3;
  this fallback does not claim every failed byte is copied locally.
- Nine successful table directories: **516files/2,486,276,798bytes** copied to
  `results/physical_table_byte_fallback_20261015/`. Worker3 verified local copied
  path/size/SHA inventory against original manifest and rehashed unchanged sources.
  Receipt `results/physical_table_byte_fallback_verification_20261015.json`.
  **Catalog portability is unverified**; absolute metadata paths remain server-specific.

Byte source manifest SHA:
`89e5e51c04ed818cbcd6e502282dd2c5e51d7a5991f67fca867817722a7b1a96`.
Independent model audit SHA:
`fad4fe8fb85c1c3f22ab34a54f59b61b6fc9d75ba712a306c3cf969d84f4d7f8`.
Detailed execution/hash/PID receipts are in the overnight ledger. Targeted commits
were pushed andworker3fast-forwarded with intended-file SHA agreement after units.
Unrelated dirty files/stashes and the unapproved local-only archive were preserved.
No services/processes were killed/restarted/canceled, no tables/data deleted.

## What to do next

1. Validate unsubmitted-deferral behavior in naturally occurring real telemetry
   stalls under a preregistered protocol; do not induce dummy evidence or relax
   timing rules. Sampler durability/host scheduling remains a reliability gate.
2. Preregister independent matched source blocks, actual varied layouts/regimes and
   one consistent instrumentation version.11pending-state training rows and4total
   rewrites cannot support reliable conditional/rewrite models or calibration.
3. Develop a lower-dimensional or positive-target model using training-only
   diagnostics and new untouched future test families. Keep strong median baselines
   and preserve tonight's negative fit. Diagnose extrapolation without attributing
   causality from feature-range counts alone.
4. Register precision/power and genuinely independent calibration/test blocks.
   Three source families are insufficient for90%block conformal calibration;
   at least9calibration blocks is only a mathematical minimum, not a power argument.
5. Only after cost/forecast/uncertainty gates pass, evaluate temporal schedules with
   identical real offered work, common horizon and residual debt accounting.
   Broader SQL, larger validated Iceberg scale, resource configurations and novelty
   review remain necessary for a strong SIGMOD/PVLDB submission.

Snowset supplies actual arrivals, not original SQL. Current physical workload uses
verifiedTPC-HSF1data and four custom lineitem queries; it is a trace-driven benchmark
mapping, not originalSnowflakeSQLreplay or the full22-query TPC-Hsuite. Alibaba tasks
are not integrated database SQL demand; Borg replay is absent. Resources currently
support controlled exploratory experiments, not every proposed paper claim.

## Process state at preparation

Own collector/fitter/auditor jobs finished; Spark REST reports no running jobs.
Spark/Thrift services were preserved. Physical episode/operation cutoffs passed;
no new physical work will be launched. At06:00IST the automation must pause and
leave all services/in-flight work untouched; any final status amendment is appended.
