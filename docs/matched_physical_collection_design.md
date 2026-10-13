# Matched physical collection design

Status: design for the next collection protocol, not permission to train or replay.

The four-client correctness pilot established result preservation and real overlap.
It did not identify an isolated maintenance effect: three other query clients also
ran during the treated query, and warm-cache/time trends could differ from controls.
Do not fit A/B models to those rows or call their latency difference causal.

## First identifiable benchmark cohort

For each supported query identity, use a new dedicated verified benchmark table and
record its fragmented snapshot. Keep the original files/snapshot after rewriting.
Pin the probe SQL to that exact original snapshot for all interference comparisons.
Measure a control before maintenance, one query during useful physical rewrite,
and a control afterwards **at the original snapshot**, not the new compacted layout.
This compares the same data/files while bracketing cache and time drift. Separately
measure the compacted snapshot to estimate layout benefit, without mixing that
contrast into the interference target.

Use one foreground probe query per event initially; exclude unrelated Spark work.
Record background processes, cache conditions and current engine configuration.
Do not flush OS caches, reset existing tables or make queries artificially slow.
Trigger from observed actual rewrite tasks; label exposure only from attributable
completed task lifetimes and a positive rewrite-file result. Preserve no-ops, failed
queries, missed-overlap attempts and all partial evidence. A missed overlap is not
a positive treatment or an invented latency target.

Subsequent cohorts must also cover queries already active when maintenance begins,
multiple measured fragmentation/rewrite-size conditions, and observed arrival load.
Small/fast SF1 queries may finish before rewrite planning completes; record that
limitation and increase real benchmark scale after provenance checks, rather than
manufacturing overlap. Query identity, layout, action order and offered demand must
have common support across control/treatment; otherwise models extrapolate.

## Precision and model gates

Preregister the bounded variance pilot separately from final train/calibration/test.
Use repeated independent rewrite episodes to estimate run-level variance; choose
final repetition counts from precision goals and observed variance. A handful of
probes or repeated telemetry ticks cannot justify a publication confidence claim.
Counterbalance action/order across episodes and retain controls on both sides.
Split whole experiments chronologically, purge overlapping feature-history windows,
and reserve independent calibration/evaluation blocks. The trainer's finite block
order-statistic and per-query error/coverage/baseline gates remain in force.

New client timing must use the actual execute-call start and record logger overhead.
Keep UTC and monotonic duration checks explicit. Metadata must identify the snapshot
used by the query; CPU/I/O windows precede submission and report coverage/freshness.
Do not invent normalized demand when the arrival source is absent. Diagnostic
benchmark cohorts can inform design/variance; they are not an accepted traced
publication training corpus until its feature/export protocol is reviewed.

## Offered load and ingestion

Replay exact observed arrivals independently of query completion, recording offered,
queued, dispatched and completed times. A bounded client pool may create queueing;
report it rather than shifting arrivals or dropping events to mimic lower load.
Benchmark query mapping is explicit because Snowset has no SQL text. Warehouse/window
selection and mapping tuning use training-only information. The forecaster receives
past observations, not the replay generator's future schedule or completed-query
resource profiles before those outcomes become available.

Ingestion requires a separate real source or official benchmark refresh data with
generator provenance, disjoint update identities and declared semantics. Random
self-inserts duplicate rows and do not establish observed ingestion or measured
fragmentation growth. No fixed file increment may substitute for these observations.
