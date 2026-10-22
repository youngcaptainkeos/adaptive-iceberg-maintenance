# Durable sample notification and automatic candidate export

## Observed outcome, preserved

Attempt02 completed physical stage09:54:15UTC22October (15:24IST), exit0.
Raw correctness/freshness/publication checks passed.109query captures/completions,
A0/B109; no models fitted or accepted. Useful rewrite16files→1file recorded with
13.829652766s maintenance call at replay302.937149720–316.766802486s. Completion
ntfy deliveredHTTP200. Attempt01 remains failed; attempt02 is a valid engineering
measurement with insufficient A coverage, not a failed raw gate or a model success.

Read-only actual-evidence coverage diagnostic wrapper1285408: a telemetry wait
266.993938037–409.018536980s (142.024598943s) overlapped the entire maintenance
call.73publications occurred after300s of replay, all B; actual offered-prefix
completeness is verified by export rather than inferred from this count alone.
Temporal overlap explains missing observations during that wait, not exclusive
causal attribution of the wait to storage/scheduler/polling. Source shows once-per-
second polling at the same cadence as sampling; with1s admission this can alias
fresh availability. No claim that notification guarantees enough A rows.

## Implementation

`runtime/notifying_sampler.py` subclasses the registered physical sampler. Keep
real psutil counters, cadence, intervals, window arithmetic, coverage and age gates.
Only after a telemetry interval has actually flushed/fsynced does it append to
available samples and notify a Condition using the sampler lock. The waiter releases
that lock while sleeping and wakes on actual publication/failure/deadline, replacing
fixed-period polling. Never log while holding sampler lock: original log→sampler
ordering stays intact. No synthetic tick, sample timestamp repair or fresh flag for
unpersisted intervals. All real waits remain logged.

`runtime/collect.py` selects the new sampler and archives its source.1s preparation
admission,2s actual sample-frontier limit,95%coverage/2s gaps, FIFO/queue accounting,
query results, engine evidence and logical-table checks remain unchanged. Terminal
stale refusal still preserves all remaining offered debt; it does not create a label.

`preparation/export_live_candidates.py` re-runs full recorded raw/publication audits,
checks unchanged terminal event hashes and actual query UUID/service targets, exports
all completed rows and exact publication receipts. Offered histories use only the
actual prior offered-log prefix at publication; incomplete60/300s histories remain
missing rather than zero. Explicit14feature allowlist excludes targets/outcomes.
Report includes complete-history A/B support, SHA-bound CSV/receipt outputs and known
source-family role. Runtime acceptance and fit authorization remain false: exporting
candidate rows does not promote calibration, independence or a scheduler.

`run_registered_collection.py` optionally verifies/exports attempt02 before new
physical work, exports attempt03 after terminal raw/publication success and reports
condition support in completion ntfy. Progress remains export-pending until export
finishes. Absence of either condition explicitly blocks A/B support; presence alone
is not training approval or statistical sufficiency. Every stage uses the ntfy failure
wrapper and no retry. No code/threshold alteration to prior raw evidence or receipts.

## Registration before attempt03

Same known day6 first1554arrivals/four imposed real SF1 templates; this is repeated
engineering development, not independent test/calibration. Fresh isolated table
`local.experiment.integrity_horizon_three_model_pub_20261022_03`, new output paths.
305s warmup,600s actual arrivals,16files and rewrite at300s retained. No new episode
after12:00UTC17:30IST; no newSQL after13:00UTC18:30IST, natural completion of active
calls. New unit cutoffs registered after earlier completed unit, not extension of a
running/expired operation. Expected20–30minutes; no guarantee of A support/performance.

Regression reuses all297actual failed-run query clocks to verify unchanged strict
frontier predicate and additionally parses/imports new notification/export source.
This does not test concurrent Condition behavior; that needs actual new execution.
Then independently re-audit/export actual attempt02 before launch, not dummy inputs.
Automatic attempt03 export uses only its own passed raw record. Failed/unattempted
stages preserved. Do not use one known family as an independent model validation set.
