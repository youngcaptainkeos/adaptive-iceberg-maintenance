# Daytime evidence review — 2026-10-14

## Initial state and handover

New work explicitly authorized after overnight cutoff; automation remains paused.
Interrupted fallback report committed as0f82c42, pushed and worker3 fast-forwarded;
full HEAD and three intended file hashes matched. Before today’s pilot preparation,
worker3 reported no own physical run and no active Spark jobs. Existing services,
tables/data, unrelated dirty files and unapproved local-only archive preserved.

## Preregistered first unit

See `daytime_execution_plan_2026-10-14.md` and
`experiment_protocols/sf1_action_order_repeatability_20261014.json`.
Implement dedicated-session query-first/active-task evidence and signed descriptive
repeatability review. Four Q1/SF1 episodes in preregistered ABBA order, two per
order, no final scientific sample-count inference. Every real episode must pass
raw export before the next. Stop on a failed gate, preserve evidence; no dummy
runs, manufactured exposure, interval/metadata freshness relaxation or cost fitting.
Code/config were published and hash-matched before execution.

## Pre-execution audit

All five changed/new Python modules compiled from source without executing a
synthetic scenario or writing fake data. Updated exporter replayed two actual
complete historical packages Q1/Q2; original timing/window/layout/task/result/
multiset checks still passed. Their missing explicit order registration remains
absent, with no retrospective query-first assertion.

New query-first path captures fresh inventory before query launch, observes its
actual marked active stages, then captures action windows just before real rewrite.
The two-second metadata gate is checked before action and at actual RPC in the
independent validator. No preparatory Spark metadata query runs during treatment.
Each cursor has a dedicated role; query-session refresh after natural completion
prevents stale new-snapshot reads. Completed task overlap remains a separate strict
gate from submission order. REST response availability bounds the active-stage
observation; it is not treated as an instantaneous sample at request start.

Cohort controller pins each registered config before and after execution, freezes
runner/export dependencies, runs serially, and independently exports/audits each
real episode before another. A failed gate records the attempted episode and stops
the remaining schedule; active operations finish naturally. No cost model fit.

## Actual launch

Implementation/protocol unitc7eeaf6 pushed and worker3 fast-forwarded; full HEAD
`c7eeaf69c45b3ef7f7e69bf834c54d82b89a110d` and all12 intended file hashes matched.
Before launch no own physical/source cohort and no active Spark jobs. Worker3
reported45,582,340,096 available RAM bytes and493,505,921,024 free disk bytes.
Coordinator PID459764, launched03:18:22 UTC (08:48:22 IST), output
`results/sf1_order_repeatability_20261014/` and matching launch log/JSON receipt.
Four distinct preregistered episodes passed their independent raw export gates and
completed naturally. No new operation was launched after the registered
04:44:59 UTC (10:14:59 IST) cutoff. This was a bounded daytime unit, not a resumed
overnight automation.

## Completed cohort audit

All four SF1 episodes passed: two query-first and two rewrite-first. Each cloned
the verified 6,001,215-row table, rewrote 16 files to one, preserved exact row
multisets and query results, and recorded actual Spark task overlap. The complete
raw and exported packages for all four episodes were mirrored to the local
workspace and SHA256-checked against worker3; see
`action_order_artifact_mirror_2026-10-14.json` and
`results/sf1_order_repeat_20261014_01` through `_04`.

The signed exploratory contrast (during latency minus the mean of the before and
after original-layout controls) was +93.94 and +97.48 ms for query-first, and
-46.43 and +168.08 ms for rewrite-first. With only two episodes per order, these
are descriptive values, not stable variances, confidence intervals, causal
effects, or cost-training labels. More concerning, the before-to-after control
drift was -64.57/-142.51 ms in query-first and +86.67/+92.69 ms in rewrite-first,
which is on the same scale as the during-rewrite contrasts. This is direct evidence
that time/cache drift can explain the apparent signal. The separate compacted
versus original-layout comparison is also cache/time-confounded.

The audit artifact is `action_order_repeatability_review_2026-10-14.json`.
No forecast, cost model, conformal interval, or scheduler was trained or accepted.
One local review invocation was started before the artifact mirror finished and
failed because its input files were not present yet. It did not touch the physical
cohort; after the copy and SHA256 verification completed, the review was rerun and
passed. This was an avoidable orchestration error, not a cohort failure.

## Dataset decision and next gate

TPC-H SF1 is the controlled Iceberg data being acted on; it is not an observed
arrival trace. The verified Snowset cohort is the strongest available source for
real database query arrival times, but it has no SQL text. The one-warehouse
forecast is diagnostic only, with roughly 13.34 observed days and no adequate
independent calibration blocks for the proposed 90% conformal claim. Alibaba
2017 provides cluster-task events and resource usage, not database SQL arrivals;
it must not be presented as the query workload for this experiment. The former
Google-named mapper's silent mathematical fallback is retired: the current mapper
requires an explicit verified trace manifest and refuses an absent or inadequate
trace.

