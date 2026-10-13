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

No accepted SQL-arrival replay manifest or clean event-linked training dataset.
SF100 complete source verification and Alibaba member/mapping review are pending.
Publication claims and sufficient independent experiments remain future work.
