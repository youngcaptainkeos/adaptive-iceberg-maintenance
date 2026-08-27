# Phase 2B: Controlled Iceberg Table Fragmentation

This directory contains the tools and configurations to build a physically degraded (fragmented) copy of the TPC-H `lineitem` table under `local.experiment.lineitem_fragmented`.

## Purpose
To study how physical layout affects query execution performance, we need to create a **treatment group table** containing identical logical data as the control table (`local.tpch.lineitem`) but written as a high count of small files. This allows us to isolate physical storage layout as the single experimental variable.

---

## Directory Structure
```
scripts/phase2-fragmentation/
├── create_fragmented_table.py  # Repartitions and writes the fragmented table, verifying logical equivalencies
├── inspect_fragmented_table.py # Collects physical metadata stats and compiles a comparative report
├── run_fragmentation.sh       # Automates execution, environment checks, and finalAssertions
├── results/                   # Outputs directory
│   ├── fragmented_table_metrics.json
│   ├── fragmented_file_metrics.csv
│   ├── fragmented_file_size_distribution.csv
│   ├── fragmented_snapshot_history.csv
│   └── fragmentation_report.md  # Detailed comparison report (Control vs Fragmented)
└── README.md                  # This documentation
```

---

## Fragmentation Strategy
- We enforce a high file count by repartitioning the logical DataFrame to `200` partitions prior to writing.
- We set the target file size to `524288` bytes (512 KB) to prevent Spark from writing large blocks and force small physical files.
- The original control table `local.tpch.lineitem` remains completely untouched.

---

## Logical Equivalence Verification
To guarantee the scientific integrity of the comparison, the creation script enforces that the fragmented table matches the control table across:
1. **Schema**: Strict comparison of Spark DataFrame column names, types, and nullability.
2. **Row Count**: Asserts that both tables contain exactly `6,001,215` rows.
3. **Data Checksums**: Sum aggregates of `l_quantity`, `l_extendedprice`, and `l_discount` must match exactly between the control and treatment tables.

---

## How to Run
1. Ensure the Spark environment by sourcing your configurations:
   ```bash
   source ./setup_env.sh
   ```
2. Run the runner script:
   ```bash
   ./scripts/phase2-fragmentation/run_fragmentation.sh
   ```

*Note: Compaction and storage maintenance procedures are intentionally NOT executed in this phase.*
