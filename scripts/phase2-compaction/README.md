# Phase 2D: Iceberg Compaction and Physical Storage Recovery

This directory contains scripts and configurations for the **Phase 2D** experiment of our research Capstone project. The goal is to evaluate Iceberg-supported table compaction on a heavily fragmented table (`local.experiment.lineitem_fragmented`), measure physical storage improvements, and confirm complete logical data integrity.

---

## 1. Context and Relationship to Previous Phases

*   **Phase 2A (Table Health Baseline)**: Inspected the healthy control table `local.tpch.lineitem` and recorded its physical baseline characteristics (16 consolidated data files, ~9.08 MB average size, 1 snapshot).
*   **Phase 2B (Controlled Fragmentation)**: Repartitioned the control table's logical data into 200 small files (~842 KB average size) to create the fragmented table `local.experiment.lineitem_fragmented` in an isolated namespace.
*   **Phase 2C (Performance Impact)**: Executed the TPC-H analytical workload to quantify performance changes (slowdowns/speedups) on the small-file fragmented table layout.
*   **Phase 2D (Storage Maintenance - Current)**: Calls the Iceberg `rewrite_data_files` procedure to rewrite the 200 small files into a consolidated, optimized layout. This is a physical storage recovery step to test compaction efficiency.

---

## 2. Experimental Safety & Protection of the Control Table

*   **Control Table (`local.tpch.lineitem`) Protection**: The control table must **never** be compacted or modified. It serves as our permanent experimental baseline. Post-compaction, validation checks confirm its row count, file count, and snapshot remain untouched.
*   **Fragmented Table (`local.experiment.lineitem_fragmented`) target**: Compaction is performed exclusively on the experimental table.

---

## 3. Compaction Mechanism

We use the officially supported Iceberg Spark SQL procedure:
```sql
CALL local.system.rewrite_data_files(table => 'experiment.lineitem_fragmented')
```
This procedure merges data files inside active partitions using the default **binpack** strategy, which combines small files without altering the sort order. It commits a new snapshot containing references to the newly consolidated data files and removing references to the rewritten small files.

---

## 4. Directory Structure

```
scripts/phase2-compaction/
├── README.md
├── inspect_pre_compaction.py    # Reads pre-compaction storage and metadata characteristics
├── compact_table.py            # Executes Spark SQL rewrite_data_files
├── inspect_post_compaction.py   # Reads post-compaction storage and metadata characteristics
├── validate_compaction.py      # Verifies checksums, control table, and writes report
├── run_compaction.sh           # Main orchestration script
│
├── results/                    # Generated metrics and reports (JSON, CSV, MD)
└── logs/                       # Compaction execution timing logs
```

---

## 5. Execution and Validation

To run the experiment, execute the following script from the project root:

```bash
source ./setup_env.sh
./scripts/phase2-compaction/run_compaction.sh
```

The script will:
1. Initialize a Spark session to record baseline logical (row count, schema, sums) and physical (file metrics, sizes, snapshot ID) states.
2. Run Spark SQL compaction.
3. Perform a post-compaction physical inspection.
4. Validate that the schema, row counts, and checksums match exactly (Pre vs Post).
5. Verify the control table remains unmodified.
6. Generate a comparative markdown report `results/compaction_report.md` stating `COMPACTION DATA INTEGRITY: PASSED`.