Before any cost fitting or arrival replay, register and run no-maintenance
bracketing controls to measure the query's own time/cache drift, with the same
actual query, snapshot, logging and cadence as the treatment. Then specify and
audit a transparent Snowset-arrival-to-benchmark-query mapping and an offered /
queued / dispatched / completed ledger. That replay would preserve real arrival
times while using declared benchmark SQL; it would not reproduce Snowflake's
original SQL workload. Check replay capacity before physical execution. Collect
independent common-horizon action blocks only after those controls and queue gates
pass. Do not derive counterfactual cost labels from the four pilot episodes.

## Next authorized implementation: null controls and model candidates

User authorized the next step and cost-model implementation, with every validation
and physical run on worker3 detached via nohup. Registered four fresh SF1 Q1 null
blocks matching previous actual query end-to-next-start spacings from SHA-pinned
raw logs. Same warmup/windows and result/layout/multiset gates; no rewrite/cache
flush/trace replay. Null contrasts remain descriptive, not causal cost labels.
The independent raw review reconstructs timings, windows, SQL/state, Spark tasks
and unrelated-job exclusion. Stop on any gate failure and preserve every table.
Operational cutoff 12:30 IST is not a scientific horizon.

Added opt-in shared action-conditioned latency candidate to the existing strict
A/B trainer, with identical splits/hyperparameters, whole-experiment calibration,
and unchanged per-regime/query accuracy/coverage gates. All candidates must pass
before publishing a new bundle; no automatic scheduler selection. This implements
a candidate comparison, not future-defer cost or a deployed scheduler. Current
pilot/control data cannot meet the physical training schema and independent split
requirements, so no cost fit or model promotion is authorized by these artifacts.
Snowset supplies arrivals without SQL; Alibaba supplies cluster-task events;
neither supplies action labels. Existing dataset/provenance limitations remain.

Worker3 detached prepublication checks: both changed Python files compiled;
independent review of all four actual historical episodes passed. Raw reference
gaps were [1.928607459,10.676690485], [0.591082813,12.599220833],
[0.557166038,12.715071664], [8.018002224,4.622654346] seconds. The modified trainer
correctly refused actual diagnostic observations because required physical
training fields/splits were absent. No model was fitted; shared fitting/acceptance
remains unvalidated until a legitimate corpus exists. Logs staged on worker3 at
`/tmp/capstone-null-controls-20261014/validation.log` and `model_validation.log`.

## Detached control execution

Implementation committed/pushed as `5f2a5544ebe1cd471052f5edf2ee4dd7658ddb4e`;
worker3 fast-forwarded, all eight intended SHA256s matched. Real control runner
launched under nohup, PID476932 confirmed alive at04:19:47 UTC (09:49:47 IST).
Output `results/sf1_null_controls_20261014/`; launch log
`results/sf1_null_controls_20261014_launch.log`. Four 305-second warmups plus
actual query, clone, validation and observed spacing overhead imply an estimated
10:15–10:20 IST check-in, not a completion guarantee. At handover the run is active;
no result/variance/causal-effect claim is made. Any failure stops dependent blocks
and retains evidence; any in-flight operation completes naturally.

Next check: inspect PID/log/progress without starting another physical run. After
natural completion, execute the frozen runner's `--audit-directory` and
`--audit-output` on worker3 under nohup, mirror all raw/frozen-code/reference/audit
files, verify SHA256s, and document signed null contrasts alongside historical
values without causal subtraction. Only then register queue/mapping and common-
horizon collection. Shared candidate fitting remains blocked on real independent
training/calibration/test data; its successful fit path has not yet been exercised.

## Null-control failure diagnosis and repair

User reported the missing completion. Worker3 inspection at05:19:55 UTC found
PID476932 ended naturally, no active Spark jobs, one completed physical block,
zero SQL failures, and a terminal auditor KeyError `file_state`. This was an
implementation error: block summaries contain exact `files` and `snapshot_id`,
while the audit incorrectly assumed an aggregate field in that summary.

Repaired auditor derives aggregates from actual exact files and additionally
binds both initial/final file lists and snapshots to raw SQL results. Explicit
partial review records all registered/unattempted blocks and terminal failures;
it does not change the original failed status. Worker3 compiled corrected code
and audited the first completed block from original frozen code/logs with no new
query. It passed timing/windows/snapshot/files/task/result/exact-multiset checks.
Observed before/middle/after latencies:2513.566123/2440.186065/2501.015968ms;
signed null contrast−67.1049805ms. One block is not a variance/causal conclusion.
Review: `no_maintenance_partial_review_2026-10-14.json`; full failed raw package
mirrored at `results/sf1_null_controls_20261014/`. Original failure.json remains.

Recovery preregisters only the three unattempted original blocks/cadences/tables,
not a repeated first block or a retry selected by outcome. Historical protocol,
raw logs and failed table are preserved. The same12:30 IST operational cutoff
applies. No cost labels/model promotion or maintenance operation added.
