# Phase 1: Baseline Workload Characterization (Pilot Run)

This directory contains the configurations and custom SQL files to run a baseline workload pilot. 

## Purpose
The purpose is to characterize and record normal query execution performance (without any concurrent storage maintenance operations). This serves as the CONTROL group for future scheduler interference-cost measurements.

## Architecture
- **Engine**: Apache Spark 3.3.4 (Spark Thrift Server)
- **Table Format**: Apache Iceberg 1.4.3
- **Workload Client**: LST-Bench (Java JDBC driver)
- **Database**: local.tpch (TPC-H SF1)
- **Telemetry Storage**: DuckDB database (`scripts/baseline-workload/telemetry_baseline_pilot.db`)

## Query Selection
This baseline pilot runs three TPC-H queries sequentially:
1.  **`query1`**: High aggregation scan on the `lineitem` table.
2.  **`query6`**: Selective aggregation filtering on dates, discounts, and quantities.
3.  **`query12`**: Two-table join (`orders` and `lineitem`) with case-statement aggregation and shipmode filtering.

No writes, deletes, updates, or maintenance tasks (such as compaction or update statistics) are executed.

---

## Execution
To run this baseline experiment, run from the `lst-bench/` submodule root directory:
```bash
./launcher.sh \
  -c ../scripts/baseline-workload/config/connections_config.yaml \
  -e ../scripts/baseline-workload/config/experiment_config.yaml \
  -t ../scripts/baseline-workload/config/telemetry_config.yaml \
  -l ../scripts/baseline-workload/config/library.yaml \
  -w ../scripts/baseline-workload/config/workload_pilot.yaml
```

---

## Telemetry & Verification
- Telemetry results are saved in the DuckDB database: `scripts/baseline-workload/telemetry_baseline_pilot.db`.
- Query execution duration is measured at the statement level in the `experiment_telemetry` table.
- All execution records are verified to have completed with status `SUCCESS`.
- The Iceberg tables are read-only and remain completely unmodified.
