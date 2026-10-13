# Overnight review — 2026-10-14

## In progress

Started 00:07 IST; deadline 07:00 IST. No shutdown or cancellation authorized.
Initial local/worker3 HEAD: a44f2a9edf2bcf3ae7fd77dc224863917e77cbf6.
SSH works; existing Spark Thrift app local-1791896695889 is available (3.3.4).
Preserved unrelated local changes and untracked archive/drafts/results.

Same-chat continuation `capstone-overnight-audited-implementation` created at
15-minute intervals, with explicit deadline and preservation rules.

## Evidence ledger

Implemented durable exclusive JSONL event logging, client statement timing/results/
failure records, raw Spark REST capture and independent counter-based telemetry.
Commit: 26959b5. Pushed and synced; three intended file SHA256 values matched.

Actual observer validation on worker3 recorded seven real host intervals and raw
environment/jobs/stages responses. Five-second window reported 4.277 seconds of
measured coverage and 0.723 seconds freshness, rather than pretending complete
coverage. See `observer_integrity_validation_2026-10-14.json`. Raw evidence remains
on worker3 at `results/measurement_integrity_20261014/observer_events.jsonl`.
This validates observer plumbing only, not workload performance, per-query I/O,
60/300-second model features or engine overlap. No dummy input or model training.

Read-only catalog queries recorded in `catalog_events.jsonl` found SF1 tables in
`local.tpch`, not `local.tpch_sf1`. Catalog commands produced no matched Spark jobs;
this does not establish that query SQL markers fail to correlate with scan jobs.

**Blocking discovery:** source metadata query against `local.tpch.lineitem.files`
failed because its snapshot manifest points to
`file:/home/shashank/Link to PDocuments/Capstone/implementation/warehouse/tpch/...`,
a laptop-only path absent on worker3. Source snapshot ID observed in history:
8128630582928284438. Failure is preserved in
`results/measurement_integrity_20261014/source_metadata_events.jsonl`.
Earlier successful SELECT version/history must not be treated as data readability.
Do not rewrite/reset this historical table to hide the failure. Next unit must
create its own uniquely named Iceberg table from verified SF1 source `.tbl` files,
record generator/source hashes and ingestion schema, and validate loaded cardinality.

Legacy launch paths remain blocked. No benchmark workload or rewrite has run yet.
Existing Spark/service/table state preserved; only our observation thread stopped.

### 00:24–00:31 IST: isolated source preparation

Implemented `prepare_correctness_table.py` and preregistered explicit SF1 preparation
configuration, committed/pushed/synced as 4d38c84. Three changed file hashes matched
before execution. Source parsing checks every line has the reviewed 16 pipe-separated
fields plus trailing separator; typed CSV FAILFAST checks all columns for nulls with
column pruning disabled. Destination-exists checks forbid overwrite, and a host-local
advisory lock prevents duplicate preparation instances.

One launch used an abbreviated revision by mistake and was correctly refused before
output/table creation. Relaunched with the exact full pinned HEAD. No gate changed.
Worker3 had zero running Spark jobs before launch.

**Physical preparation passed:** retained table
`local.experiment.integrity_sf1_20261014_0024`, snapshot 2963541948322332238,
6,001,215 rows, 16 files, 152,325,814 bytes. Parsed and loaded null checks both zero;
physical count and metadata record count agree; source SHA256 unchanged after load.
Original broken table and source data were preserved. No reset/drop/restart/cancel.

Evidence: `results/sf1_source_integrity_20261014_0024/` on worker3 includes exclusive
events log, frozen configuration, copied code and result. Audit saved in
`sf1_preparation_validation_2026-10-14.json`. Eleven statements completed without
failure. Six statement markers matched actual Spark REST job descriptions, including
source scan, CTAS and physical loaded scan. Catalog commands need not create jobs.
Marker-to-job attribution is now observed; actual completed-stage interval overlap
has not yet been validated. Do not infer treatment labels from client overlap.

Next ready unit: inspect REST stage timestamps/job-stage mapping, then preregister
and implement bounded control/concurrent-query/rewrite correctness on isolated
tables at recorded snapshots. Verify rewrite counts, unchanged row/result contents,
and stage overlap. No performance or scheduling benefit claim follows from this
source preparation. The copied-code package protects provenance but is not yet a
general immutable run-packaging interface for future long experiments.

## Outstanding resources/gates

### 00:39–00:47 IST: first query/rewrite pilot and repair

Committed/synced pilot and task-level overlap analyzer as 04de0a1; all five changed
file hashes matched. Protocol preserves measured source file count with explicit
repartition, runs four control/concurrent/post query identities, checks an exact
bidirectional full-row multiset, and requires actual task overlap. Query controls
use 60-second prior telemetry, not future samples. No legacy guard enabled.

First pilot retained at `results/sf1_correctness_pilot_20261014_0039/` on worker3.
An abbreviated revision launch was refused before effects; correct full revision
used for the physical run. This repeated command mistake is recorded; future launch
commands must use the full tool-observed HEAD, not a manually shortened value.

**Failed gate:** after successful physical rewrite output `[16,1,164550027]`,
control-session metadata still reported the original 16-file state. The pilot
refused acceptance and preserved all artifacts/table. Four concurrent query
results matched controls before that failure; 80 actual telemetry intervals logged.
Task overlap/full-multiset/post-query checks were not reached, so no treatment
labels or correctness acceptance follow.

Fresh-connection read-only audit found the committed new snapshot
3129288059524244264, one file, 6,001,215 records, 163,892,210 bytes. Explicit
REFRESH TABLE in that fresh session preserved those readings. Actual rewrite job
2063 was attributed by unique table description and group REWRITE-DATA-FILES-6.
Evidence indicates stale control-session relation caching after another Thrift
connection commits. Added a post-commit REFRESH TABLE before postconditions.
This invalidates session metadata; it does not rewrite/reset/drop data.

