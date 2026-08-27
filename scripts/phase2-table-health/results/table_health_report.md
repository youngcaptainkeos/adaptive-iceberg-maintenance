# Apache Iceberg Table Health Report (Baseline)

This report documents the physical storage characteristics of the `local.tpch.lineitem` Iceberg table before any fragmentation experiments.

**Table Full Identifier:** `local.tpch.lineitem`
**Analysis Time:** `2026-08-27T03:59:12.896822Z`

---

## 1. Summary Statistics
- **Logical Row Count:** 6,001,215
- **Number of Data Files:** 16
- **Total Data Size:** 145.27 MB
- **Average Data File Size:** 9.08 MB
- **Median Data File Size:** 9.12 MB
- **Smallest Data File:** 8.30 MB
- **Largest Data File:** 9.22 MB
- **Number of Snapshots:** 1
- **Current Snapshot ID:** `8128630582928284438`

---

## 2. File Size Distribution
Below is the breakdown of files classified by size buckets:

| Size Bucket | File Count | Total Size |
| :--- | :---: | :--- |
| < 1 MB | 0 | 0 Bytes |
| 1-10 MB | 16 | 145.27 MB |
| 10-50 MB | 0 | 0 Bytes |
| 50-100 MB | 0 | 0 Bytes |
| 100-250 MB | 0 | 0 Bytes |
| 250 MB-1 GB | 0 | 0 Bytes |
| > 1 GB | 0 | 0 Bytes |


---

## 3. Snapshot History
Below is the historical lineage of committed snapshots:

| Snapshot ID | Parent Snapshot ID | Committed Time | Operation |
| :--- | :--- | :--- | :--- |
| `8128630582928284438` | `None` | `2026-08-27 00:11:48.070000` | **append** |


---

## 4. List of Data Files
Below are the individual data files comprising the active table state:

| File Name | Record Count | File Size |
| :--- | :---: | :--- |
| `00000-22-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 380,414 | 9.22 MB |
| `00001-23-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 379,576 | 9.19 MB |
| `00002-24-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 378,504 | 9.17 MB |
| `00003-25-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,624 | 9.11 MB |
| `00004-26-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,569 | 9.11 MB |
| `00005-27-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,664 | 9.12 MB |
| `00006-28-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,495 | 9.11 MB |
| `00007-29-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,535 | 9.11 MB |
| `00008-30-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,585 | 9.11 MB |
| `00009-31-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,650 | 9.11 MB |
| `00010-32-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,566 | 9.12 MB |
| `00011-33-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,625 | 9.12 MB |
| `00012-34-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,724 | 9.12 MB |
| `00013-35-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,568 | 9.12 MB |
| `00014-36-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 376,573 | 9.12 MB |
| `00015-37-0c25e7d5-a731-4374-913e-88dfd73170a0-00001.parquet` | 343,543 | 8.30 MB |


---

## 5. Storage State Interpretation
The table is currently in a **healthy, consolidated physical storage state**. It consists of 16 relatively large data files with an average size of 9.08 MB. This layout is optimal for scan-heavy analytical queries because it avoids the overhead of managing millions of tiny files.

These measurements will serve as the exact baseline (Phase 2A) to compare against future layout degradation (small-file insertions) and subsequent compaction/maintenance phases.
