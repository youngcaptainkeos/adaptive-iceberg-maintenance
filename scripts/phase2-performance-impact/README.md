# Phase 2C: Performance Impact of Iceberg Small-File Fragmentation

This directory contains the tools and configurations to execute the query benchmark against our physically fragmented table (`local.experiment.lineitem_fragmented`) and evaluate the performance impact compared to the healthy control table baseline.

## Purpose
By executing the exact same query workload (TPC-H Q1, Q3, Q6, Q12, Q14, Q18) with the same number of repetitions, but replacing ONLY the `lineitem` table references with the fragmented copy, we can isolate the performance impact of small-file fragmentation as the single independent physical layout variable.

The original control table `local.tpch.lineitem` is strictly read-only and is never modified by this experiment. No compaction or storage maintenance is performed in this phase.

---

## Directory Structure
```
scripts/phase2-performance-impact/
├── config/
│   ├── connections_config.yaml      # Client JDBC configurations
│   ├── telemetry_config.yaml        # Telemetry storage path
│   ├── experiment_config.yaml       # Run metadata and repetitions configuration (3)
│   ├── library.yaml                 # Registers query SQL paths
│   └── workload_fragmented.yaml     # Sequence of tasks running sequential TPC-H queries
│
├── sql/
│   ├── query1_fragmented.sql
│   ├── query3_fragmented.sql
│   ├── query6_fragmented.sql
│   ├── query12_fragmented.sql
│   ├── query14_fragmented.sql
│   └── query18_fragmented.sql       # Both lineitem references replaced
│
├── run_fragmented_benchmark.sh      # Reproducible runner script
├── analyze_results.py               # Telemetry analysis and comparative calculations script
├── results/                         # Outputs directory
│   ├── fragmented_statement_results.csv
│   ├── fragmented_summary.csv
│   └── performance_comparison.csv   # Absolute delta, factor change, and pct change
│
├── analysis/
│   └── fragmentation_impact_report.md # Final human-readable report comparing control vs fragmented
│
└── README.md                        # This documentation
```

---

## Prerequisites
- The Spark Thrift Server must be running on port `10000`.
- The environment variables must be configured by running:
  ```bash
  source ./setup_env.sh
  ```

---

## How to Execute the Benchmark
1. From the project root, run the orchestrator script:
   ```bash
   ./scripts/phase2-performance-impact/run_fragmented_benchmark.sh
   ```
2. The script will automatically:
   - Perform port checks and verify table counts (6,001,215 rows).
   - Clear any stale telemetry databases.
   - Execute LST-Bench sequentially across 3 repetitions (18 statement runs).
   - Execute the `analyze_results.py` post-processing script.
   - Run post-run assertions verifying that no data was modified.
