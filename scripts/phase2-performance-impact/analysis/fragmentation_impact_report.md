# Apache Iceberg Small-File Fragmentation Performance Impact Report

This report evaluates the performance difference between the healthy control table (`local.tpch.lineitem`) and the deliberately fragmented table (`local.experiment.lineitem_fragmented`).

**Control Table:** `local.tpch.lineitem` (16 consolidated data files, ~9.08 MB average)
**Fragmented Table:** `local.experiment.lineitem_fragmented` (200 fragmented data files, ~842 KB average)
**Analysis Time:** `2026-08-27T05:49:59.407649Z`

---

## 1. Executive Summary
Surprisingly, the experimental data shows a **performance improvement** after fragmentation. The total mean execution time decreased from **13.811 seconds** (baseline) to **8.992 seconds** (fragmented), a speedup of **1.54x**. This could be due to increased query parallelism on the repartitioned dataset, or local caching effects.

---

## 2. Workload Performance Comparison
Below is the comparison of average runtimes (seconds) for each query:

| Query | Baseline Mean Time | Fragmented Mean Time | Absolute Difference | Slowdown Factor | Percentage Change |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Q1** | 8.111 s | 3.240 s | -4.871 s | 0.40x | -60.05% |
| **Q3** | 1.300 s | 0.838 s | -0.462 s | 0.64x | -35.54% |
| **Q6** | 0.406 s | 0.499 s | 0.093 s | 1.23x | +22.92% |
| **Q12** | 0.738 s | 0.778 s | 0.040 s | 1.05x | +5.40% |
| **Q14** | 0.557 s | 0.500 s | -0.057 s | 0.90x | -10.22% |
| **Q18** | 2.699 s | 3.137 s | 0.438 s | 1.16x | +16.23% |


---

## 3. Storage Layout Comparison
- **Control Table Data Files:** 16 files (Average size: 9.08 MB)
- **Fragmented Table Data Files:** 200 files (Average size: 842.34 KB)
- **Fragmentation Factor:** **12.50x** increase in file count.

---

## 4. Run Details
Below are the individual statement runtimes for all 3 repetitions:

| Run ID | Query | Statement ID | Status | Duration |
| :--- | :--- | :--- | :--- | :--- |
| `2026_08_27_05_49_32_068` | **Q1** | `query1_fragmented.sql_0` | SUCCESS | 3.750 s |
| `2026_08_27_05_49_32_068` | **Q3** | `query3_fragmented.sql_0` | SUCCESS | 0.927 s |
| `2026_08_27_05_49_32_068` | **Q6** | `query6_fragmented.sql_0` | SUCCESS | 0.773 s |
| `2026_08_27_05_49_32_068` | **Q12** | `query12_fragmented.sql_0` | SUCCESS | 0.843 s |
| `2026_08_27_05_49_32_068` | **Q14** | `query14_fragmented.sql_0` | SUCCESS | 0.497 s |
| `2026_08_27_05_49_32_068` | **Q18** | `query18_fragmented.sql_0` | SUCCESS | 3.162 s |
| `2026_08_27_05_49_32_068` | **Q1** | `query1_fragmented.sql_0` | SUCCESS | 3.017 s |
| `2026_08_27_05_49_32_068` | **Q3** | `query3_fragmented.sql_0` | SUCCESS | 0.752 s |
| `2026_08_27_05_49_32_068` | **Q6** | `query6_fragmented.sql_0` | SUCCESS | 0.359 s |
| `2026_08_27_05_49_32_068` | **Q12** | `query12_fragmented.sql_0` | SUCCESS | 0.743 s |
| `2026_08_27_05_49_32_068` | **Q14** | `query14_fragmented.sql_0` | SUCCESS | 0.515 s |
| `2026_08_27_05_49_32_068` | **Q18** | `query18_fragmented.sql_0` | SUCCESS | 3.177 s |
| `2026_08_27_05_49_32_068` | **Q1** | `query1_fragmented.sql_0` | SUCCESS | 2.953 s |
| `2026_08_27_05_49_32_068` | **Q3** | `query3_fragmented.sql_0` | SUCCESS | 0.835 s |
| `2026_08_27_05_49_32_068` | **Q6** | `query6_fragmented.sql_0` | SUCCESS | 0.366 s |
| `2026_08_27_05_49_32_068` | **Q12** | `query12_fragmented.sql_0` | SUCCESS | 0.749 s |
| `2026_08_27_05_49_32_068` | **Q14** | `query14_fragmented.sql_0` | SUCCESS | 0.487 s |
| `2026_08_27_05_49_32_068` | **Q18** | `query18_fragmented.sql_0` | SUCCESS | 3.073 s |


---

## 5. Factors Influencing Measurements
When interpreting these results, several environmental factors should be considered:
1. **JVM Warm-up**: The initial executions (Repetition 1) typically incur JIT compilation and metadata class loading overhead.
2. **Spark Catalyst Planning**: Spark caches catalog metadata and logical query plans, which speeds up subsequent repetitions.
3. **OS Filesystem Cache**: The local OS caches recently read Parquet file footers and dictionary pages in memory, reducing physical disk I/O.
4. **Local Hardware Jitter**: CPU throttling and background processes on the local machine can lead to run-to-run variability.

This performance baseline provides the treatment reference (Phase 2C) to contrast against subsequent compaction and maintenance phases.
