# Phase 1B: Comprehensive Baseline Workload Characterization

This directory contains the configurations, SQL files, analysis scripts, and runner scripts to execute a comprehensive baseline workload characterization.

## Purpose
The purpose is to characterize and record normal query execution performance (without any concurrent storage maintenance operations). This serves as the CONTROL group for future scheduler interference-cost measurements.

## Architecture
- **Engine**: Apache Spark 3.3.4 (Spark Thrift Server)
- **Table Format**: Apache Iceberg 1.4.3
- **Workload Client**: LST-Bench (Java JDBC driver)
- **Database**: local.tpch (TPC-H SF1)
- **Telemetry Storage**: DuckDB database (`scripts/baseline-workload/telemetry/telemetry_baseline_comprehensive.db`)

## Query Selection
We use six representative TPC-H queries providing a diverse mix of operations:
1.  **Q1 (Scan-Heavy / Aggregation-Heavy)**: Large-scale table scan on the `lineitem` table with groupings and aggregate computations.
2.  **Q3 (Join-Heavy / Aggregation-Heavy)**: Performs a three-way join across `customer`, `orders`, and `lineitem` with filter criteria and groupings.
3.  **Q6 (Scan-Heavy / Filtering-Heavy)**: Scan of `lineitem` with multiple highly selective range filters.
4.  **Q12 (Join-Heavy / Aggregation-Heavy / Filtering)**: Performs a join between `orders` and `lineitem` with complex conditional aggregates.
5.  **Q14 (Scan-Heavy / Join-Heavy / Case Aggregation)**: Joins `lineitem` and `part` within a specific date range.
6.  **Q18 (Join-Heavy / Large Grouping / Subquery)**: Employs an IN-subquery with a `GROUP BY HAVING` clause on `lineitem`, joined back with `customer` and `orders`.

No writes, deletes, updates, or maintenance tasks are executed.

---

## Directory Structure

```
scripts/baseline-workload/
├── config/
│   ├── connections_config.yaml     # Reuses loopback Thrift Server connection
│   ├── telemetry_config.yaml       # Points to telemetry_baseline_comprehensive.db
│   ├── experiment_config.yaml      # Configures 3 repetitions
│   ├── library.yaml                # Registers task templates for Q1, Q3, Q6, Q12, Q14, Q18
│   └── workload_baseline.yaml      # Workload phase running the 6 queries sequentially
│
├── sql/
│   ├── query1.sql
│   ├── query3.sql
│   ├── query6.sql
│   ├── query12.sql
│   ├── query14.sql
│   └── query18.sql
│
├── telemetry/                      # Stores DuckDB database
│
├── results/                        # Stores generated CSVs
│
├── analysis/
│   └── extract_results.py          # Post-execution analytics parsing script
│
├── run_baseline.sh                 # Fully automated runner script
├── validate_integrity.py           # Integrity checking via PySpark
└── README.md                       # This documentation
```

---

## How to Execute the Experiment

1. Ensure the Spark Thrift Server is running on port 10000.
2. Source your environment variables:
   ```bash
   source ./setup_env.sh
   ```
3. Run the automated runner script from the project root:
   ```bash
   ./scripts/baseline-workload/run_baseline.sh
   ```

The script will automatically:
- Verify variables and thrift server status.
- Execute LST-Bench for 3 repetitions (18 total query executions).
- Parse the telemetry database into CSV results at `results/`.
- Print a summary and validate the row counts of key Iceberg tables.
