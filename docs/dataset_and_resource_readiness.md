# Dataset and resource readiness

Updated: 2026-10-14. Initial evidence: `dataset_resource_inventory_2026-10-13.json`;
subsequent evidence: `overnight_review_2026-10-14.md` and linked validation artifacts.

## Verdict

We have sufficient benchmark data and compute to begin reliable single-node
physical experiments. We do **not** yet have all validated datasets, evidence,
and environment guarantees needed for the intended publication. No new experiment
was launched in this inventory step.

## What is available and what is verified

| Asset | Evidence | Readiness |
| --- | --- | --- |
| TPC-H SF1 | All eight source tables on both machines; freshly counted rows and SHA256 agree with existing manifest and each other | Verified bytes/cardinality; generator/build provenance recorded in existing manifest |
| TPC-H SF100 | All eight files match across both machines by fresh full-byte SHA256, bytes and newline row counts: 114641618862 bytes, lineitem 600037902 actual rows | Bytes/cardinality verified; typed parsing, relational checks and generator/build provenance still needed |
| Large Iceberg lineitem | Initial metadata reports 600037902 records; inspected later snapshot reports 600039613 after writes | About 600 million, not the 60 million repeatedly claimed in drafts; metadata observation, not a newly executed COUNT query |
| Alibaba 2017 archive | Same SHA256 locally/remotely; publisher size/CRC64 match; all six members fully audited against publisher schema | Missing resource/identity fields recorded; container trailing-empty-field serialization explicitly validated; SQL workload mapping still absent |
| Snowset complete source | Full archive mirrored with equal SHA256; gzip/tar and all values from 2,000 regular Parquet files validated: 69,182,074 unique query IDs, 2,051 warehouses, approximately 13.34 observed days | Accepted arrival source only. No SQL text, ingestion or Iceberg action costs. Publisher does not provide an independent cryptographic checksum; recovered-range receipt limits retained |
| Snowset selected arrival cohort | Training-only warehouse selection; 2,760,971 actual arrivals, 19,211 complete minute bins; independent timestamp/identity/bin audit and both-host hashes passed | Original timing preserved; one warehouse and short history. Partial tail retained separately; no padded quiet tail or approved SQL mapping |
| Arrival forecast diagnostic | Past-only Poisson count model versus persistence/day/week baselines; saved prediction/truth/split/metric audit passed | Lower held-out count MAE on one warehouse; no uncertainty, server-load, scheduling or Model C acceptance |
| Verified workload replay | Historical Google CSV absent; no approved observed replay manifest exists | Missing; synthetic fallback removed by the fail-closed step |
| Publication training data | Historical runs exist, with known leakage/label/schema and sample-size problems | Not ready for the new model/forecast claims |
| Long independent workload traces | Alibaba server_usage covers 39600–82500 seconds; 80386 positive task creations preserved at times 5–60181. Snowset separately provides validated SQL-query arrival timestamps | Alibaba remains a cluster-event candidate; Snowset has limited temporal depth and no original SQL mapping |

The overnight work changed availability, not publication readiness. Snowset source,
cohort and forecast evidence is recorded in `snowset_complete_source_validation_2026-10-14.json`,
`snowset_independent_cohort_audit_2026-10-14.json` and
`arrival_forecast_diagnostic_review_2026-10-14.json`. Actual SF1 matched Q1/Q0/Q2/Q3
episodes passed timing/window/task/result/row checks; strengthened Q2 additionally
passed fresh pre-action state binding, as did Q3. They remain diagnostic episodes
rather than independent cost-training data. Q3 ended naturally and all four
episodes passed strengthened raw correctness export checks.

Alibaba archive SHA256 is
`b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66`.
The publisher's repository lists a different checksum for `trace_201708.tgz`.
Our file is named `alibaba-trace-2017.tar.gz`; a mismatch could reflect different
packaging/version, so it proves neither corruption nor authenticity. Its original
download history remains unknown. A subsequent direct check of the archive URL
linked by the publisher resolved the current-object integrity question: HTTPS
returned Content-Length 243321159 and x-oss-hash-crc64ecma 2700699146184863613;
the local file matches both exactly. The ETag is multipart, so it must not be
compared to the local MD5. See `alibaba_trace_reverification_2026-10-13.json`.
CRC64 is an integrity check, not an independent cryptographic authenticity proof.
No dataset was downloaded in this check: only HTTP headers were fetched.

The archive contains batch_task, batch_instance, server_event, server_usage,
container_event and container_usage CSVs. Its recorded modification time matches
the publisher object's February 27, 2023 Last-Modified header; that does not prove
the local download date. Retrieved Antigravity records show transfer to worker3,
not the original acquisition. The user's unsuccessful download recollection is
preserved; it cannot be reconciled to an acquisition event from the evidence yet.
The CPU/memory time series is not itself a SQL arrival or write-ingestion trace.

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

1. Record the publisher URL and successful current-object size/CRC check; preserve
   the unknown acquisition history. Validate timestamps, units, missing values and
   sorting for every used trace member. Never relabel a CPU curve as observed SQL
   demand. This file's presence does not mean the Google-mapper experiment used it.
2. Snowset acquisition and complete arrival validation are finished. Register an
   explicit training-only arrival-to-benchmark-SQL mapping and queue accounting
   before trace-driven physical replay. The actual observed source interval is
   approximately 13.34 days; do not pad it to a nominal 14-day quiet endpoint.
   Its schema includes createdTime but no SQL-text replay field: mapping to TPC-H
   templates must be justified, not represented as replay of original queries.
   [Dataset documentation](https://github.com/resource-disaggregation/snowset)
   and [schema](https://github.com/resource-disaggregation/snowset/blob/master/schema.md).
3. Google cluster traces are another genuine demand/resource source but describe
   cluster jobs, not original database SQL. They do not automatically supply an
   ingestion trace or maintenance counterfactual labels.
   [Google trace documentation](https://github.com/google/cluster-data/blob/master/ClusterData2019.md).
4. Complete SF100 generator provenance and typed/relational validation; bytes and
   source row counts already match both machines. Use new isolated experiment
   tables and retain existing data/snapshots; no table reset is authorized.
5. Finish fourth-query pilot audit, then register variance, common-horizon action
   comparison and independent experiment splits. Reliable measurement primitives
   exist; publication replay and accepted cost schema remain unimplemented.
   External traces cannot replace actual Iceberg action-cost measurements.
6. Secure a second environment/configuration for generalization, or scope claims
   explicitly to tested hardware while varying data size and resource budgets.

The original inventory started no large external download and regenerated no source;
later authorized overnight Snowset acquisition is recorded above. No service was
shut down, restarted or cancelled. Existing tables remain preserved. Pilot output remains
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

Subsequent implementation: `docs/fail_closed_experiment_contract.md` records removal
of the trace/training fallbacks and retirement of unvalidated execution paths.
The raw Alibaba archive still needs a reviewed transformation and workload mapping;
its integrity check does not supply a ready-to-run experiment manifest.
