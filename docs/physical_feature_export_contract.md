# Physical feature export contract

Status: next implementation gate. No existing correctness pilot is approved as a
training cohort. Raw timing and task-label checks do not certify measured features.

## Bind observations to actual submissions

Allocate the query measurement ID before its features/state are captured. The
request event must reference exact feature-window records and exact metadata
statement measurement IDs, rather than joining telemetry by nearest timestamp or
joining concurrent queries by query identity alone. Preserve failed/no-op/missed
exposure observations separately; report exclusions and forbid selection on target
latency. A CSV field's presence or an artifact hash alone does not prove its meaning.

For each 60/300-second window, retain exact monotonic bounds and the sampler's actual
last available sample frontier. Independently reconstruct from original counter
intervals, preserving coverage, gap and freshness gates. Both cutoff and feature
availability must precede the actual query submission. CPU percentages are 100 times
measured busy fractions; CPU trend needs a registered definition/units. Memory use
is host total minus available divided by total, with explicit units; it is not query
RSS. Feature-history windows can contain real prior work but no future samples.

The source-verification/download process is real host background activity. Record
its presence and resource effects; do not silently label that episode as an idle
server or attribute its I/O to Iceberg. Run measured cohorts after acquisition or
preregister/background-match such conditions. No cache flushing or artificial
slowdown is allowed to manufacture exposure.

## Bind layout to the queried snapshot

Record the exact Iceberg snapshot, table, catalog/engine identity, and the metadata
statement used to read that snapshot's data-file inventory. Query SQL must actually
pin the same snapshot for matched before/during/after interference controls. A
snapshot field in a CSV cannot substitute for snapshot-pinned SQL. Compacted-layout
benefit is a separate comparison with its own recorded snapshot.

Derive record/file counts, byte size and average file size from the physical file
inventory, including explicit byte-to-unit conversion. A small-file feature requires
a preregistered byte threshold and rationale or a reviewed engine-derived planning
rule. Do not silently insert a default threshold or treat a size count as guaranteed
rewrite eligibility. Eligibility also depends on grouping and actual rewrite
planning; preserve the positive physical result separately. No fixed file-growth
increment or random self-insert may provide future layout transitions.

## Bind demand and experimental context

Normalized intensity remains unavailable until a verified arrival transformation
and training-only scaling protocol exist. Do not fill it with zero for a quiet
host or completed-query CPU usage. A diagnostic quiet-host cohort can be recorded
without that feature, but requires a separately reviewed model schema before fitting.
Original offered arrivals, queue delay, dispatch and service time remain distinct.

Record the Spark application/session and capture scope for every task response;
missing retained job/stage/task history is a failed gate. Independently inventory
other foreground jobs and background processes during each episode. The four-client
correctness pilot has known interference from other probes and does not identify
the effect of maintenance alone. The next variance cohort uses one foreground probe
per rewrite with bracketing controls pinned to the original files, then separately
covers query-first order and more than one observed layout/load condition.

Training acceptance additionally requires registered independent experiment blocks,
chronological purging, calibration sample sufficiency and held-out accuracy/coverage.
This contract does not supply arbitrary model hyperparameters, sample counts,
performance claims or a publication-readiness assertion.

## Action-time feature boundary

Query-submission windows during maintenance are post-action observations. They may
describe measured interference, but cannot become controller features for predicting
the effect of starting maintenance earlier. New matched episodes require a separate
`maintenance_decision_observation`, allocated with the actual maintenance UUID and
recorded before that statement's client execute start. Exact history bounds/frontier,
original snapshot/file inventory, table and actual-action freshness must bind to its
request. Query-time and action-time observations remain separate. The first matched
Q1 episode has no such record and remains diagnostic-only; no nearest-window join or
backfilled decision context can repair it. A common-horizon cost/export/training
protocol is still required before fitting controller counterfactual/action costs.
