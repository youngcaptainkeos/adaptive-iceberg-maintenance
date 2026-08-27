# Phase 2A: Iceberg Table Health / Physical State Baseline Inspection

This directory contains the tools and scripts to capture the physical baseline characteristics of the `local.tpch.lineitem` Iceberg table before any layout degradation or small-file experiments are introduced.

## Purpose
In order to accurately measure the impact of table degradation (such as fragmentation and small-file conditions) and subsequent compaction/maintenance operations, we must first capture the **control healthy storage state** of the table. This healthy state acts as a reference point for comparing:
- Data file size distributions.
- Total count of data files.
- Metadata and snapshot lineage history.
- Average/median/min/max data file sizes.

---

## Directory Structure
```
scripts/phase2-table-health/
├── inspect_table_state.py      # PySpark script to query metadata tables and compute metrics
├── run_inspection.sh          # Orchestrates execution and environment sourcing
├── results/                    # Output directory for results
│   ├── table_health_baseline.json
│   ├── file_metrics.csv
│   ├── snapshot_history.csv
│   ├── file_size_distribution.csv
│   └── table_health_report.md  # Human-readable markdown health report
└── README.md                  # This documentation
```

---

## How to Execute the Inspection
1. Verify the Spark environment by sourcing the configuration:
   ```bash
   source ./setup_env.sh
   ```
2. Run the executable run script:
   ```bash
   ./scripts/phase2-table-health/run_inspection.sh
   ```

---

## Output Metrics Files
- **`results/table_health_baseline.json`**: Key-value summary of table metadata, snapshots, row counts, and files.
- **`results/file_metrics.csv`**: Detail listing of active data files, their formats, record counts, and sizes in bytes.
- **`results/snapshot_history.csv`**: Log of committed snapshots, listing snapshot IDs, parent IDs, operation types, and summary metadata.
- **`results/file_size_distribution.csv`**: File counts and byte volume aggregated across standard size buckets.
- **`results/table_health_report.md`**: Auto-generated human-readable markdown report analyzing the table state.

This phase is strictly read-only; no modification of table structures, data, or metadata takes place.
