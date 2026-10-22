# One real development run: new publication collector

## Scope frozen before new cost outcomes

Protocol `protocols/live_collection_20261022.json`; mapping selection
`protocols/live_day6_mapping_20261022.json`. First complete nonempty ten-minute
window in source day6 of the verified Snowset warehouse cohort. Source selection
uses arrival timestamps/counts only. The expanded source interval includes300s
lookback and is checked against the consumed cost-family registry before SQL.
Engineering development only; no fresh test/calibration claim. Other historical
forecast usage and same-warehouse dependence remain limitations.

Fresh destination `local.experiment.integrity_horizon_three_model_pub_20261022_01`.
Verified existing SF1 source/snapshot and four real custom SQL references retained.
16-file layout matches prior engineering source scale; no natural-ingestion claim.
600s uncompressed arrivals; compaction at300s makes complete offered history
possible during pending-state observations. Telemetry305s warmup,1s cadence,
60/300s windows, existing2s gap/age gates and95% coverage retained. New publication
maxage2s preserves that age requirement. No new episode after10:30UTC (16:00IST),
no new SQL after11:30UTC (17:00IST); active calls finish naturally. These are
operational safety cutoffs, not modeled policy constants. No retries or tuning
from this outcome. Existing failed/unattempted experiments remain unchanged.

## Edits and code responsibilities

`runtime/collect.py` is a clearly isolated fork of the existing real common-horizon
collector. Preserves source multiset/query-result checks, fresh-table refusal,
engine markers/foreign-work checks, FIFO/all offered IDs, real telemetry, horizon
and actual-RPC cutoff gates, engine archives and raw audits. Adds new source
archives and publication audit; does not modify the old/frozen collector.

`runtime/collector_bridge.py` provides a new EventLog/StatementRecorder pair only
inside this collector. Physical queue transitions update the locked direct-state
journal. Maintenance request/actual return/failure update pending state; this is
client lifetime, not Spark-active inference. Query preparation first performs the
existing durable preparation/dispatch, then publishes actual query/layout/host
features. SQL/file layout remains tied to the explicit recorded snapshot; cached
metadata access is not relabelled as a fresh metadata RPC. Raw original inventory
measurement references remain bound in source_context.

The query runs through the existing actual StatementRecorder so all original
markers/result/timing evidence remain available. The new PublicationJournal's
standalone execute_query/execute_maintenance wrappers are NOT the integration
path exercised here. After actual completion, the bridge records exact query UUID,
full publication receipt, real execute/fetch clocks and verifies receipt-before-call
and feature age. An independent journal scan reconstructs pending IDs, queue depth,
state versions and persistence records and matches every completed trace query.
Every receipt stays runtime_adapter_accepted false pending independent acceptance.

`runtime/publication.py` adds a strictly explicit unsubmitted requeue case. The
bridge supplies the actual UUID only after a real statement_not_submitted event;
the original physical ledger/raw audit still requires the registered horizon
abort/no actual SQL proof. No generic catch-and-retry or prediction fallback.

`runtime/run_registered_collection.py` orchestrates mapping, independent mapping
audit and one physical episode. Verifies registered source hashes before both
preparation and physical launch, obtains common/queue/model locks, checks source
interval overlap and freezes the derived physical configuration (actual mapping
receipt hashes are known only after preparation). Every child stage runs through
the ntfy failure wrapper with unique log/receipt. Failures stop dependencies;
outputs and stage status remain. Completed measurement sends a separate success
notification; delivery failure is recorded without rewriting experiment status.

## Outputs and monitoring

Parent `results/three_model_live_collection_20261022/{progress,result}.json` and
per-stage logs; mapping `results/three_model_live_day6_20261022/`; actual physical
raw package `results/sf1_three_model_publication_20261022_01/` with events,
feature_publication journal, frozen source, registration and result/failure.
Parent launched detached under nohup and failure wrapper. Estimate15–30minutes,
not a guarantee; check after2minutes for dependency errors and around25minutes
for completion. No laptop connection is needed once launched.

This run validates measurement integration on actual data; it does not fit A/B/C,
provide an independent model test, establish causal A-minus-B effects, solve
backlog/full-drain policy comparison or prove publication novelty. Additional
source roles/resource configurations/calibration remain future registrations.
