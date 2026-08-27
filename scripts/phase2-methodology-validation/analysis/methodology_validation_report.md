# Experimental Methodology Validation & Benchmark Noise Characterization Report (Phase 2F)

This scientific report establishes the statistical validation layer for the lakehouse storage maintenance experiment. It evaluates the natural run-to-run timing variance ("noise floor") of the Spark Thrift Server / Iceberg catalog execution environment across 20 complete, identical repetitions of the 6-query representative TPC-H workload targeting the unchanged healthy control table.

---

## 1. Storage State & Environment Metadata

The validation experiment was executed on the original healthy control table:
- **Table Name**: `local.tpch.lineitem`
- **Active Data Files**: 16
- **Total Table Size**: 145.27 MB (152,325,814 bytes)
- **Logical Row Count**: 6,001,215 (Read-Only)

### System Environment Metrics
| Parameter | Value |
| :--- | :--- |
| **timestamp** | 2026-08-27T14:45:44.636185 |
| **hostname** | shashlaptop |
| **os_name** | Linux |
| **os_release** | 7.0.0-30-generic |
| **os_version** | #30~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Fri Aug  7 13:27:52 UTC 2 |
| **cpu_model** | AMD Ryzen 7 5800H with Radeon Graphics |
| **logical_cpu_cores** | 16 |
| **total_physical_memory** | 14.96 GB |
| **spark_version** | 3.3.4 |
| **java_version** | openjdk version "11.0.32" 2026-07-21 |
| **iceberg_version** | 1.4.3 (from POM) |
| **warehouse_location** | file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse |
| **catalog_name** | local |
| **catalog_type** | hadoop |
| **control_table** | local.tpch.lineitem |
| **control_table_rows** | 6001215 |
| **control_table_files** | 16 |
| **control_table_snapshot_id** | 8128630582928284438 |
| **control_table_snapshot_count** | 1 |


---

## 2. Warmup Policy Execution

We executed **2 complete warmup repetitions** prior to recording the measured repetitions. These runs populated the Spark Thrift Server JVM class caches, JIT cache, and underlying OS filesystem page caches.

| Repetition | Type | Duration |
| :--- | :--- | :--- |
| Warmup run 0 | Repetition index 0 | 24.049 s |
| Warmup run 1 | Repetition index 1 | 13.548 s |


*Note: Warmup runs are excluded from all subsequent Central Tendency, Spread, Outlier, and Temporal Stability statistics.*

---

## 3. Measured Central Tendency & Spread (20 Repetitions)

The table below summarizes the timing results across the 20 measured sequential executions:

| Query / Workload | Mean (seconds) | Median (seconds) | Min (seconds) | Max (seconds) | Range (seconds) | Std Dev (seconds) | Variance | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Q1** | 6.801 s | 6.774 s | 6.550 s | 7.303 s | 0.753 s | 0.1745 s | 0.030435 s | **2.57%** |
| **Q3** | 1.140 s | 1.126 s | 1.033 s | 1.323 s | 0.291 s | 0.0777 s | 0.006043 s | **6.82%** |
| **Q6** | 0.385 s | 0.378 s | 0.357 s | 0.426 s | 0.069 s | 0.0212 s | 0.000449 s | **5.50%** |
| **Q12** | 0.688 s | 0.679 s | 0.625 s | 0.798 s | 0.173 s | 0.0522 s | 0.002721 s | **7.58%** |
| **Q14** | 0.572 s | 0.559 s | 0.498 s | 0.719 s | 0.221 s | 0.0628 s | 0.003946 s | **10.99%** |
| **Q18** | 3.025 s | 2.985 s | 2.710 s | 3.384 s | 0.674 s | 0.1724 s | 0.029705 s | **5.70%** |
| **Total Workload** | 12.612 s | 12.464 s | 12.036 s | 13.360 s | 1.324 s | 0.4097 s | 0.167891 s | **3.25%** |


### Key Analysis of CV (Coefficient of Variation)
The Coefficient of Variation ($CV = \sigma / \mu \times 100$) represents the relative dispersion of execution times. 
- **Stable Queries ($CV < 5\%$)**: These queries have extremely tight distributions. Timing variations are minimal, and any physical-layout effect larger than a few percent can be confidently attributed.
- **Unstable/Noisy Queries ($CV \ge 5\%$)**: These queries exhibit significant run-to-run variance, meaning that small observed timing changes could easily be environment noise.

---

## 4. Outlier Analysis (IQR Method)

Using the standard Interquartile Range (IQR) rule:
- $IQR = Q_3 - Q_1$
- $\text{Outlier Bounds} = [Q_1 - 1.5 \times IQR, \; Q_3 + 1.5 \times IQR]$

Below are the individual statements flagged as statistical outliers:

| Level | Repetition | Duration | Outlier Bounds | Notes / Details |
| :--- | :--- | :--- | :--- | :--- |
| Query Q1 | Repetition 17 | 7.303 s | [6.372 s, 7.216 s] | IQR=0.2109 s |
| Query Q3 | Repetition 5 | 1.323 s | [0.959 s, 1.297 s] | IQR=0.0846 s |


*Recommendation*: All valid runs are preserved in the main analysis. No statement executions failed.

---

