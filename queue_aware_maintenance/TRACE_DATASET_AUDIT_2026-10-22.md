# Trace and physical dataset binding audit — 22 October 2026

The fresh detached read-only audit passed. It establishes implementation fidelity to the declared hybrid benchmark, not reproduction of the original Snowflake SQL workload.

## What was independently checked

- Scanned all 2,760,971 rows of the selected-warehouse arrival export, checked its registered SHA256, extraction producer and upstream validation receipt hashes, unique identities, warehouse and chronological/numeric-ID tie order.
- Reconstructed every arrival in the half-open source interval 2018-02-27 20:40:00.286 UTC to 21:00:00.286 UTC. All 3,094 rows exactly matched the registered mapping, including IDs, warehouse, timestamp, integer nanosecond offset and round-robin template assignment. Template counts: 774/774/773/773.
- Streamed raw events from all eight physical episodes. Verified the unchanged schedule, complete offered/FIFO/completed identities, actual SQL template text/table/snapshot for all 24,752 requests, and two logical multiset-check intents per episode. Existing completed raw audits separately establish query-answer equality, task evidence, multiset-check results and exact full-drain response accounting.
- Independently checked current original `datasets/tpch/sf1/lineitem.tbl` and `manifest.txt` bytes on worker3 against the registered ingestion SHA256 values: both OK. Historical source ingestion checked 6,001,215 rows, parsed schema/null/trailing fields and loaded row counts; each physical run copied the pinned source snapshot and checked symmetric EXCEPT ALL before and after replay. No new SQL or table mutation was issued for this audit.

## Timing findings and limits

Scheduled offsets are preserved exactly; physical thread release is not instantaneous. Across runs, median release lateness was 3.389–31.960 ms, per-run p99 253.747–508.956 ms, and the overall maximum 1,162.967 ms. These delays are not subtracted from response time. They are another reason not to interpret the small 60-second intervention contrasts as a demonstrated causal gain.

The four SQL statements are custom aggregations/filters on generated TPC-H SF1 lineitem data, not the full official TPC-H query suite. Original Snowset SQL identities, query costs and correlations between arrival time and query complexity are not recovered: the benchmark explicitly assigns templates cyclically. This audit starts at the hash-bound arrival CSV; the full 69,182,074-row raw Parquet/archive validation is historical and was not repeated. Generator provenance is recorded, not independently rebuilt; publisher cryptographic authenticity is not independently established. Serial foreground execution and telemetry/preparation overhead remain part of the benchmark.

## Reproducible evidence

- Audit source revision: `90f59d3ae987f33a29f08a7a34349669daf72600`; script SHA256 `15639d0bc1ad131e48337620c3b14276aa4ae9b9582582229bdb5dd93fc116db`.
- Physical source runtime remains frozen at `790f4f89d1d8cbe821903af79392134bfb1c6bbb`; protocol SHA256 `dbfab850c4eb100caff416515f58756451ebca0d574023ae96289e03c463d102`.
- Result: `results/trace_dataset_binding_20261022/audit/result.json`, SHA256 `b3358b7c4f652d2397f874fdbe53e81f1aa14472b12a478319ca97efbf23576b`; log `results/trace_dataset_binding_20261022/audit.log`.
- Wrapper/client PIDs 1158443/1158444; completed 03:06:00 UTC (08:36 IST), no new SQL. Failure-alert wrapper used; no failed test or fabricated validation data.
- Original-dataset check: `results/trace_dataset_binding_20261022/dataset_checksums.sha256` and `dataset_checksum.log`, separate detached failure-alert wrapper.

No physical replay was rerun and no historical result was changed. Next gate: independent workload/SQL-mix representativeness and repeatability, including release/instrumentation overhead, before any useful scheduler or novelty claim.
