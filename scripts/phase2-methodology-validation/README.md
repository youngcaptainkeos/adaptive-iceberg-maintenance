# Phase 2F: Experimental Methodology Validation & Benchmark Noise Characterization

This phase establishes the statistical validity and validation layer for the Apache Iceberg performance benchmarking project. It responds to peer reviewer feedback to ensure any performance differences attributed to layout transformations (fragmentation or compaction) are scientifically valid and exceed the system's baseline "noise floor".

---

## 1. Scientific Motivation & Reviewer Concerns

Exploratory benchmarks (Phases 2C, 2D, and 2E) evaluated table performance using 3 repetitions per state. While functionally correct, this approach has methodological limitations:
1. **Low Repetition Count**: A 3-run sample size has high margin-of-error and is susceptible to system transients.
2. **Characterization of Noise Floor**: Without measuring run-to-run variation under *identical* conditions, we cannot distinguish real performance differences from JVM, GC, OS, or disk-cache variance.
3. **Warmup Influence**: Initial sequential execution without a warmup phase can bias results due to JIT compilation and class loading.
4. **Compaction Boundaries**: The exploratory compaction resulted in a 1-file state (~156 MB). This represents an extreme physical condition that starves thread parallelism rather than a representative production-style compaction.

To address these concerns, this phase executes a noise-floor characterization run:
- **Core Question**: *How much timing variance naturally occurs when the same unchanged queries run repeatedly against the same unchanged healthy table in this environment?*

---

## 2. Experimental Design

- **Control Table**: `local.tpch.lineitem` (16 data files, ~9.08 MB average size, 6,001,215 rows).
- **Representative Workload**: TPC-H queries Q1, Q3, Q6, Q12, Q14, and Q18.
- **Warmup Policy**: **2 complete workload repetitions** (12 query runs) are executed to warm up JIT, page cache, and Spark metadata caches. These are logged but excluded from statistical summaries.
- **Measurement Repetitions**: **20 complete repetitions** (120 query runs) are executed sequentially and recorded for variance processing.
- **Execution Order**: Sequential query execution within each repetition.

---

## 3. Data Collection & Statistical Metrics

For the 20 measured repetitions, the analysis pipeline computes:
- **Central Tendency**: Mean, Median
- **Spread**: Minimum, Maximum, Range, Standard Deviation ($\sigma$), Variance ($\sigma^2$)
- **Relative Variation**: Coefficient of Variation ($CV = \sigma / \mu \times 100$)
- **Outlier Detection**: Interquartile Range (IQR) method:
  $$IQR = Q_3 - Q_1$$
  $$Outlier\ Bounds = [Q_1 - 1.5 \times IQR, \;\; Q_3 + 1.5 \times IQR]$$
- **Temporal Stability**: Comparison of first 5 runs vs. last 5 runs to evaluate drift or late-stage JIT/GC optimization.

---

## 4. How to Reproduce

First, ensure the Spark Thrift Server is running on port 10000 and the environment variables are sourced:
```bash
source setup_env.sh
```

Execute the orchestration script:
```bash
./scripts/phase2-methodology-validation/run_noise_characterization.sh
```

### Script Execution Workflow:
1. Validates Spark/Java env variables.
2. Confirms Thrift Server connectivity.
3. Runs `collect_metadata.py` to write `results/environment_metadata.json` and records the pre-execution row count, file count, and snapshot ID of `local.tpch.lineitem`.
4. Clears previous telemetry database.
5. Launches LST-Bench for 22 total repetitions.
6. Runs `analyze_results.py` to query the telemetry DuckDB and build statistical reports.
7. Runs `verify_post_state.py` to assert that the control table was NOT modified (read-only verification).

---

## 5. Interpreting the Results

### The $3\sigma$ (or $3\text{CV}$) Scientific Significance Threshold
To confidently attribute a performance speedup or slowdown to a physical layout change, the observed difference must exceed **$3 \times \text{Standard Deviation}$** ($3\sigma$) or **$3 \times \text{CV}$** of the natural environment noise. 
- *Example*: If Query A has a $CV$ of $4\%$, any layout transformation that results in a performance difference smaller than $12\%$ must be treated as OS/JVM scheduling noise.

---

## 6. Single-Machine Benchmarking Limitations

This experiment runs on a local, single-node workstation. Users should note the following constraints:
- **No Cluster Generalization**: Runtimes, scheduling patterns, and memory footprints characterize single-node execution and may not represent multi-node Hadoop/Kubernetes clusters.
- **Resource Contention**: Background OS processes, CPU thermal throttling, and local SSD I/O latency contribute to the variance recorded here.
- **Heap Pressure**: Running 132 consecutive query executions on a single Spark Thrift Server instance can induce Java Garbage Collection pause variance, which is explicitly tracked in our outlier report.