## 5. Temporal Stability & Performance Drift

To analyze whether execution stabilizes after the initial warmup runs, we compare the mean runtime of the **first 5 measured repetitions** (Repetitions 1–5) against the **last 5 measured repetitions** (Repetitions 16–20):

| Query / Workload | First 5 Mean (s) | Last 5 Mean (s) | Temporal Change (%) |
| :--- | :--- | :--- | :---: |
| **Q1** | 6.798 s | 6.894 s | **+1.41%** |
| **Q3** | 1.218 s | 1.117 s | **-8.27%** |
| **Q6** | 0.407 s | 0.379 s | **-6.90%** |
| **Q12** | 0.750 s | 0.673 s | **-10.30%** |
| **Q14** | 0.639 s | 0.563 s | **-11.97%** |
| **Q18** | 3.126 s | 3.156 s | **+0.96%** |
| **Total Workload** | 12.937 s | 12.781 s | **-1.21%** |


*Interpretation*: A negative temporal change indicates a gradual speedup (cache consolidation / JIT optimization continuing over time), while a positive change indicates performance drift or slowdown (possibly due to Java Garbage Collection overhead, heap pressure, or thermal throttling).

---

## 6. Practical Noise Floor Definition

Based on the empirical measurements, we define the **Scientific Confidence Threshold** for performance differences. An observed execution change is statistically valid only if it exceeds **$3 \times \text{Standard Deviation}$** ($3\sigma$) or **$3 \times \text{CV}$** to ensure a $99.7\%$ probability that the difference is not natural environment fluctuation.

*   **Q1**: Standard Deviation = `0.1745 s` (CV = `2.57%`). Required threshold for statistical significance: **>7.70%** change (or **>0.523 s** absolute change).
*   **Q3**: Standard Deviation = `0.0777 s` (CV = `6.82%`). Required threshold for statistical significance: **>20.45%** change (or **>0.233 s** absolute change).
*   **Q6**: Standard Deviation = `0.0212 s` (CV = `5.50%`). Required threshold for statistical significance: **>16.50%** change (or **>0.064 s** absolute change).
*   **Q12**: Standard Deviation = `0.0522 s` (CV = `7.58%`). Required threshold for statistical significance: **>22.75%** change (or **>0.156 s** absolute change).
*   **Q14**: Standard Deviation = `0.0628 s` (CV = `10.99%`). Required threshold for statistical significance: **>32.96%** change (or **>0.188 s** absolute change).
*   **Q18**: Standard Deviation = `0.1724 s` (CV = `5.70%`). Required threshold for statistical significance: **>17.09%** change (or **>0.517 s** absolute change).
*   **Total Workload**: Standard Deviation = `0.4097 s` (CV = `3.25%`). Required threshold for statistical significance: **>9.75%** change (or **>1.229 s** absolute change).


> [!WARNING]
> Any observed performance difference smaller than the $3\sigma$ (or $3\text{CV}$) threshold listed above MUST be treated as experimental noise. For example, if a query has a $CV$ of $4.0\%$, any physical layout change that results in less than a $12.0\%$ performance change cannot be scientifically validated as a causal consequence of the layout.

---

## 7. Relationship to Previous Phase 2C/2D/2E Results

The previous Phase 2C, 2D, and 2E experiments successfully demonstrated the engineering mechanics of table fragmentation and rewrite compaction. The timing results generated in those phases remain preserved as **Exploratory / Pilot Results**.

We revise the scientific strength of their interpretation as follows:
1. **Low Repetition Count**: Because the pilot results utilized only 3 repetitions, their calculated means have high statistical uncertainty. In queries with naturally high variance (e.g. where the $CV$ is high), a 3-run average is insufficient to distinguish physical layout effects from random JVM/OS noise.
2. **Compaction Strategy**: The Phase 2D compaction consolidated the table into a single active file (~156 MB). This created a severe core-starvation condition (1 task running sequentially). This represents an exploratory extreme boundary rather than a representative production-style compaction.
3. **Draft Conclusions**: The previously suggested speedups/slowdowns and optimal layout findings are classified as exploratory hypotheses. They must be validated using the strengthened methodology outlined below.

---

## 8. Proposed Phase 2G Experimental Design

To establish a scientifically rigorous conclusion, we recommend proceeding to **Phase 2G: Strengthened Comparative Analysis** with the following corrections:

1. **Explicitly Controlled Compaction Target Size**: Instead of allowing compaction to produce a single active file, we will rewrite data files with explicit target sizes to test realistic maintenance conditions:
   - Target Size: **64 MB** (will produce 2–3 moderate-sized data files) or **128 MB** (will produce 1–2 data files).
2. **Execution Interleaving**: We will randomize or interleave the execution order of states to eliminate JVM warmup bias. For example, instead of running all Control runs, then all Fragmented runs, and then all Compacted runs, we will interleave:
   - Cycle: $A \to B \to C \to A \to B \to C \dots$
3. **Repetition Count**: We will execute at least **10 measured repetitions** per physical state, preceded by 2 warmups.
4. **Variance Reporting**: The comparative report will display error bars ($95\%$ confidence intervals) and explicitly check if differences exceed the practical noise floor.

---

*Report compiled on: 2026-08-27T09:20:37.688531*
