# Workload Characterization Report

This report documents the baseline performance characterization of the TPC-H workload on our local Iceberg catalog, serving as the experimental control group for Phase 1B.

**Experiment Run ID:** `2026_08_27_03_24_52_570`
**Generated At:** `2026-08-27T03:25:42.015346Z`

---

## 1. Query Classifications and Profiles
The selected query set comprises six representative TPC-H queries providing a diverse mix of operations:

*   **Q1 (Scan-Heavy / Aggregation-Heavy)**: Large-scale table scan on the `lineitem` table with groupings and aggregate computations (sums, averages, counts). Very CPU and I/O intensive.
*   **Q3 (Join-Heavy / Aggregation-Heavy)**: Performs a three-way join across `customer`, `orders`, and `lineitem` with filter criteria and groupings, limiting output to the top 10 rows.
*   **Q6 (Scan-Heavy / Filtering-Heavy)**: Scan of `lineitem` with multiple highly selective range filters. Tests the efficiency of data skipping and predicate pushdowns.
*   **Q12 (Join-Heavy / Aggregation-Heavy / Filtering)**: Performs a join between `orders` and `lineitem` with complex conditional aggregates (`CASE` statements) and selective filtering on shipping mode.
*   **Q14 (Scan-Heavy / Join-Heavy / Case Aggregation)**: Joins `lineitem` and `part` within a specific date range, calculating promotional revenue using conditional logic.
*   **Q18 (Join-Heavy / Large Grouping / Subquery)**: Employs an IN-subquery with a `GROUP BY HAVING` clause on `lineitem`, joined back with `customer` and `orders`. This is a computationally intensive query involving large volume aggregations.

---

## 2. Baseline Performance Results
Below is the summary of the execution statistics across all repetitions:

| Query | Count | Successes | Failures | Mean (s) | Median (s) | Min (s) | Max (s) | StdDev (s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Q1 | 3 | 3 | 0 | 7.888 | 7.829 | 7.638 | 8.197 | 0.284 |
| Q3 | 3 | 3 | 0 | 1.611 | 1.336 | 1.276 | 2.222 | 0.529 |
| Q6 | 3 | 3 | 0 | 0.529 | 0.511 | 0.434 | 0.643 | 0.105 |
| Q12 | 3 | 3 | 0 | 0.998 | 0.886 | 0.808 | 1.299 | 0.264 |
| Q14 | 3 | 3 | 0 | 0.726 | 0.617 | 0.595 | 0.968 | 0.209 |
| Q18 | 3 | 3 | 0 | 4.602 | 3.704 | 3.420 | 6.683 | 1.807 |


---

## 3. Detailed Execution Records
Below are the individual statement execution records:

| Query | Repetition / Statement | Status | Start Time | End Time | Duration (s) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Q1 | `query1.sql_0` | **SUCCESS** | `2026-08-27T03:24:52.587805Z` | `2026-08-27T03:25:00.784428Z` | 8.197 |
| Q3 | `query3.sql_0` | **SUCCESS** | `2026-08-27T03:25:00.792780Z` | `2026-08-27T03:25:03.014587Z` | 2.222 |
| Q6 | `query6.sql_0` | **SUCCESS** | `2026-08-27T03:25:03.014818Z` | `2026-08-27T03:25:03.657606Z` | 0.643 |
| Q12 | `query12.sql_0` | **SUCCESS** | `2026-08-27T03:25:03.657846Z` | `2026-08-27T03:25:04.956482Z` | 1.299 |
| Q14 | `query14.sql_0` | **SUCCESS** | `2026-08-27T03:25:04.956695Z` | `2026-08-27T03:25:05.924223Z` | 0.968 |
| Q18 | `query18.sql_0` | **SUCCESS** | `2026-08-27T03:25:05.924525Z` | `2026-08-27T03:25:12.606992Z` | 6.682 |
| Q1 | `query1.sql_0` | **SUCCESS** | `2026-08-27T03:25:12.701124Z` | `2026-08-27T03:25:20.338854Z` | 7.638 |
| Q3 | `query3.sql_0` | **SUCCESS** | `2026-08-27T03:25:20.339046Z` | `2026-08-27T03:25:21.675325Z` | 1.336 |
| Q6 | `query6.sql_0` | **SUCCESS** | `2026-08-27T03:25:21.675513Z` | `2026-08-27T03:25:22.109617Z` | 0.434 |
| Q12 | `query12.sql_0` | **SUCCESS** | `2026-08-27T03:25:22.109790Z` | `2026-08-27T03:25:22.995852Z` | 0.886 |
| Q14 | `query14.sql_0` | **SUCCESS** | `2026-08-27T03:25:22.996043Z` | `2026-08-27T03:25:23.612605Z` | 0.617 |
| Q18 | `query18.sql_0` | **SUCCESS** | `2026-08-27T03:25:23.612779Z` | `2026-08-27T03:25:27.317213Z` | 3.704 |
| Q1 | `query1.sql_0` | **SUCCESS** | `2026-08-27T03:25:27.367812Z` | `2026-08-27T03:25:35.196342Z` | 7.829 |
| Q3 | `query3.sql_0` | **SUCCESS** | `2026-08-27T03:25:35.196579Z` | `2026-08-27T03:25:36.472649Z` | 1.276 |
| Q6 | `query6.sql_0` | **SUCCESS** | `2026-08-27T03:25:36.472902Z` | `2026-08-27T03:25:36.983804Z` | 0.511 |
| Q12 | `query12.sql_0` | **SUCCESS** | `2026-08-27T03:25:36.984005Z` | `2026-08-27T03:25:37.791782Z` | 0.808 |
| Q14 | `query14.sql_0` | **SUCCESS** | `2026-08-27T03:25:37.791947Z` | `2026-08-27T03:25:38.387081Z` | 0.595 |
| Q18 | `query18.sql_0` | **SUCCESS** | `2026-08-27T03:25:38.387333Z` | `2026-08-27T03:25:41.806838Z` | 3.420 |


---

## 4. Workload Performance & Variability Analysis
- **Runtimes and Complexity**: As expected, Q1 and Q18 are the most expensive queries due to their large aggregation scans and complex join structures, respectively. Q6 is the fastest query due to the simplicity of its single-table scan and selective filters.
- **Variability**: Repetitions show minor variations typical of JVM warmup, Spark execution planning, and OS thread scheduling.
- **Workload Diversity**: The selection represents a robust test suite to measure degradation. Join-heavy queries (Q3, Q12, Q18) will be sensitive to compaction and data clustering, while scan-heavy queries (Q1, Q6) will directly measure scan throughput and file-skipping efficiency.

---

## 5. Limitations
- **Scale Factor**: The dataset is TPC-H SF1 (~1 GB), which fits entirely into memory. Runtimes on larger datasets will scale non-linearly.
- **Local Spark Context**: A standalone local Spark context on a single machine is not representative of a distributed, production-grade lakehouse cluster.
- **Experimental Control**: These numbers are designed specifically to act as control baselines to compare against compacted/degraded Iceberg layouts.
