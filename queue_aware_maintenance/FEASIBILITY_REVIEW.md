# Queue-aware maintenance feasibility: evidence and open gates

Working review, 19 October 2026. This is not a completed positive feasibility
report. Append superseding results; do not erase the failed attempts below.

## Intended contribution and implementation

The prototype is an external start/wait/no-action controller. It forecasts query
arrivals from strictly earlier real trace bins, combines current FIFO backlog
with measured query/rewrite costs, and compares candidate rewrite start times.
The objective is total query response time from original scheduled arrival until
actual result through full cohort drain. Rewrite duration/bytes are separate;
there is no invented cloud price, latency SLA or scalar maintenance penalty.

Three prediction components do not require three complex learned models. The
current empirical models are deliberate baselines, not evidence of novel ML.
The potential research question is whether backlog and maintenance interference
make forecast-only quiet-window timing unreliable, and whether lookahead can
improve complete physical outcomes under matched conditions. The prior project
[novelty review](../docs/novelty_comparison_2026-10-17.md) already identifies
forecast-aware maintenance/planning precedents. A forecast or a three-model
architecture by itself is not a defensible novelty claim.

## Data and claim boundaries

- Historical cost corpus: 18 completed physical episodes, 9,923 query labels,
  12 rewrite labels and three source-overlap families. These are development
  history. Previously examined test outcomes are not a fresh test set.
- Prospective physical scope: two contiguous 1,200-second source windows,
  3,067 and 3,211 real arrivals, four policies per window, full drain. These
  windows share a day; eight arms do not create eight independent demand days.
- Demand is real Snowset arrival timing mapped to four benchmark SQL templates.
  Missing Snowflake SQL is not inferred. This is a trace-driven benchmark
  mapping, not replay of original production queries.
- Table is real TPC-H SF1 lineitem, 6,001,215 rows, initially 16 files, with at
  most one rewrite per arm. There is no continuing ingestion in this scope.
- Single query client and static small table limit capacity/generalization
  claims. Host counters are recorded; the current model does not forecast
  arbitrary external server CPU/I/O load. Arrival forecasting is not a complete
  server-load forecast.

## What the audits established

| Item | Authoritative evidence | Current meaning |
|---|---|---|
| Original physical initialization | `results/queue_aware_maintenance_20261019/cohort/result.json` | 0 passed, 1 failed, 7 unattempted; table preserved |
| Exact logical table equality | `multiset_container_repair/result.json` | Actual count zero; client returns tuple rows, while old check expected list rows |
| Corrected equality check | `run_episode.py`, actual read-only repair receipt | Exact one-row/one-column/zero gate retained |
| Live recovery | `cohort_container_repair/progress.json` plus actual PIDs | Actual controller/rewrite/query execution; not yet complete cohort |
| Original model semantics | `simulator_semantics_audit/result.json` | Failed: all 61 real-source boundary examples contradict whole-call label interpretation |
| Separate snapshot model | `snapshot_model_reconstruction/result.json` | 131,838 real-source query/candidate checks passed; no physical validation |
| Explicit version wiring | `controller_wiring/result.json` | 16 actual-source policy/window/version checks passed; legacy behavior preserved |
| Operational timing | `runtime_budget_prefix/result.json`, exact raw prefix | Long busy inter-call gaps coincide with freshness waits; original runtime estimate unreliable |
| Publication wakeup repair | `publication_sampler.py` and registered observer test | Implemented; real-host validation still running at this review revision |

Artifact paths in the table are relative to the study result root unless the
full root is shown. Receipts and exact SHA256 values are in the append-only
methodology and handover. A source preflight is not a physical experiment.

## Model defect and separate repair

Historical query labels measure the entire client call on a pinned snapshot.
The original simulator instead treats medians as fractional work rates and can
change a query's layout when a simulated rewrite ends. Historical measurements
do not identify those sub-query rates. A successful FIFO conservation check did
not validate this transition assumption; that earlier interpretation is
superseded by the failed semantics gate.

The separate snapshot model chooses one measured whole-call duration from the
layout/pending state at dispatch and preserves it for the query. Its source
reconstruction passed, but observational pending-state medians are still not
causal interference effects. Treating rewrite RPC completion as immediate
layout publication also remains approximate; actual metadata/session refresh
lag must be measured or explicitly bounded before stronger timing claims.

The repaired model initially chooses a 60-second wait on both windows. Its
predicted advantage over immediate is only about 22 seconds of summed response
across thousands of queries, roughly 7 milliseconds per query. This is a model
margin, not measured improvement or a robust optimum. No uncertainty-based
decision guarantee is established. The active frozen cohort uses the original
model and cannot be relabelled as validation of the repaired controller.

## Runtime defect and proposed repair

The preserved prefix contained 91 completed calls over 557.9 seconds: 83.75
seconds of client service and 382.81 seconds of busy inter-call gaps. Completed
REST request lifetimes totalled 1.118 seconds. The largest gaps, about 164,
123 and 56 seconds, contain actual telemetry-availability waits. Their exact
cause cannot be inferred from event presence alone, but the code has a concrete
aliasing hazard: it polls every second while requiring a durable sample younger
than one second from a one-second sampler. A repeated unlucky phase can miss
freshness on successive polls.

`PublicationTelemetrySampler` notifies waiting clients immediately after the
real event is flushed/fsynced and its sample becomes available. It retains the
one-second submission freshness requirement, 60/300-second windows, two-second
gap/age gates and 95% coverage. A 305-second warmup plus real publication
observations is registered to verify this observer change. This is an
instrumentation test, not the requested substantial physical PoC.

## Required next gates

1. Complete real-host publication validation and independently reconstruct its
   durable sample/window observations. Keep failures if it does not pass.
2. Bind the repaired sampler and snapshot controller explicitly in a fresh
   runtime/protocol. Never patch the active frozen cohort or delete its table.
3. Continue the existing cohort naturally within its cutoffs, preserving every
   completed/failed/unattempted arm. Do not thin/compress demand to meet time.
4. Reconstruct all complete physical evidence: actual SQL/results, pinned
   snapshots, task attribution, strict telemetry, queue transitions and exact
   full-population response integral. Comparison requires the whole registered
   cohort, not selected successful arms.
5. Give the repaired implementation its own substantial physical comparison
   before calling it physically validated. Source reconstruction and old-model
   physical runs cannot substitute. If resources/cutoffs prevent that by 6 am,
   report incomplete feasibility and preserve the working code/evidence.
6. For a paper, collect independent demand/source blocks and table layouts,
   establish decision stability under measured forecast/model errors, compare
   strong baselines under identical budgets, and measure observer overhead.
   Determine collection size from observed block-level variability and a
   preregistered precision/power target rather than inventing a convenient count.

## Completion rule

A runnable candidate exists, but a completed, defensible repaired-controller
PoC is not yet proven. Final acceptance needs actual substantial execution of
the accepted implementation, complete raw evidence, independent comparison,
explicit negative results/limits, runnable reproduction commands, mirrored
artifacts and matching source/evidence hashes. A negative scientific result is
valid; a missing or failed implementation gate is not a positive feasibility
result. The active goal remains incomplete until its full requirements are
audited against actual terminal evidence.
