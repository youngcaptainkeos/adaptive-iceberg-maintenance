# Workload Characterization Report

This report documents the baseline performance characterization of the TPC-H workload on our local Iceberg catalog, serving as the experimental control group for Phase 1B.

**Experiment Run ID:** `2026_08_27_05_48_13_779`
**Generated At:** `2026-08-27T05:48:55.579785Z`

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
| Q1 | 3 | 3 | 0 | 8.111 | 7.169 | 7.106 | 10.059 | 1.687 |
| Q3 | 3 | 3 | 0 | 1.300 | 1.172 | 1.117 | 1.612 | 0.271 |
| Q6 | 3 | 3 | 0 | 0.406 | 0.401 | 0.401 | 0.417 | 0.009 |
| Q12 | 3 | 3 | 0 | 0.738 | 0.729 | 0.672 | 0.813 | 0.070 |
| Q14 | 3 | 3 | 0 | 0.557 | 0.542 | 0.540 | 0.587 | 0.027 |
| Q18 | 3 | 3 | 0 | 2.699 | 2.678 | 2.638 | 2.781 | 0.074 |


---

## 3. Detailed Execution Records
Below are the individual statement execution records:

| Query | Repetition / Statement | Status | Start Time | End Time | Duration (s) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Q1 | `query1.sql_0` | **SUCCESS** | `2026-08-27T05:48:13.799557Z` | `2026-08-27T05:48:23.858358Z` | 10.059 |
| Q3 | `query3.sql_0` | **SUCCESS** | `2026-08-27T05:48:23.866371Z` | `2026-08-27T05:48:25.478081Z` | 1.612 |
| Q6 | `query6.sql_0` | **SUCCESS** | `2026-08-27T05:48:25.478305Z` | `2026-08-27T05:48:25.895102Z` | 0.417 |
| Q12 | `query12.sql_0` | **SUCCESS** | `2026-08-27T05:48:25.895291Z` | `2026-08-27T05:48:26.707918Z` | 0.813 |
| Q14 | `query14.sql_0` | **SUCCESS** | `2026-08-27T05:48:26.708112Z` | `2026-08-27T05:48:27.295552Z` | 0.587 |
| Q18 | `query18.sql_0` | **SUCCESS** | `2026-08-27T05:48:27.295760Z` | `2026-08-27T05:48:30.076701Z` | 2.781 |
| Q1 | `query1.sql_0` | **SUCCESS** | `2026-08-27T05:48:30.137272Z` | `2026-08-27T05:48:37.243720Z` | 7.106 |
| Q3 | `query3.sql_0` | **SUCCESS** | `2026-08-27T05:48:37.243914Z` | `2026-08-27T05:48:38.415743Z` | 1.172 |
| Q6 | `query6.sql_0` | **SUCCESS** | `2026-08-27T05:48:38.415906Z` | `2026-08-27T05:48:38.816687Z` | 0.401 |
| Q12 | `query12.sql_0` | **SUCCESS** | `2026-08-27T05:48:38.816929Z` | `2026-08-27T05:48:39.489351Z` | 0.672 |
| Q14 | `query14.sql_0` | **SUCCESS** | `2026-08-27T05:48:39.489550Z` | `2026-08-27T05:48:40.031708Z` | 0.542 |
| Q18 | `query18.sql_0` | **SUCCESS** | `2026-08-27T05:48:40.031940Z` | `2026-08-27T05:48:42.670332Z` | 2.638 |
| Q1 | `query1.sql_0` | **SUCCESS** | `2026-08-27T05:48:42.712495Z` | `2026-08-27T05:48:49.881512Z` | 7.169 |
| Q3 | `query3.sql_0` | **SUCCESS** | `2026-08-27T05:48:49.881718Z` | `2026-08-27T05:48:50.998429Z` | 1.117 |
| Q6 | `query6.sql_0` | **SUCCESS** | `2026-08-27T05:48:50.998609Z` | `2026-08-27T05:48:51.399447Z` | 0.401 |
| Q12 | `query12.sql_0` | **SUCCESS** | `2026-08-27T05:48:51.399639Z` | `2026-08-27T05:48:52.128798Z` | 0.729 |
| Q14 | `query14.sql_0` | **SUCCESS** | `2026-08-27T05:48:52.129004Z` | `2026-08-27T05:48:52.669552Z` | 0.541 |
| Q18 | `query18.sql_0` | **SUCCESS** | `2026-08-27T05:48:52.669767Z` | `2026-08-27T05:48:55.347342Z` | 2.678 |


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
