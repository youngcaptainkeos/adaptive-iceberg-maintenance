# Dataset and resource readiness

Updated: 2026-10-13. Evidence: `dataset_resource_inventory_2026-10-13.json`.

## Verdict

We have sufficient benchmark data and compute to begin reliable single-node
physical experiments. We do **not** yet have all validated datasets, evidence,
and environment guarantees needed for the intended publication. No new experiment
was launched in this inventory step.

## What is available and what is verified

| Asset | Evidence | Readiness |
| --- | --- | --- |
| TPC-H SF1 | All eight source tables on both machines; freshly counted rows and SHA256 agree with existing manifest and each other | Verified bytes/cardinality; generator/build provenance recorded in existing manifest |
| TPC-H SF100 | All eight source files on both machines; initial Iceberg metadata contains expected large-scale cardinalities | Available; complete source checksum/row-count manifest still needed |
| Large Iceberg lineitem | Initial metadata reports 600037902 records; inspected later snapshot reports 600039613 after writes | About 600 million, not the 60 million repeatedly claimed in drafts; metadata observation, not a newly executed COUNT query |
| Alibaba 2017 archive | Same SHA256 locally/remotely; gzip integrity passes; tar members readable; server_usage member read fully | Real-looking trace artifact, but publisher provenance not yet authenticated |
| Google workload CSV | Default mapper input absent on both machines | Missing; synthetic fallback is unacceptable |
| Publication training data | Historical runs exist, with known leakage/label/schema and sample-size problems | Not ready for the new model/forecast claims |
| Long independent workload traces | Alibaba server_usage covers 39600–82500 seconds across 1310 server IDs and is not time-sorted | Useful candidate after provenance/schema validation; does not establish multi-day periodicity |

Alibaba archive SHA256 is
`b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66`.
The publisher's repository lists a different checksum for `trace_201708.tgz`.
Our file is named `alibaba-trace-2017.tar.gz`; a mismatch could reflect different
packaging/version, so it proves neither corruption nor authenticity. Resolve its
download origin before using it as a verified trace. The CPU/memory time series
is not itself a SQL arrival or write-ingestion trace.

Publisher references inspected:

- [Alibaba 2017 dataset documentation](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/README2017.md)
- [Alibaba schema](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/schema.csv)
- [Publisher checksum](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/SHA256SUM)

## Compute and runtime

Observed worker3 resources:

- Intel Core i7-6950X: 10 physical cores, 20 logical CPUs. Prior Xeon wording is
  unsupported by the actual CPU inventory.
- About 62.6 GiB total RAM (nominal 64 GB); about 41.9 GiB available at inspection.
- About 507 GiB available on the mounted project filesystem. This is observed
  free capacity, not a reservation or sustained storage-bandwidth measurement.
- Spark 3.3.4; Iceberg 1.4.3 jar present and hashed. PyHive, pandas, numpy,
  scikit-learn, psutil, PySpark and fastavro are installed.
- Actual Spark process uses `local[16]` with a 16 GiB driver heap. This is one
  machine with local parallelism, not a distributed multi-node cluster.
- Actual Java is OpenJDK 8, while documentation states Java 11. Lock and verify
  the environment in P1; do not change the active process during inventory.

CPU capacity is sufficient for classical forecasting/cost models and initial
interference studies. GPU acceleration is not a prerequisite. Single-machine
results alone do not establish multi-node or cross-hardware generalization.
Confirm dedicated/reserved access, background tenant load, experiment duration,
storage throughput and quota before long runs. Existing free RAM/storage does
not guarantee reproducible isolation or room for every retained snapshot.

## Missing items and next actions

1. Reconstruct the Alibaba download provenance or acquire a publisher-verified
   subset. Validate timestamps, units, missing values and sorting for every used
   trace member. Never relabel a CPU curve as observed SQL demand.
2. Obtain a real database arrival trace for forecast validation and trace-driven
   benchmark replay. A candidate is Snowset, whose published data contains query
   timing/resource records over 14 days. Its schema includes createdTime but no
   SQL-text replay field: any mapping to TPC-H query templates must be explicit
   and justified, not represented as replay of original queries.
   [Dataset documentation](https://github.com/resource-disaggregation/snowset)
   and [schema](https://github.com/resource-disaggregation/snowset/blob/master/schema.md).
3. Google cluster traces are another genuine demand/resource source but describe
   cluster jobs, not original database SQL. They do not automatically supply an
   ingestion trace or maintenance counterfactual labels.
   [Google trace documentation](https://github.com/google/cluster-data/blob/master/ClusterData2019.md).
4. Complete the SF100 generation/checksum/cardinality manifest, then identify
   immutable source snapshots and data locations for table resets.
5. Repair the physical harness, then collect independent compaction/no-compaction
   observations with matched states and offered workloads. External traces cannot
   replace measuring Iceberg action costs on our actual system.
6. Secure a second environment/configuration for generalization, or scope claims
   explicitly to tested hardware while varying data size and resource budgets.

No large external download was started, no source dataset was regenerated, and
no active Spark table/process was changed. Existing pilot output remains
diagnostic/failed-validation evidence rather than publication success.

## Source reconciliation result and audit

Preserved 327 remote project source/configuration files in the isolated
`archive/worker3_handover_2026-10-13/` tree, including 277 absent locally and four
different versions. Both local and remote versions of each conflict are preserved.
SHA256/size verification passed for all 327 files and all four local conflicts.
Credential-pattern inspection found no candidates before staging this source archive.

No historical code was imported into the active execution path. This is source
preservation, not certification of old experiments. Full raw evidence backup,
provenance classification and active-source conflict resolution remain pending.

The full archive is retained locally on `codex/local-handover-snapshot`. Automatic
approval review rejected its GitHub upload as a potentially sensitive bulk export.
Only the routine readiness documents and verification tool are published/synced
at this step; full archive upload awaits explicit user approval. Do not claim that
the archive is backed up to GitHub or present in the remote archive path yet.

Current publication-gate status: **BLOCKED**. Evidence preservation and inventory
are completed bounded tasks; missing data/provenance and measurement quality must
be resolved before we train the intended forecasting scheduler.
