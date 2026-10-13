# Isolated physical correctness preparation

This interface prepares a new SF1 lineitem table for harness validation. It cannot
authorize a trace replay, policy evaluation, training or publication result. The
legacy experiment guards remain in force.

`prepare_correctness_table.py` requires a checked JSON configuration and explicit
expected Git revision. It verifies source/provenance SHA256, counts every actual
source row and checks pipe/trailing-field structure. The schema is TPC-H lineitem
with decimal money/quantity and date fields, matching the existing loader. SQL CSV
parsing uses explicit types, FAILFAST, disabled quote interpretation and column
pruning; all columns are checked for nulls before any persistent table creation.

It refuses existing destinations and writes only a new `local.experiment.integrity_sf1_*`
table. Source and existing table files are untouched. It records configuration,
copied code, code hashes/revision, statement events/results/failures, and raw Spark
REST evidence. A host-local advisory lock prevents two instances of this preparation
tool running together; unrelated jobs must also be checked before launch.

Postconditions: physical loaded count and no-null checks, metadata record/file count,
snapshot ID, table properties, and source checksum unchanged after ingestion.
Failures preserve partial tables/artifacts. No retry into an existing directory/table,
reset, drop, service restart or process cancellation. Session SQL settings affect
only the dedicated connection.

Existing generator provenance is a historical generation manifest, not an independent
rebuild of dbgen. Spark REST payloads are preserved, but this step does not yet prove
job-marker attribution or actual control/treatment engine overlap.

Sources: [Spark 3.3.4 CSV options](https://archive.apache.org/dist/spark/docs/3.3.4/sql-data-sources-csv.html)
and [Iceberg 1.4.3 table DDL](https://iceberg.apache.org/docs/1.4.3/spark-ddl/).