See `sf1_failed_pilot_validation_2026-10-14.json`. Next: separately preregister a new
destination/output and rerun all unchanged acceptance checks with the cache repair.
Do not relabel the failed pilot accepted or relax overlap/result/row gates.

No accepted SQL-arrival replay manifest or clean event-linked training dataset.
SF100 complete source verification and Alibaba member/mapping review are pending.
Publication claims and sufficient independent experiments remain future work.

### 00:54–00:58 IST: repaired pilot passed

Separately preregistered second pilot as commit 776c86d, with unchanged correctness
gates. Verified full local/worker3 HEAD, protocol and three physical module hashes;
worker3 had no active physical driver or running Spark job before launch. Used the
exact full tool-observed revision. Original failed table/output retained.

**Passed bounded physical correctness:** retained table
`local.experiment.integrity_pilot_20261014_0054`; snapshots
4510401085806035540 (before) and 7970187667229592262 (after).
Actual binpack result: 16 rewritten files, one added file, 164,550,027 rewritten
bytes; final file 163,892,210 bytes. Physical rows remain 6,001,215. Full bidirectional
EXCEPT ALL comparison across every column found zero differences, including duplicate
multiplicities. Four concurrent and four post-rewrite result sets matched controls.

All four queries had attributable successful Spark task-lifetime overlap with the
useful rewrite: Q0 0.383s, Q1 2.613s, Q2 0.436s, Q3 0.237s (union duration, not inflated
task-pair totals). Raw tasks/stages/jobs are preserved, not inferred from client
timestamps. This establishes overlapping task lifetimes, not simultaneous CPU
instruction execution or causal latency effects.

Independent recorded-artifact audit verified every overlap pair lies inside both
actual SUCCESS task lifetimes; every request completed without failed events; all
four control/concurrent/post results match. Eight pre-query 60-second windows met
declared coverage/freshness and preceded query submission. Minimum measured coverage
98.40%, maximum feature age 0.959s; 107 actual telemetry intervals, 26 completed
statements, 192 event records. See `sf1_correctness_validation_2026-10-14.json`.
Worker3 raw/frozen code/config/results: `results/sf1_correctness_pilot_20261014_0054/`.

This clears the bounded measurement-path pilot gate only. It does not supply enough
independent training blocks, a traced offered-load generator, 300-second window
validation, forecasting or a performance benefit claim. Legacy guards remain blocked.
The diagnostic simultaneous four-client pattern is not a causal single-query
compaction experiment. No failed evidence has been promoted.

Next ready independent unit: full Alibaba member schema/type/missing-value/timestamp
audit against the fetched publisher schema. It is running locally, using the actual
verified archive; no extraction/replay/mapping or fabricated input. Initial output
already flags batch-task schema issues, which must be reviewed before arrival mapping.

### 00:58–01:01 IST: full Alibaba audit completed

All six actual CSV members read fully; per-member byte hashes and column/type/
missing/time counters retained in `alibaba_member_validation_2026-10-14.json`.
Archive SHA256 rechecked before/after. Publisher schema saved verbatim in
`datasets/provenance/alibaba2017_schema.csv`; source URL and tool/schema hashes in
`alibaba_full_member_audit.md`. No member extraction, fabricated data or replay.

Batch task: 80,553 rows, no duplicate job/task keys, 80,386 positive and 167 negative
create timestamps; 9,017 rows missing CPU plans and 9,017 missing memory plans.
Batch instances: 16,094,656 trial records, job/task IDs each missing in 3,992,098.
Resource weighting and joins cannot silently fill these omissions. Usage members
also have genuine missing fields. Container-event rows all have nine fields against
the eight-column schema; sampled rows show a trailing empty field. The strict audit
preserves the width failure and does not pretend those rows have validated semantics.
Next unit must verify the ninth field is empty for every row before explicitly
normalizing this serialization detail. Positive task creations remain a candidate
for honestly labelled cluster-task-driven benchmark demand, never observed SQL arrivals.

### 01:09–01:15 IST: serialization resolved; long integrity checks started

Container-event serialization review verified every one of the 11,102 rows has
exactly one ninth, empty field. Explicitly removing only this CSV terminator yields
eight documented semantic fields with no required omissions or numeric violations.
10909 records are time-zero pre-trace creations; only 193 have positive timestamps;
all events are Create. The strict raw width-failure audit remains unchanged.
See `alibaba_serialization_validation_2026-10-14.json`; raw member hash agrees with
the strict audit. This does not create a replay or fill any data.

Full SF100 byte-hash/newline-count inventories started separately on local and
worker3 using committed tool 70d3863. No SF100 generator manifest is present.
Customer source already matches: 15,000,000 rows, 2,463,490,271 bytes and SHA256
874a0706b4bbcc83acbbf9bad94fa2d4cb7207febc0d39f45b982575893efb4c.
Remaining tables are still being scanned; do not mark full verification complete.
No latency pilot while these I/O scans run. Processes are observation-only and
must never be killed at cutoff. Pending outputs:
`docs/sf100_local_source_validation_2026-10-14.json` (local),
`results/sf100_remote_source_validation_2026-10-14.json` (worker3).
Tool sessions at launch: local 63555, remote 38441; inspect process/output state
before starting replacements if resuming in a new turn.

Next independent tasks: preserve exact positive task-create timestamps and identities
as a clearly labelled candidate (no mapping/zero-padding/compression/query mix), and
validate actual 60/300-second host telemetry windows during the real source I/O scan.
Batch-task last reported create time is 60181 seconds; do not invent a quiet tail
out to the publisher's nominal 24-hour period or claim complete event-free coverage.
