# Common-horizon action-cost protocol

Status: design dependency, not an executable experiment registration or accepted
training schema. The four-query SF1 pilots validate measurement integrity only.
No horizon, load scale, repetition count, query mix, penalty weight or ingestion
process is silently selected here.

## Research target

For the same initial logical table state and offered workload, compare starting
compaction now against waiting until a later candidate time. Count the costs of
waiting, interference while rewriting, and the resulting layout over the same
observation horizon. Comparing one treated query latency against one untouched
query does not measure this decision.

Forecast arrivals from past observations. Translate arrivals and query mix into
measured service consequences; arrival counts alone are not server CPU load.
Use observed rewrite duration and layout transitions. No fixed file-growth rate,
synthetic slowdown, predicted constant idle period or oracle future input can
substitute for these measurements.

## Required physical record

Register a fresh isolated episode with verified source and original snapshot/file
inventory, actual engine configuration, protocol revision and source hashes. At
each decision capture the fresh pre-action state and exact available telemetry
history, separately from features observed after maintenance starts.

Record every offered arrival identity and original timestamp, dispatch/queue
timestamps, query SQL identity, actual execute/fetch clocks, outcome and engine
task evidence. Record every attempted maintenance action, including no-ops,
missed overlap and failures, with actual metadata changes and rewritten bytes.
Physical execution must preserve logical contents and query results. Never
convert a missed-overlap episode into a positive interference label or hide its
existence from the experiment inventory.

Snowset provides query-arrival timestamps but no SQL. A benchmark SQL mapping
therefore needs explicit training-only registration and must be described as a
trace-driven benchmark mapping, not reproduction of the original warehouse.
Retain original arrival spacing. If real capacity cannot serve the offered
arrivals, report queueing and unfinished work; do not thin or shift arrivals
after seeing the results. Ingestion remains blocked until legitimate update
sources and disjoint identities/provenance are verified.

## Comparable arms and horizon

Register a variance pilot before final collection. Use repeated, separate physical
episodes with the same logical input, intended offered arrivals and comparable
initial file state. Counterbalance action/order and record host/cache/background
conditions. An isolated clone is an intervention whose initial layout must be
measured; equal row counts do not prove equal physical layout or equivalent cache.
Do not run competing arms concurrently on this single worker and call them
independent: shared CPU, disk and cache would couple their outcomes.

Choose the observation horizon from the research question and training/variance
evidence, before examining held-out action outcomes. Both arms share its start
and end. A decision near the end cannot receive a free advantage by pushing its
rewrite or queued queries beyond the boundary. Register how boundary work and
remaining maintenance debt are reported. Prefer explicit completion and debt
metrics over an arbitrary scalar penalty. If a bounded extension is registered,
apply the same accounting rule to both arms and preserve unfinished outcomes.

The overnight physical cutoff is an operational constraint, not a scientific
horizon. Do not begin a new physical operation after it or cancel ongoing work
to manufacture a completed arm.

## Labels and evaluation

Report offered-load-normalized latency/queueing distributions, actual completed
work, maintenance progress, rewritten bytes, duration and residual file state.
Before collapsing these into one objective, state units and justify any tradeoff
weights. Never add milliseconds, bytes and file counts directly. A SLA objective
needs an actual declared SLA; do not invent one from the observed latencies.

Unobserved alternative-action outcomes remain unobserved. A same-episode model
prediction is not ground truth for decision regret. Matched repeated arms support
an empirical comparison with uncertainty and recorded differences; they do not
erase temporal drift or identify every counterfactual.

Split whole independent episodes chronologically, purge overlapping histories,
reserve independent calibration blocks, and retain all attempted episodes in the
inventory. Select repetitions using declared precision goals and measured variance.
Do not count telemetry ticks or overlapping forecast windows as independent
experiments. Keep current-state scheduling, persistence forecasting, separate A/B
costs and a shared action-conditioned estimator as comparable candidates. A
forecast oracle is a separately labelled ceiling only.

## Next implementation dependencies

1. Complete the fourth-query raw measurement audit and preserve all pilot outcomes.
2. Verify source/engine resources for a bounded variance pilot, including scale,
   query-first ordering and measured layout diversity. No SF100 run before its
   typed and generator-provenance gaps are resolved.
3. Register the real arrival-to-SQL mapping, queue accounting and common-horizon
   boundaries; implement the recorder before physical replay.
4. Register independent repetitions and splits after variance evidence. Only then
   implement the accepted cost schema/export and fit models behind existing gates.
5. Evaluate temporal scheduling benefit, uncertainty and strong baselines on held-
   out physical episodes. The current forecast diagnostic and measurement pilots
   do not yet establish a publication contribution.
