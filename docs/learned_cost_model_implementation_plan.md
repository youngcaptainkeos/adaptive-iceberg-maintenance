# Learned cost model: implementation and acceptance plan

Registered2026-10-14; this is the next end-to-end milestone, not a promise of
publication acceptance or a deadline that permits weakened evidence gates.

## Research target and model responsibilities

Predict measured query service consequences and rewrite duration/work from
available table/workload/host state. Use forecasts of future offered demand to
compare maintenance schedules over a common horizon, including residual queue
and maintenance debt. Arrival counts are not CPU load, and an observed query
latency is not an unobserved compact-versus-defer causal penalty.

Compare separate conditional latency estimators A/B against one shared estimator
with observed maintenance state as an input. Keep a measured rewrite-duration/
transition estimator separate where its targets/units require it. Demand forecasting
is another component. Three models is a candidate architecture, not the novelty
claim or an invariant requirement. Prediction and physical scheduler benefit must
both beat declared baselines on held-out experiments.

## Job1: verified physical cost-candidate export — start now

Input only SHA-pinned successful common-horizon arm packages; rerun raw audit,
bind every query to actual SQL/UUID/result/client clocks/windows/snapshot/files,
and retain a separate inventory of every failed/unattempted experiment. Export:

- Query table: actual service milliseconds; pre-query CPU/memory/I/O60/300-second
  windows; measured file count/bytes/rows; query identity; controller maintenance
  request/completion availability; observed queue state. Post-query task overlap
  is diagnostic outcome metadata, never a prediction feature.
- Rewrite table: actual client duration, rewritten bytes/files, added files,
  original/final state and actual pre-action windows. No-op/failed outcomes remain
  in inventory and cannot become useful-rewrite cost labels.
- Episode table: offered, completed inside/outside horizon, remaining queue IDs,
  maintenance progress and residual layout, with explicit units. No invented scalar
  penalty, SLA or counterfactual regret.

Incomplete offered-history windows remain missing with measured coverage; no
zero padding, guessed intensity, small-file threshold or synthetic augmentation.
Current diagnostic outputs are candidate data, not the retired trainer schema or
accepted calibrated corpus. Record source/exporter hashes and frozen dependencies.
Acceptance: all exported values reconstruct exactly from raw physical evidence,
failed attempts cannot slip into fitting, and no post-decision field is in X.

## Job2: complete reliable collection and preregister diversity

Register the explicit boundary preparation contract and a fresh recovery unit;
original failed attempts remain. Do not reuse occupied tables or repeat runs until
an attractive latency appears. No new SQL after the declared unit cutoff.

Preregister a matrix spanning verified physical file layouts, disjoint actual
training-trace windows, query identities and maintenance state. Layout interventions
use the same proper source rows and measured resulting files, with a named rationale;
they are controlled fragmentation, not natural ingestion. Keep actual source
spacing and all offered requests. Configured horizons/concurrency/layout candidates
are experimental parameters, never hardcoded predictions. Select repetitions from
an explicit precision target and pilot variability before held-out outcomes.

Do not endlessly expand identical SF1 pilot episodes. Verify larger data/generator/
relational provenance before SF100 claims and add richer benchmark SQL; the current
four lineitem templates are not the official22-query TPC-H suite. A second resource
configuration/environment remains necessary for broad generalization.
Acceptance: stable boundary accounting, meaningful measured feature variation,
logical/physical state checks, all attempted outcomes retained and sufficient
whole-block samples for the chosen statistical objective.

## Job3: exploratory fitting and comparison

Implement a new trainer for the candidate schema, rather than fabricating missing
legacy intensity/small-file fields. Fit transparent training-median and simple
regression baselines, separate A/B and shared candidates under identical episode
splits/hyperparameter budgets. Seeds/model settings explicitly registered; no
held-out tuning or winner selected from six pilot means. Report per-query, layout,
maintenance regime and demand-window error, all failures and data coverage.

An exploratory bundle must say uncalibrated/no scheduler authorization. Diagnostic
cross-validation can guide collection but cannot substitute for independent
chronological held-out experiments. Failure to outperform simple baselines is a
result, not permission to augment with fabricated labels.

## Job4: held-out accuracy and uncertainty

Register whole-experiment chronological train/calibration/test partitions, purge
feature histories, and separate source-window overlap families; repeated source
IDs/overlapping windows cannot quietly become independent train/test examples.
Never treat telemetry ticks, task pairs or queued requests as independent episodes.

Use independent calibration blocks and finite conformal rank. For90% block coverage
at least9calibration blocks are mathematically necessary, not a sufficient scientific
sample-size/power argument. Check empirical coverage/accuracy per query/state,
report dependent/nonstationary limitations, and refuse promotion on failed gates.
Acceptance limits/precision/risk targets need justified preregistration, not made-up
values added to make the first fit pass. Keep actual interval units and no fixed
uncertainty offset. Archive complete evidence with any promoted bundle.

## Job5: temporal scheduler and paper evaluation

Feed past-observation forecasts into a receding-horizon action comparison using
measured cost/transition models. Evaluate no-maintenance/always-compact, a justified
reactive policy, persistence forecasting and learned forecasting under identical
work and horizon/debt rules. Literature-derived baselines must be faithfully
implemented or clearly labeled prototypes. An oracle future is a separate ceiling,
never training/runtime input to the learned policy.

