# SF10 failure and registered scratch repair — 25 October 2026

The deferred SF10 attempt actually launched on worker3 on 24 October at
18:52:47 UTC, after the four-arm queue comparison finished. It ended failed at
19:04:10 UTC. This supersedes the earlier review's waiting/running status; it
does not supersede the failed outcome. No model weights were produced.

## Observed failure and retained evidence

`results/three_model_sf10_plan_capability_20261024_02/result.json` has status
`failed_preserved_no_retry`, SHA256
`45ea9f3d9cce5dc0ecc9802646e406d4abab61777ec6e82eb5d7b05dab61ef05`.
Admission, real dbgen generation and independent typed/relational/reference
validation passed. Preparation failed; plan/query and final audit were unattempted.
The original tables, raw files, partial preparation and failure logs are retained.

All eight generated tables passed lexical/type/null/terminator checks, primary
key checks and eight foreign-key checks. Actual lineitem cardinality is 59,986,052
rows, not an assumed fixed scale count. Six declared custom SQL reference outputs
were computed with DuckDB 1.5.6. This is a controlled benchmark, not original
Snowflake SQL or an official 22-query TPC-H score.

Seven Spark table ingestions passed their exact row comparisons. The lineitem
table was created and its row count matched, but its full-row bidirectional
EXCEPT ALL comparison failed with `java.io.IOException: No space left on device`
in Spark's UnsafeSorterSpillWriter/UnsafeExternalSorter. Lineitem ingestion is
therefore **unaccepted**; neither counts alone nor other successful tables repair
that missing gate. Failure alert receipt reports HTTP200; parent also alerted.

The original admission checked free capacity on the data disk and host RAM, but
missed Spark's independent spill disk. Original Spark3.3.4/local[16]/16g service
10000/UI4040 had Java temporary directory `/tmp` and no explicit spark.local.dir.
Spark defaults its local scratch to `/tmp`; at diagnosis the system filesystem
had about21.8GB free while the data filesystem had about445.7GB free. This is a
resource admission defect, not evidence of wrong source rows. Reference:
[official Spark3.3.4 configuration](https://archive.apache.org/dist/spark/docs/3.3.4/configuration.html).

Small receipts/logs/raw statement events have been copied to the client at the
same relative output path, excluding `reference.duckdb` and spill directories.
The2.83GB reference database and generated raw source remain authoritative on
worker3; a complete raw-data client mirror is not claimed.

## New bounded recovery registration

`three_model_maintenance/protocols/sf10_scratch_recovery_20261025.json` and
`experiments/sf10_scratch_recovery.py` implement one engineering repair:

1. Wait for all four existing shared resource locks. Waiting does no source scan,
   SQL, fitting or service startup. Latest lock admission05:00UTC/10:30IST;
   no new stage/SQL after07:00UTC/12:30IST; active work finishes naturally.
2. Pin the original failed terminal receipt and successful generation/reference
   receipts; rehash all eight actual source files. Reuse successful source and
   independent query references explicitly, without claiming a rerun or reusing
   failed ingestion.
3. Admit32GiB available RAM,100GiB free data disk and5GiB free system disk, then
   launch a **new persistent** Spark Thrift service10001/UI4050. Keep the original
   service unchanged. Same Spark3.3.4/local[16]/16g and Iceberg1.4.3, dedicated
   Derby directory, data-disk `spark.local.dir`/SPARK_LOCAL_DIRS and Java tmp.
   Inspect actual REST environment and TCP readiness before any SQL.180s bounded
   startup, no automatic restart. Resource floors are budgets, not peak guarantees.
4. Write the actual app ID/endpoint and source registration before physical SQL.
   Use fresh03tables and repeat unchanged eight-table ingestion, exact full-row
   multiset gates, six actual pre-execution plan/query pairs before and after a
   useful rewrite, exact reference results, rewrite preservation and raw audit.
5. Each physical stage and persistent service use failure-alert wrappers. Logs,
   PID, terminal status and failures remain. No kill/restart/delete on any exit.

The new backend is a changed execution configuration; do not compare its timing
to the old backend as a treatment effect. Startup/source/AST checks do not validate
plans or models. Original02 remains failed; fresh03 acceptance depends on actual
physical gates, with no favorable retry or relaxed comparison.

Expected duration after resource admission: roughly30–120minutes, uncertain
because full exact comparison spill dominates. This is capability work only.
Matched A/B histories, independent splits, uncertainty, C forecasting, SF100
resource admission and scheduling-benefit evaluation remain separate gates.

## Launch and actual results

Pending source preflight, targeted commit/synchronization and actual detached
launch. No fresh03service, SQL or successful capability is claimed by this entry.

25Oct01:42UTC coordination refinement before launch: the newly registered queue
complexity unit is starting and may wait for a backup before holding its locks.
The SF10 waiter now requires that exact unit's terminal receipt
(`results/queue_complexity_maintenance_20261025/result.json`, protocol
`ade885ec56edb671466828cbc36e648272b550efdd17d7f8e7b473dbfc1ae3a2`)
**and** resource-lock release. Both successful and failed terminal outcomes allow
this independent capability repair; there is no favorable-science outcome gate.
This avoids racing a parent that has not yet acquired locks. Original source-only
preflight at01:39UTC logged frozen AST/source/schema/generator/backend-digest PASS;
no SQL/data scans/service startup. Its wrapper2192932 was observed ended; the
failure-only wrapper emits no success receipt, so no recorded exit-status claim
is inferred. The added metadata wait requires a new frozen-source check.
