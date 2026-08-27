# Phase 2G: Validated Three-State Physical Layout Performance Experiment

This directory implements the scientifically validated comparative benchmarking pipeline to evaluate Apache Iceberg performance across three different physical layouts of the `lineitem` table. 

---

## 1. Experimental Methodology Corrections

This experiment addresses the peer-reviewer feedback from Phase 2F:
* **Repetition Count**: Runs **22 repetitions** total (2 warmups to populate Spark JIT and page cache, and **20 measured repetitions**).
* **Positional Bias Counterbalancing**: Alternates execution order using all 6 permutations of the 3 states (ABC, ACB, BAC, BCA, CAB, CBA) in rotation to eliminate JVM warming and caching biases.
* **Realistic Compaction**: State C is compacted using an explicit target size of **64 MB**, avoiding the core starvation of a single giant file.
* **State B Stress Treatment**: State B is explicitly framed as an **intentional small-file stress treatment** (512 KB target, ~200 files) to evaluate metadata and I/O degradation.
* **Empirical Noise-Floor Screening**: observed differences are screened against Phase 2F thresholds (Q1=7.70%, Q3=20.45%, Q6=16.50%, Q12=22.75%, Q14=32.96%, Q18=17.09%, Workload=9.75%) and classified as `EXCEEDS EMPIRICAL NOISE THRESHOLD` or `WITHIN EMPIRICAL NOISE RANGE` rather than claiming formal statistical significance without hypothesis testing.
* **Student-t Confidence Intervals**: Reports 95% Confidence Intervals for means using the Student-t distribution ($df=19$, $t_{0.025, 19}=2.093$).
* **Paired Comparisons**: Computes repetition-cycle-level differences between states to isolate system drift.

---

## 2. Table States

* **State A (Control)**: `local.tpch.lineitem` (16 files, ~9.08 MB avg size, completely read-only).
* **State B (Fragmented Stress Treatment)**: `local.experiment.lineitem_validated_fragmented` (repartitioned to 200, target size 512 KB).
* **State C (Realistically Compacted)**: `local.experiment.lineitem_validated_compacted` (repartitioned to 200, compacted using 64 MB target).

---

## 3. Directory Layout

* `preparation/`: Creation, validation, and metadata collection scripts.
* `config/`: Connections, library, and workload configuration files.
* `sql/`: State-isolated SQL queries for Q1, Q3, Q6, Q12, Q14, and Q18.
* `telemetry/`: Raw DuckDB telemetry records.
* `results/`: Processed CSV metrics and JSON environment metadata.
* `analysis/`: Plot generation scripts, statistical compiler, and the final Markdown scientific report.

---

## 4. How to Reproduce

Execute the orchestration pipeline:
```bash
./scripts/phase2-validated-layout-comparison/run_validated_experiment.sh
```

The script will automatically perform pre-run integrity assertions, prepare treatment tables, run LST-Bench, calculate statistics, generate plots, verify read-only invariants, and output the final report.