Run held-out counterbalanced physical policy episodes, uncertainty and forecast
ablations, workload/layout/scale shifts. Query metrics, completed work and remaining
debt must support the claimed benefit; prediction MAE alone is not a scheduler paper.
No arbitrary mixed-unit objective or invented SLA. Negative findings may require
changing the research hypothesis. Complete primary-source novelty review before
claiming SIGMOD/PVLDB-level originality.

## Working schedule and documentation

Exploratory fitting is an engineering target of1–2focused working days once the
export and reliable diverse collection exist. Defensible evaluation may require
several further collection days; larger scale/provenance/generalization can extend
that. These are effort estimates, not evidence acceptance or publication promises.

After every major job append to `methodology_working_doc.md`: purpose/hypothesis,
protocol/code revision, data/source provenance, pipeline changes, raw outputs,
checks, observed/negative results, failures, limitations, and next gate. Keep the
updated-master file's append-only pointer synchronized. Preserve old claims as
history and supersede them explicitly. Every repository unit: targeted commit,
GitHub push, worker3 fast-forward and intended SHA256 agreement; preserve dirt.
All validation/physical runs occur on worker3 detached under nohup with log/PID/
expected check time. Never restart/kill/cancel services or delete tables/data.

## Job1 completion/readiness —2026-10-14

Implemented and ran the raw-verified exporter and independent round-trip verifier
on worker3 under nohup:489query rows,4rewrite rows,7successful episodes. Source
failures/unattempted remain excluded and recorded. Artifact hashes mirrored.
`physical_cost_candidate_readiness_2026-10-14.json` shows one connected overlapping
source interval family and no full300-second offered-demand history rows. This
blocks independent source-family train/test/calibration and demand-history inputs;
it does not erase the valid host windows/physical latency targets. Next collection
must explicitly address those gaps and varied layouts, rather than counting more
queries from the same source minute as independent trials. No model fit occurred.

## Exploratory trainer preregistration —2026-10-14 evening

`train_candidate_cost_models.py` implements candidate-schema shared latency,
separate latency conditional on measured maintenance-client pending state, and
rewrite client-duration Ridge regressions. Register alpha=1.0 for the first fit:
unit-scaled predictors with modest L2 stabilization, no held-out search; it is an
experimental model parameter, not a policy prediction. Training-only SQL one-hot
encoding, feature scaling and per-SQL median latency baselines; rewrite baseline
is training median. No clipping or missing-value imputation. Negative predictions
are reported as a limitation. Separate/shared comparisons must use the same
retained query set; do not infer exact engine-active state from client pending.

Planned split: first two connected source-window families train, third test, all
whole episodes and layouts within each family stay together. Exact export and
verification SHA256, family indices, alpha, output and demand-history choice must
be registered in a candidate_cost_fit_v1 JSON before execution. Full60/300s offered
history is required for the primary demand-aware latency comparison; early rows
are excluded with explicit UUID inventory. Rewrite regression uses measured
pre-action host/layout fields only. One source family cannot produce this split.
No calibration partition, confidence interval, fitted scheduler or winner claim
with three source families. Report held-out predictions and per-episode/SQL/layout/
pending-state MAE against training medians. Insufficient state rows remain not-fit.

This is source implementation pending worker3 syntax validation and later actual
end-to-end fitting. Run heavy verification/fitting only after physical collection
is inactive. Bind future export/verification to actual completed raw evidence;
never create placeholder hashes/labels to exercise a successful fit.

## First fit outcome and next independent gates —2026-10-15

First chronological fit was executed and independently reconstructed from saved
real CSV targets, training medians and persisted models. Shared latency MAE311.395ms
versus median22.928ms across521heldoutrows. SeparatependingFalse312.200versus20.364ms;
pendingTrue1033.551versus48.999ms on12testrows/11trainrows,9negativepredictions.
Rewrite199.722versus311.921ms on exactly1testrewrite/3trainrewrites. Models remain
exploratory and rejected for scheduler use; one rewrite result cannot establish
accuracy. No automatic winner, post-test feature pruning/refit or calibration.

Next gate priorities:

1. Fix availability race between waiting for durable samples and acquiring the
   submission log lock. If samples are stale at lock acquisition, release before
   waiting and record unsubmitted preparation; preserve FIFO, cutoff and all2s
   gap/freshness rules. No physical SQL retry or erased failed episodes. Registered
   live instrumentation comparison/new tables required; historical audit cannot
   validate a new synchronization path. A separate-process telemetry observer may
   be needed if Python/log contention continues; no fabricated catch-up counters.
2. Collect independent matched source blocks with both original layouts and
   measured pre/during/post maintenance regimes.11pendingtrainingqueries from one
   episode are not a defensible conditional estimator. Same instrumentation across
   train/calibration/test, verified larger scale and another resource setting remain
   necessary; source0/32 and many other planned cells currently missing.
3. Develop any positivity-preserving/log-target or lower-dimensional candidate using
   training-only diagnostics with a new preregistered comparison and untouched
   future test families. Current heldout results stay negative historical evidence;
   do not tune alpha/remove inconvenient predictors on this test set and call it
   independent validation. Feature-range diagnostics identify shifts, not causes.
4. Preserve raw packages and actual table bytes/catalog references, then independent
   calibration/power protocol. No accepted cost model, scheduler or publication-level
   temporal maintenance benefit exists yet. Strong median baselines must stay in
   future evaluation; completing the pipeline is not scientific acceptance.
