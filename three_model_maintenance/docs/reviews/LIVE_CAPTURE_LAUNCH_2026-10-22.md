# Live capture launch and code explanation

## Actual status at launch review

Runtime revision `976dbb2fc4e4edea28b61fdc8a6418970c9a72ed`.
Detached parent wrapper1234592, orchestrator1234593; physical wrapper1234753,
collector1234754 on worker3. Parent started08:11:40UTC (13:41:40IST), physical
stage08:11:59UTC (13:41:59IST),22October2026. Actual telemetry recorded on the new
table during warmup. Mapping completed08:11:51UTC and its independent audit passed
08:11:59UTC; physical replay/compaction/terminal audits pending at this review.
No physical success, fitted model or completed corpus claimed. Check around
14:05IST; estimate15–30minutes from launch, not a deadline/guarantee.

Actual mapping:1554offered source arrivals in
2018-02-27T20:00:00.286000Z–20:10:00.286000Z. Every mapped ID/timestamp/spacing
preserved. Expanded interval includes300s lookback and does not overlap the three
registered consumed cost windows. This checks that registry only, not global
independence or original Snowflake SQL. Incomplete offered histories remain missing
until the live replay has accumulated sufficient past observations.

Immutable physical registration SHA256
`ea1942f2da0757167b182b7abc8c1b7a4b878241c5f395e0e2af32304d040ef5`.
Mapping receipt SHA256
`d1d2cffa1527af24ada85b48217455288ddecf2957a3d2dbceded50139220ec3`;
mapping audit SHA256
`0eb9ffd5737e63d58b3b3bf38c5ba181596c80cae2ee912a773b8bbdc6f50e0f`.
These completed artifacts were mirrored and local/server SHA agreement verified.
Active raw evidence remains on worker3; no completed raw backup claimed.

## How the implementation runs

1. `run_registered_collection.run` acquires the three-model, queue-study and cohort
   reservation locks, probes physical availability, checks SHA-bound source files
   and parses actual Python source before running real work. It invokes the existing
   mapping exporter and independent mapping audit. It checks the actual selected
   source interval plus300s against consumed cost history, freezes the physical JSON
   using actual mapping hashes and only then launches the collector. Source hashes
   are checked again before physical launch. Each stage gets its own log, failure
   wrapper and ntfy receipt. No failed stage is automatically retried.
2. `collect.py` is an isolated fork of the established physical common-horizon
   collector. It makes a fresh16-file table from the accepted SF1 snapshot, validates
   source state, warms real telemetry305s and releases the1554real arrivals at their
   original offsets over600s. Four existing custom SQL templates are assigned by
   the declared round-robin mapping. A real binpack rewrite is scheduled at300s.
   No arrivals are thinned to match the single SQL client's capacity; residual queue
   and any refused/failed requests remain visible. Existing reference-result,
   logical-multiset, Spark task/foreign-work, telemetry and actual-RPC cutoff audits
   are preserved. Old source/frozen collectors are not patched.
3. `collector_bridge.build_classes` supplies subclasses of the physical log and
   statement recorder only for this new collector. Queue events update the direct
   state journal under the same physical-log ordering. Maintenance start/return/
   failure updates the pending set instead of reconstructing it later from timestamp
   comparisons. The serialized query preparation captures actual SQL ID, explicit
   snapshot layout and measured host windows, then publishes them before SQL intent.
   Original physical StatementRecorder remains responsible for actual marked SQL,
   execute/fetch clocks and query-result rows. The journal's standalone cursor
   wrappers are not the path exercised by this integration.
4. `PublicationJournal.publish` records feature capture, flushes/fsyncs it, takes
   an actual post-return timestamp, persists the acknowledgement and returns a
   second observed bound. The full receipt is included in the physical event log
   and later completion binding. These bounds prove chronology under the recorded
   process clock; they are not invented exact commit times. After the actual query
   returns, the bridge checks publication-before-execute and actual feature age,
   retaining a failed experiment if those checks fail. Snapshot metadata is cached
   explicit-snapshot context; its cache-access clock is not a fresh inventory RPC.
5. `audit_publications` independently scans the new raw journal, reconstructs state
   versions/pending IDs/queue depth, matches persisted feature records and joins all
   completed trace-query UUIDs to actual execute/fetch clocks. It runs after all
   legacy raw audits. A separate requeue path exists only for a physically recorded
   statement_not_submitted UUID; the original audit still verifies no SQL execution.
   Runtime acceptance remains false pending independent review and future training
   eligibility/export checks.

## Notifications, artifacts and remaining gates

Both parent and every child stage use run_with_failure_alert.py under the detached
parent; failures POST to https://ntfy.sh/shashank_capstone_alerts and preserve their
exit codes/logs/receipts. Notification delivery failure does not hide run failure.
Actual delivery has not been certified with a dummy alert. A successful terminal
measurement also sends an evidence-linked completion notification and saves its
HTTP outcome. Laptop disconnection does not terminate this nohup job.

Parent progress/logs: `results/three_model_live_collection_20261022/`.
Launch log: `results/three_model_live_collection_20261022_launch.log`.
Physical package: `results/sf1_three_model_publication_20261022_01/`, including
`events.jsonl`, `feature_publication.jsonl`, frozen code and result/failure records.
No services/processes/tables are shut down, killed or deleted by the orchestration.
Normal sampler/file/connection cleanup is part of the existing collector lifecycle.

This is one engineering development episode, not A/B/C training, calibrated model
acceptance, a fresh held-out test, a full-drain policy comparison or an A* novelty
result. Next inspect actual terminal gates, preserve failures/unattempted work, then
independently export and admit eligible new publication-bound measurements before
any model fitting. Extra fsync/archival overhead remains measured workload cost.


## First new live publication-bound queries observed — 22 October 2026

Read-only worker3 checkpoint08:17:27UTC (13:47:27IST): physicalcollector1234754 running5m29s, five actual three_model_query_binding events present after registered warmup. This confirms first real SQL completions linked to new publication receipts, not merely process startup/source-only constructor checks. No failure shown in physical log at checkpoint. Midpoint compaction and terminal legacy/direct-state audits remain pending; A-condition, final integrity, useful rewrite and accepted training eligibility not yet established. Running source/configs unchanged. No new test/SQL launched by checkpoint and no terminal success claimed.
