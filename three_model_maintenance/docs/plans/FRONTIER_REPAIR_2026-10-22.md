# Submission-frontier repair and one registered recovery

The first new publication run remains failed. Seven of297query calls used source
samples older than the unchanged2s age limit (worst2.194519463s); the window's
calculation clock was recent but its input sample was already1.65–1.87s old.
Observed calculation-to-call delay for violations was0.3159–0.4084s. No assertion
that all delay is removable logging overhead.

## Repair

`runtime/submission.py`: isolated copy of the physical StatementRecorder's real
call/timing logic. After durable preparation and intent and after releasing the log
lock, read actual prepared-window sample frontiers, stamp the client call boundary
and check age against2s. No SQL if a frontier is stale/future. Successful calls keep
unchanged SQL markers, execute/fetch timing, rows and exception records. This is not
a forecast or policy threshold. A tiny checking/scheduling interval remains between
the recorded call boundary and actual Python invocation, as with the original
recorder; no atomic engine-start claim.

`runtime/collect.py`: real-sample preparation admission uses1s instead of2s,
leaving1s nominal headroom for the previously observed~0.4s preparation delay.
This is a registered stricter operational limit, not a guarantee. Waits occur
outside the durable log lock; inside-lock expiration raises the existing no-intent
sample-wait branch. The final acceptance limit stays exactly2s.

A final stale-sample refusal is terminal for query dispatch in this engineering
unit: record no-SQL intent/refusal, requeue that request and retain all remaining
offered queue debt. No thinning, repeated SQL, new observation chosen until a
favorable measurement, copied timestamp or acceptance-threshold change. This is
NOT a full-drain execution or complete SQL workload and cannot be labelled as one.
An early refusal can prevent useful A support; report it and withhold fitting.

`runtime/queue_ledger.py`: isolated queue-ledger copy permits the explicit stale
terminal requeue only when the physical log has a statement_not_submitted UUID.
`collect.audit` requires exact source-window frontiers, actual age violation at the
refused boundary, unchanged2s age limit, no completed SQL/no Spark job for the refused
UUID, a single terminal refusal and every source request accounted for. Existing
horizon-requeue proof remains. Executed-query freshness/correctness gates unchanged.

`collector_bridge.py`: use the repaired recorder for trace SQL, retain input sample
frontiers in publication source context, check those frontiers (not calculation
clock) against actual execution and reconstruct them in the publication audit.
Standalone PublicationJournal cursor wrappers remain outside this collection path.

## Real regression and recovery

`audits/frontier_guard.py` checks the pure repaired predicate on all297actual query
clocks from attempt01 and must reject precisely the7IDs already identified by the
independent failed-evidence diagnosis. No fake cursor, boundary times or dummy data.
It parses hash-bound source and imports the collector. Parent refuses physical work
unless this new gate passes against the current recorder SHA. This is not a rerun
or re-certification of attempt01; it stays failed, with no scores recomputed.

Recovery uses fresh table `local.experiment.integrity_horizon_three_model_pub_20261022_02`,
new mapping/output registrations and explicit attempt02. Same real1554arrival
source window remains the same known development family, not new independent test
or extra statistical replication.600s arrivals,305s telemetry warmup,16files and
rewrite at300s retained. No newepisode after11:30UTC (17:00IST), noSQL after12:30UTC
(18:00IST); in-flight completes naturally. Parent and all child jobs are detached
with ntfy failure receipts; no automatic physical retry. New outputs:
`results/three_model_frontier_regression_20261022/`,
`results/three_model_live_collection_repair_20261022/`,
`results/sf1_three_model_publication_20261022_02/`.

After real raw and publication acceptance, next gate is source-/receipt-bound
eligible export and prospective candidate-fit authorization. A/B source exists;
this job does not silently promote runtime acceptance or start fitting on failed/
missing evidence. Report actual complete-history A/B support before fit selection.
One engineering family cannot validate generalization or calibration.
