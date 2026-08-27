# Phase 2E: Performance Recovery Benchmark After Iceberg Compaction

This directory contains configuration files and scripts to benchmark query performance on the compacted experimental table `local.experiment.lineitem_fragmented` (State C, 1 data file) and compare it against the baseline healthy control (State A) and small-file fragmented (State B) table layouts.

---

## 1. Experimental Lifecycle Context

*   **State A (Healthy Control):** `local.tpch.lineitem` | 16 data files | ~9.08 MB average size.
*   **State B (Fragmented Treatment):** `local.experiment.lineitem_fragmented` (Before compaction) | 200 data files | ~842 KB average size.
*   **State C (Compacted Treatment):** `local.experiment.lineitem_fragmented` (After compaction) | 1 data file | ~156.34 MB average size.

In **Phase 2C**, we evaluated State B and identified that fragmentation causes parallelism speedups for scan-heavy queries (e.g. Q1, Q3) but significant task scheduling and footer-read overhead slowdowns for filter-heavy and complex join queries (e.g. Q6, Q18). 
In **Phase 2D**, we compacted State B down to State C.
In **Phase 2E (Current)**, we benchmark State C using the exact same TPC-H query set (Q1, Q3, Q6, Q12, Q14, Q18) with 3 repetitions (18 total executions) to evaluate if compaction recovers the performance degradation.

---

## 2. Directory Structure

```
scripts/phase2-compaction-performance/
├── README.md
├── run_compacted_benchmark.sh     # Orchestrator runner script
├── analyze_results.py              # Results extraction and three-state comparison
│
├── config/                         # LST-Bench configuration files
│   ├── connections_config.yaml
│   ├── telemetry_config.yaml
│   ├── experiment_config.yaml
│   ├── library.yaml
│   └── workload_compacted.yaml
│
├── sql/                            # Compacted SQL query templates
│   ├── query1_compacted.sql
│   ├── query3_compacted.sql
│   ├── query6_compacted.sql
│   ├── query12_compacted.sql
│   ├── query14_compacted.sql
│   └── query18_compacted.sql
│
├── telemetry/                      # duckdb telemetry database
├── results/                        # output CSV results (statement, summary, three-state)
└── analysis/                       # final compaction_performance_report.md
```

---

## 3. How to Run the Experiment

From the project root directory, run:

```bash
source ./setup_env.sh
./scripts/phase2-compaction-performance/run_compacted_benchmark.sh
```

---

## 4. Telemetry and Results Extraction

All executions are logged in a local DuckDB database `telemetry/telemetry_compacted.db` using the LST-Bench event logging framework.
The python analyzer `analyze_results.py` extracts the timings and creates:
1. `results/compacted_statement_results.csv` — Runtimes for all individual executions.
2. `results/compacted_summary.csv` — Aggregated metrics per query (mean, stddev, min, max, median).
3. `results/three_state_comparison.csv` — Comparative table of means and percentage deviations for Control vs. Fragmented vs. Compacted.
4. `analysis/compaction_performance_report.md` — Detailed scientific analysis answering performance recovery and trade-off questions.
