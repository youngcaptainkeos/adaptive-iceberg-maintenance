# Offered arrivals, queueing and observation boundaries

Status: next implementation contract, not an executable replay registration.
Actual source is the independently audited Snowset cohort `observed_arrivals.csv`;
its receipt and byte digest must pin the source. It has original query identities
and timestamps, not original SQL. No query mix, client count, replay window,
common horizon or penalty weight is silently selected by this document.

## Preserve exogenous offered demand

Choose a source interval using training-only rules before held-out outcomes. Keep
every arrival's original identity and timestamp, including ties. The replay clock
may shift the interval to the present but must retain original interarrival spacing.
No time compression, thinning, padded quiet tail, completion-driven next arrival,
random curve, or future resource-profile information supplied to the forecaster.
An explicit benchmark SQL mapping must be preregistered separately and described
as a mapping, not reproduction of Snowset's original queries. The four existing
SF1 query identities are custom benchmark templates, not the full official TPC-H
query suite or an official benchmark performance result.

Use an offer/dispatch ledger independent of query completion. At each planned
arrival retain source query ID/time, shifted scheduled monotonic time, actual offer
time, durable-record time and queue-admission time. Keep generator lateness separate
from client queueing. Never silently retime the source to hide an overloaded client
pool. A record of an intended arrival is not evidence of successful submission.

## Bind actual states and events

Preallocate the physical measurement UUID before features or submission. Each
arrival follows an explicit state chain: offered, queued, dispatched, completed or
failed. Preserve each transition time and any remaining queued/in-flight work.
Dispatch records bind source identity, actual SQL-template identity/parameters,
session identity, table/snapshot, feature references and measurement UUID. Bind
service time to actual execute/fetch monotonic clocks from the existing statement
recorder. Record scheduling/intake delays rather than adding them to service time.
Never reuse a cursor concurrently; a client slot belongs to one active operation.

Validate uniqueness, full source-interval coverage, ordering and legal transitions.
Outcome records must have an actual dispatch/request; no missing, duplicate or
conflicting completion. A failure is not a zero-latency success. Forecaster history
may use observed offered demand available before the decision, not the generator's
future schedule. Dispatched/completed rates are affected by maintenance and queueing;
they cannot silently stand in for offered demand.

## Fixed boundary accounting

Both action arms share preregistered source arrivals, observation start and end,
client/resource configuration and initial logical/physical state. At the horizon,
report offered, queued, dispatched, completed, failed and still-running counts, with
identity lists so conservation can be checked. Do not drop slow or failed queries
from the headline denominator. Report queueing/service distributions separately
from completed work and useful maintenance progress.

Never cancel a running physical operation to make an arm fit its observation end.
Retain its natural completion as a boundary outcome outside the fixed-horizon
summary. Whether queued work can dispatch beyond the horizon requires an explicit
equal-arm rule. No new dispatch beyond the operational experiment cutoff. Deferred
rewrite/queue work cannot be made free by omitting residual debt. A registered
extension must apply to both arms; no post-result horizon choice or invented SLA.

## Gates before replay or training

The current order/repeatability pilot has no observed offer/queue ledger and is
not silently upgraded to trace-driven training. Implement and audit the ledger
with real source identities and actual executions after registering a bounded
mapping/window/client protocol. Keep failed/no-op/missed-exposure attempts in the
inventory. Then register independent physical variance and common-horizon blocks,
chronological splits and uncertainty calibration. No invented counterfactual costs,
fragmentation increments or policy predictions fill these missing observations.
