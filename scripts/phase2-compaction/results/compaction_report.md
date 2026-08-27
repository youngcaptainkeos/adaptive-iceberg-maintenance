# Apache Iceberg Compaction & Storage Recovery Report

This report evaluates the physical storage changes and validates the data integrity before and after calling the Iceberg `rewrite_data_files` procedure on the fragmented table `local.experiment.lineitem_fragmented`.

**Control Table:** `local.tpch.lineitem`
**Fragmented/Compacted Table:** `local.experiment.lineitem_fragmented`
**Analysis Time:** `2026-08-27T06:17:44.443876Z`

---

## 1. Summary Metrics Comparison

| Metric | Fragmented Before | After Compaction | Change |
| :--- | :--- | :--- | :--- |
| **Row Count** | 6,001,215 | 6,001,215 | 0 (0.00% change) |
| **Data Files** | 200 | 1 | -199 files |
| **Total Size** | 164.52 MB | 156.34 MB | -8572685 Bytes size delta |
| **Average File Size** | 842.34 KB | 156.34 MB | 155.52 MB size change |
| **Minimum File Size** | 840.63 KB | 156.34 MB | - |
| **Maximum File Size** | 843.71 KB | 156.34 MB | - |
| **Snapshot Count** | 1 | 2 | 1 new snapshots |

---

## 2. Physical Layout Improvements

- **File-Count Reduction Factor:** **200.00x** reduction (from **200** files down to **1** files).
- **Average File-Size Change:** Average file size increased from **842.34 KB** to **156.34 MB** (an increase of **190.06x**).

---

## 3. Snapshot Analysis & Lineage

The compaction operation triggered a `replace` operation in Apache Iceberg, committing a new snapshot that references the consolidated files and marks the fragmented files as dead/deleted in the table's metadata:

- **Pre-Compaction Snapshot ID:** `6340323109717333721` (Snapshot Count: 1)
- **Post-Compaction Snapshot ID:** `8782426708470012666` (Snapshot Count: 2)

This represents a clean physical partition layout replacement while keeping historic lineage completely accessible via Time Travel.

---

## 4. Control Table Protection Verification

We explicitly verified that the control table `local.tpch.lineitem` was not modified in any way:
- **Logical Row Count:** 6,001,215 (Expected: 6,001,215)
- **Active Data Files:** 16 (Expected: 16)
- **Snapshot ID:** `8128630582928284438` (Expected: 8128630582928284438)
- **Verification Status:** **SUCCESS / UNTOUCHED**

---

## 5. Compaction Validation Results

- **Logical Row Count Check:** SUCCESS
- **Schema Consistency Check:** SUCCESS
- **Aggregate Checksum Verification:** SUCCESS
- **Control Table Isolation Check:** SUCCESS

**COMPACTION DATA INTEGRITY: PASSED**

