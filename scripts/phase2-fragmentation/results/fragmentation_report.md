# Phase 2B: Controlled Iceberg Table Fragmentation Report

This report compares the physical layouts of the healthy control table (`local.tpch.lineitem`) and the deliberately fragmented table (`local.experiment.lineitem_fragmented`).

**Control Table:** `local.tpch.lineitem`
**Fragmented Table:** `local.experiment.lineitem_fragmented`
**Analysis Time:** `2026-08-27T05:23:28.317050Z`

---

## 1. Storage Comparison Summary

| Metric | Control Table | Fragmented Table | Comparison / Delta |
| :--- | :--- | :--- | :--- |
| **Row Count** | 6,001,215 | 6,001,215 | Equal (Identical logical data) |
| **Number of Data Files** | 16 | 200 | **12.50x increase** |
| **Total Data Size** | 145.27 MB | 164.52 MB | 19.25 MB size delta |
| **Average File Size** | 9.08 MB | 842.34 KB | **11.04x smaller** |
| **Smallest File Size** | 8.30 MB | 840.63 KB | - |
| **Largest File Size** | 9.22 MB | 843.71 KB | - |
| **Number of Snapshots** | 1 | 1 | - |
| **Current Snapshot ID** | `8128630582928284438` | `6340323109717333721` | - |

**Fragmentation Factor:** `12.50` (ratio of fragmented files to control files).

---

## 2. Fragmented File Size Distribution
Below is the breakdown of the fragmented table's data files across standard size buckets:

| Size Bucket | File Count | Total Size |
| :--- | :---: | :--- |
| < 1 MB | 200 | 164.52 MB |
| 1-10 MB | 0 | 0 Bytes |
| 10-50 MB | 0 | 0 Bytes |
| 50-100 MB | 0 | 0 Bytes |
| 100-250 MB | 0 | 0 Bytes |
| 250 MB-1 GB | 0 | 0 Bytes |
| > 1 GB | 0 | 0 Bytes |


---

## 3. Fragmented Table Snapshot History
Below is the historical lineage of committed snapshots for the fragmented table:

| Snapshot ID | Parent Snapshot ID | Committed Time | Operation |
| :--- | :--- | :--- | :--- |
| `6340323109717333721` | `None` | `2026-08-27 10:53:15.666000` | **append** |


---

## 4. Physical Storage Layout Interpretation
The physical layout degradation has been **successfully introduced**:
- The file count increased from **16** to **200** (a fragmentation factor of `12.50x`).
- The average file size has decreased from **9.08 MB** to **842.34 KB**.
- The file size distribution is heavily concentrated in the smaller buckets (e.g. `< 1 MB`), whereas the control table files were entirely in the `1-10 MB` range.

This fragmented table serves as the exact treatment group (Phase 2B) for testing query performance degradation and subsequent recovery in later phases.
