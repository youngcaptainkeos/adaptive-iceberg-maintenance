# Physical query/rewrite correctness pilot

This new interface retains all legacy publication/trace/model guards. Its protocol
permits only one bounded instrumentation check on verified SF1, not a policy result.

It clones the recorded prepared source snapshot into a new uniquely named table,
explicitly repartitioning to the measured source file count. This is a documented
layout intervention to obtain meaningful physical rewrite work; it is not natural
fragmentation or a generated workload trace. No existing table is reset or dropped.
The original source, clone and all snapshots are retained.

The four existing query identities run as controls, as concurrent diagnostic clients
with one binpack rewrite, and after rewriting. Canonical result comparison, physical
row count, metadata file-count conservation and a full bidirectional `EXCEPT ALL`
comparison check result/row preservation including duplicate multiplicities.

Independent one-second telemetry precedes queries with a 60-second historical window;
the protocol declares coverage/gap/freshness tolerances and warmup. No CPU/I/O fallback.
Host device counters do not establish per-query or NFS I/O attribution.

SQL markers identify query jobs. Iceberg rewrite actions replace SQL job groups with
`REWRITE-DATA-FILES` groups and table-specific descriptions. Because the new table
has exactly one maintenance request under this pilot's exclusive lock, matching
table/group and request interval attributes rewrite jobs. This mechanism must be
extended/reviewed before multiple simultaneous maintenance operations are supported.
Completed attributable stages must have no failed/killed tasks. Raw task-attempt
records establish overlapping task lifetimes, not merely overlapping stage spans.
Overlap duration is the union of intervals, not a sum inflated by task-pair count.
Task lifetimes do not prove simultaneous CPU instruction execution.

At least one query must overlap useful rewrite tasks for this bounded correctness
gate. Every query's individual overlap is reported; a non-overlapping query cannot
be labelled a compaction treatment. This pilot is not accepted training data and
does not waive the independent-experiment requirements in the trainer.

Sources: [Iceberg 1.4.3 rewrite procedure](https://raw.githubusercontent.com/apache/iceberg/apache-iceberg-1.4.3/docs/spark-procedures.md)
and [rewrite job attribution source](https://raw.githubusercontent.com/apache/iceberg/apache-iceberg-1.4.3/spark/v3.3/spark/src/main/java/org/apache/iceberg/spark/actions/RewriteDataFilesSparkAction.java).
