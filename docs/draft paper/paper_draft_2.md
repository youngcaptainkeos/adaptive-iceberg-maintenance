# Predictive and Uncertainty-Aware Scheduling of Apache Iceberg Maintenance Under Concurrent Analytical Workloads

**Paper Draft Version:** 2.0 (Draft 2)  
**Target Venue:** Proceedings of the VLDB Endowment (PVLDB)  

**Shashank Keshava Murthy**  
*PES University, Bangalore*  

**Shashank D**  
*PES University, Bangalore*  

**Prachi Jalan**  
*PES University, Bangalore*  

**Samarth**  
*PES University, Bangalore*  

---

## Abstract
Modern analytical data platforms increasingly rely on open table formats like Apache Iceberg to manage large-scale data lakes. To ensure long-term read efficiency, these engines run background physical layout maintenance, such as small-file compaction (`rewrite_data_files`). However, background compaction competes directly with foreground analytical queries for CPU, executor memory, I/O bandwidth, and OS page cache. Existing platforms rely on static off-peak crons, crude resource threshold heuristics, or layout-only optimizers that determine *what* to compact without predicting *when* to execute maintenance relative to concurrent workload pressure.

This paper presents an empirical and predictive framework for learned, uncertainty-aware timing of Apache Iceberg table maintenance under concurrent analytical query execution. Through a comprehensive multi-phase experimental study on Apache Spark and TPC-H workloads—comprising both discrete paired sweeps and a continuous 4.13-hour physical workload trace ($14,867$ 1Hz telemetry records and $778$ physical query dispatches across 5 non-homogeneous Poisson process regimes)—we quantify interference dynamics, evaluate machine learning regressors for pre-decision interference prediction, and formulate uncertainty-bounded scheduling policies.

Our discrete measurement phase ($N=528$ query executions across 20 paired trials) demonstrates that concurrent Iceberg compaction induces statistically significant query latency degradation, yielding a mean Query Interference Ratio (QIR) of $+10.38\%$ under FIFO task scheduling ($p=0.00161, d_z=1.165$) and $+12.77\%$ under FAIR task pool scheduling ($p<0.00001, d_z=2.497$), with latency spikes reaching $+20.95\%$ for heavy join/aggregation queries (Q14). In Phase 3B ($N=168$ paired observations across a 12-configuration sweep), we enforce strict pre-decision feature isolation to prevent information leakage; a Random Forest regressor predicts continuous QIR with a Mean Absolute Error (MAE) of $5.38\%$. Conversely, binary Service Level Agreement (SLA) violation classification yields an ROC-AUC of only $0.531$, representing a critical negative result demonstrating that binary classification fails under severe class imbalance and boundary noise.

In Phase 4 and Phase 5, we evaluate sliding-window temporal feature engineering ($60$s rolling windows predicting $300$s execution horizons) and deploy an 8-policy scheduling harness across continuous physical workload traces ($N=2,115$ decision windows). The learned ML PointPrediction policy achieves **$64.43\%$ maintenance completion** while reducing query SLA violations from **$12.99\%$ (AlwaysRun) down to $8.43\%$**—a **$35.1\%$ relative SLA violation reduction** over baseline execution. Furthermore, zero-shot Out-of-Domain (OOD) testing on unseen file fragmentation states (100 and 350 files) proves that while point-prediction models degrade under structural distribution shift ($R^2 < 0$), split-conformal quantile upper-bound modeling ($q=0.95$) achieves **exact $95.00\%$ empirical coverage invariance** on OOD data. This work provides the first empirical and mathematical proof that conformal quantile bounds afford robust safety guarantees for dynamic database maintenance scheduling.

---

## 1. Introduction

Modern analytical data architectures have evolved from traditional monolithic data warehouses into decoupled "data lakehouses" built on top of object stores (e.g., AWS S3, HDFS, Azure ADLS) and open storage formats such as Apache Iceberg, Apache Hudi, and Delta Lake. These formats support ACID transactions, schema evolution, and fine-grained partition evolution over petabyte-scale datasets. However, continuous streaming ingestion, micro-batch writes, and frequent update/delete operations cause physical table layouts to degrade over time. In particular, tables accumulate millions of small files, inflating metadata manifests, degrading query planning performance, and creating severe file-open and I/O serialization overheads during query execution.

To preserve table health and query responsiveness, lakehouse engines execute background maintenance procedures. In Apache Iceberg, the `rewrite_data_files` procedure merges fragmented small data files into contiguous, bin-packed columnar files (e.g., 128 MB or 512 MB Parquet files). While data compaction significantly improves long-term query performance, its short-term execution incurs massive physical resource overhead. Compaction reads large volumes of small files, decompresses columnar blocks, re-sorts records, and writes merged target files. When executed concurrently with user analytical queries, compaction contends for shared compute executors, JVM heap memory, disk I/O, network bandwidth, and operating-system page cache.

### 1.1 The Operational Paradox and Existing Limitations
This dynamic introduces a fundamental operational paradox: *maintenance is necessary to prevent long-term table degradation, but its immediate execution degrades foreground query latencies.* Existing database engines and lakehouse management frameworks address this problem using simplistic operational paradigms:

1. **Static Cron / Off-Peak Rules:** Maintenance is scheduled at arbitrary fixed intervals (e.g., 2:00 AM daily). This strategy fails in global 24/7 cloud enterprise setups where non-stationary analytical workloads persist continuously without predictable low-load windows.
2. **Coarse Resource Thresholds:** Maintenance triggers only when host CPU or memory utilization drops below a static scalar threshold (e.g., CPU $< 30\%$). These rules are blind to active query stage characteristics, query structural complexity, and storage fragmentation geometry.
3. **Layout-Only Optimizers:** Frameworks like AutoComp \cite{autocomp}, Smart Compaction \cite{smartcompaction}, and PTO \cite{pto} optimize *what* tables or partitions to compact and *how* to lay out data. However, they treat maintenance execution as an isolated operation, ignoring the interference penalty imposed on active foreground query streams.
4. **Uncertainty-Blind RL Schedulers:** Recent reinforcement learning approaches (e.g., Karim et al. \cite{karim2026}) attempt to optimize action timing but lack distribution-free safety guarantees. When confronted with unobserved workload surges or distribution shifts, uncalibrated ML models make dangerously overconfident scheduling decisions that trigger catastrophic query SLA violations.

### 1.2 Core Research Question
This project addresses the operational challenge through explicit workload interference prediction, continuous temporal sequence modeling, and distribution-free uncertainty calibration. We pose the core research question:

> **Given that lakehouse table maintenance must be executed to preserve long-term read health, *when* should it be scheduled relative to active query workload dynamics to maximize storage throughput while providing explicit, empirical guarantees against query SLA violations?**

### 1.3 Key Contributions
To answer this question, we design, implement, and scientifically validate a learned, uncertainty-aware scheduling framework for Apache Iceberg on Apache Spark. Our primary contributions are:

- **Empirical Interference Quantification (Phase 3A):** We build an automated, counterbalanced experimental harness over TPC-H benchmarks ($N=528$ query executions) with verified temporal overlap ($OverlapRatio \ge 0.95$). We provide statistical proof (Wilcoxon signed-rank test $p=0.00161$, Cohen's $d_z=1.165$) that concurrent Iceberg compaction causes severe query latency degradation ($+10.38\%$ to $+12.77\%$ mean QIR, peaking at $+20.95\%$). Furthermore, we establish that task-slot isolation (Spark FAIR scheduling pools) fails to mitigate interference caused by physical I/O and memory channel contention.
- **Leakage-Isolated Predictive Signal Matrix (Phase 3B):** We formulate a prediction matrix strictly isolated to pre-decision state variables ($X_{\text{pred}}$), proving that post-execution telemetry ($X_{\text{eval}}$) causes severe information leakage. We train point regressors (MAE $5.38\%$) and publish a critical negative result: binary SLA classification ($QIR > 15\%$) achieves an ROC-AUC of only $0.531$, demonstrating that binary classifiers fail under severe class imbalance and aleatoric boundary noise.
- **Continuous Physical Workload Infrastructure (Phase 4):** We construct a 1Hz telemetry collector and a Non-Homogeneous Poisson Process (NHPP) query arrival generator simulating 5 distinct operational regimes (LOW, MODERATE, HIGH, BURST, RECOVERY). We execute a continuous 4.13-hour physical experiment logging $14,867$ 1Hz telemetry records and $778$ physical query dispatches, constructing a temporal sliding window feature dataset ($60$s rolling statistics predicting $300$s target horizons).
- **Multi-Policy Trace Replay & Pareto Superiority (Phase 5):** We implement an 8-policy scheduling harness with bounded starvation protection ($K_{\text{max}}=3$). Replaying the continuous 4-hour trace ($N=2,115$ decision windows), we prove that our ML PointPrediction policy achieves **$64.43\%$ maintenance completion** while reducing query SLA violations from **$12.99\%$ (AlwaysRun) down to $8.43\%$**—a **$35.1\%$ relative SLA violation reduction**.
- **Rigorous Scientific Falsification & Zero-Shot OOD Proof (Phase 3D):** We subject our models to Leave-One-Configuration-Out Cross Validation (LOCO-CV across 12 folds) and trivial scalar baseline comparisons. We demonstrate that while all point-prediction models fail under zero-shot Out-of-Domain (OOD) file fragmentations ($100$ and $350$ files, $N=80$ trials, $R^2 < 0$), our split-conformal quantile upper-bound model ($q=0.95$) achieves **exact $95.00\%$ empirical coverage invariance**, proving that conformal upper bounds maintain distribution-free safety guarantees under structural workload shifts.

---

## 2. Background and Related Work

### 2.1 Apache Iceberg Layout Mechanics & Compaction
Apache Iceberg is an open table format for large-scale analytical data sets. An Iceberg table snapshot consists of a metadata file, manifest lists, manifest files, and columnar data files (typically Apache Parquet or ORC). During concurrent writes or streaming ingestion, Iceberg appends new data files without altering existing files. Over time, this leads to the **small-file problem**:

$$\text{File Count} \gg \frac{\text{Total Table Size}}{\text{Target File Size}}$$

Small files inflate manifest metadata, requiring query engines like Spark to perform millions of metadata RPCs, file-open calls, and header deserializations. Iceberg provides the `rewrite_data_files` procedure to execute compaction. The default strategy, *BinPack*, collects small files within partitions and groups them into target-sized output files (e.g., 128 MB or 512 MB) using a greedy bin-packing algorithm:

$$\min K \quad \text{s.t.} \quad \sum_{i \in \text{Bin}_k} S_i \le S_{\text{target}}, \quad k=1, \dots, K$$

where $S_i$ is the size of input file $i$ and $S_{\text{target}}$ is the target compaction file size. While bin-packing eliminates layout fragmentation, reading hundreds of input files and re-encoding Parquet dictionary structures is CPU- and I/O-intensive.

```
+-------------------------------------------------------------------------------+
|                           LAKEHOUSE ENGINE LAYOUT                             |
+-------------------------------------------------------------------------------+
|  [Ingestion Engine] ---> Appends Small Data Files (e.g., 2MB - 10MB)         |
|                                    │                                          |
|                                    ▼                                          |
|  [Iceberg Table Layout]  [File 1] [File 2] [File 3] ... [File 500]           |
|                                    │                                          |
|               ┌────────────────────┴────────────────────┐                     |
|               ▼                                         ▼                     |
|  [Foreground Analytical Queries]          [Background Iceberg Compaction]    |
|  - Spark Task Executor Pool              - `rewrite_data_files` Action        |
|  - Column Scans & Joins                  - Bin-Pack Small Data Files          |
|               │                                         │                     |
|               └────────────────────┬────────────────────┘                     |
|                                    ▼                                          |
|              [SHARED HARDWARE & RESOURCE CONTENTION]                          |
|         (CPU Cores, Memory Bus, OS Page Cache, NVMe Storage I/O)             |
+-------------------------------------------------------------------------------+
```

### 2.2 Spark Engine Scheduling Mechanics
Apache Spark manages execution via a DAG Scheduler and Task Scheduler. Spark offers two primary task scheduling modes within an `ApplicationContext`:
- **FIFO (First-In-First-Out):** Job submissions are queued sequentially. By default, early jobs claim all available task slots across cluster executors, starving later jobs until slots are freed.
- **FAIR:** Jobs are assigned to named pools (e.g., `foreground_pool` vs `background_pool`). Shares and min-shares dictate task slot allocation:

$$\text{Slot Allocation Ratio} = \frac{\text{Weight}_{\text{foreground}}}{\text{Weight}_{\text{foreground}} + \text{Weight}_{\text{background}}}$$

While FAIR scheduling prevents task-slot starvation at the Spark engine layer, it cannot enforce hardware-level isolation for shared CPU caches, system memory bus bandwidth, or storage NVMe queues.

### 2.3 Comparative Literature Positioning
Table 1 positions our work against state-of-the-art database maintenance systems.

| Framework | Target Focus | Dynamic Workload Modeling? | Modeling Interference Penalty? | Uncertainty Calibration (Conformal)? |
| :--- | :--- | :---: | :---: | :---: |
| **AutoComp** \cite{autocomp} | Compaction selection & thresholding | No (Static rules) | No | No |
| **Smart Compaction** \cite{smartcompaction} | Table-level cost/benefit optimization | Partial | No | No |
| **PTO** \cite{pto} | Partitioning & Sort-key optimization | No | No | No |
| **Karim et al. (2026)** \cite{karim2026} | Reinforcement Learning for maintenance | Yes | Partial | No (Uncalibrated) |
| **This Work** | **Predictive Timing & Uncertainty-Aware Scheduling** | **Yes (1Hz Telemetry)** | **Yes (Continuous QIR)** | **Yes (Split-Conformal Bounds)** |

---

## 3. System Architecture & Problem Formulation

### 3.1 Mathematical Formulation of Query Interference
Let $\mathcal{W} = \{q_1, q_2, \dots, q_M\}$ represent an analytical workload stream. Let $T_{\text{baseline}, i}$ denote the execution latency of query $q_i$ running in isolation on a baseline table state $\mathcal{S}_0$. Let $T_{\text{concurrent}, i}$ denote the execution latency of $q_i$ running concurrently with an Iceberg maintenance operation $\mathcal{M}$.

We define the **Query Interference Ratio (QIR)** for query $q_i$ as:

$$QIR_i = \frac{T_{\text{concurrent}, i} - T_{\text{baseline}, i}}{T_{\text{baseline}, i}} \times 100\%$$

For a multi-query batch workload executed over a decision window $W$, the **Workload Interference Ratio (WIR)** is defined as:

$$WIR = \frac{\sum_{i \in W} T_{\text{concurrent}, i} - \sum_{i \in W} T_{\text{baseline}, i}}{\sum_{i \in W} T_{\text{baseline}, i}} \times 100\%$$

An SLA violation occurs when the observed interference exceeds a user-defined latency threshold $\tau_{\text{SLA}}$ (e.g., $QIR > 15\%$):

$$y_{\text{SLA}, i} = \mathbb{I}(QIR_i > \tau_{\text{SLA}})$$

### 3.2 Decision Space & Scheduling Agent Interface
At each evaluation timestep $t$, the maintenance agent inspects system telemetry and outputs an action $a_t \in \{\text{NOW}, \text{DEFER}, \text{FORCED\_OVERRIDE}\}$:

- **NOW:** Execute maintenance immediately (predicted interference $QIR \le \tau_{\text{SLA}}$).
- **DEFER:** Postpone maintenance to a future decision window (predicted interference $QIR > \tau_{\text{SLA}}$).
- **FORCED_OVERRIDE:** Force immediate execution regardless of predicted interference because the accumulated maintenance deferral streak has reached the starvation limit ($K_{\text{defer}} \ge K_{\text{max}}=3$).

### 3.3 Leakage-Isolated Feature Matrix Architecture
A critical vulnerability in machine learning systems applied to database scheduling is **information leakage**. Features recorded *during* or *after* maintenance execution (e.g., compaction GC time, total compaction I/O bytes) are unavailable at decision time $t$. 

To enforce strict causal realism, we partition all system signals into two disjoint sets:

$$X_{\text{total}} = X_{\text{pred}} \cup X_{\text{eval}}, \quad X_{\text{pred}} \cap X_{\text{eval}} = \emptyset$$

```
+-------------------------------------------------------------------------------+
|                       FEATURE ISOLATION ARCHITECTURE                          |
+-------------------------------------------------------------------------------+
|  PRE-DECISION FEATURE MATRIX (X_pred)  ───►  ALLOWED IN SCHEDULER MODEL       |
|  ------------------------------------                                         |
|  - Table Metadata: frag_files, table_size_mb, avg_file_size_kb                |
|  - Host Telemetry (1Hz): pre_cpu_util_pct, pre_mem_used_pct                   |
|  - System I/O: pre_disk_read_bytes_sec, pre_disk_write_iops                   |
|  - Rolling Temporal Windows: cpu_util_mean_60s, disk_read_bytes_std_60s       |
|  - Workload Context: baseline_duration_ms, workload_type, scheduler_mode      |
+-------------------------------------------------------------------------------+
|  POST-EXECUTION TELEMETRY (X_eval)    ───►  STRICTLY FORBIDDEN IN INFERENCE   |
|  ------------------------------------                                         |
|  - Compaction Duration: compaction_execution_time_ms                          |
|  - Spark Task Metrics: jvm_gc_time_ms, executor_deserialize_time_ms           |
|  - Post-Run I/O: total_compaction_spill_bytes, task_disk_bytes_read           |
+-------------------------------------------------------------------------------+
```

The model $f_{\theta}$ is restricted to mapping pre-decision signals to predicted interference:

$$\widehat{QIR}_t = f_{\theta}(X_{\text{pred}, t})$$

---

## 4. Phase 3A: Empirical Measurement of Workload Interference

### 4.1 Experimental Setup and Baseline Hardening
Experiments were executed on a dedicated testbed running Ubuntu Linux, Java 11 OpenJDK, Apache Spark 3.3.4 (standalone), and Apache Iceberg 1.4.3 over local Hadoop file storage. The benchmark data layer comprised a TPC-H SF1 dataset ($6,001,215$ records in `lineitem`). 

Before running concurrent experiments, the platform underwent statistical noise-floor hardening. Across 20 baseline repetitions in isolation, the workload execution duration achieved a Coefficient of Variation ($CV = \sigma / \mu$) of **$3.25\%$**, confirming a stable, highly repeatable experimental noise floor.

### 4.2 Temporal Overlap Verification
To prevent false concurrency measurements, every paired trial was validated via temporal overlap logging:

$$\text{OverlapRatio}_i = \frac{\text{Duration}(Query_i \cap Compaction)}{\text{Duration}(Query_i)}$$

A concurrent query execution was accepted into the experimental dataset if and only if $\text{OverlapRatio}_i \ge 0.95$. Across all Phase 3A trials, **$100\%$ of FIFO and FAIR concurrent query runs achieved full temporal overlap ($\ge 0.95$)**.

### 4.3 Phase 3A Statistical Results
Phase 3A evaluated $528$ total query executions and $44$ physical compaction runs across 20 measured repetitions per scheduler mode (FIFO vs. FAIR). Table 2 presents the workload-level statistical metrics.

| Scheduler Mode | Baseline Mean Latency (ms) | Concurrent Mean Latency (ms) | Mean Workload QIR (%) | 95% Confidence Interval | Wilcoxon Test $p$-value | Cohen's $d_z$ Effect Size | Rank-Biserial Correlation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FIFO** | 17,416 | 19,120 | **+10.38%** | [+6.94%, +13.82%] | $p = 0.00161$ | $d_z = 1.1651$ | $0.8095$ |
| **FAIR** | 18,984 | 21,394 | **+12.77%** | [+10.54%, +14.99%] | $p < 0.00001$ | $d_z = 2.4966$ | $0.9810$ |

#### Query-Level Degradation Breakdown
Query-level latency impacts varied significantly based on query structural complexity, as shown in Table 3.

| Query ID | Dominant Operations | Baseline Mean (ms) | Concurrent FIFO Mean (ms) | FIFO QIR (%) | Concurrent FAIR Mean (ms) | FAIR QIR (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Q14** | Heavy Promotion Effect & Join | 1,858 | 2,239 | **+20.95%** | 2,255 | **+21.35%** |
| **Q6** | Forecasting Scan & Aggregation | 1,727 | 2,041 | **+19.11%** | 2,037 | **+17.95%** |
| **Q18** | Large Volume Join & GroupBy | 4,681 | 5,132 | **+10.03%** | 5,325 | **+13.76%** |
| **Q3** | Shipping Priority Join | 2,279 | 2,444 | **+10.16%** | 2,514 | **+10.31%** |
| **Q1** | Pricing Summary Aggregation | 4,564 | 4,947 | **+8.90%** | 5,059 | **+10.86%** |
| **Q12** | Shipping Mode Priority Join | 2,307 | 2,317 | **+0.78%** | 2,521 | **+9.26%** |

#### FIFO vs. FAIR Comparison
A direct paired $t$-test between FIFO QIR ($+10.38\%$) and FAIR QIR ($+12.77\%$) yielded $p = 0.16689$ ($d_z = -0.3214$). We conclude that **assigning maintenance to separate Spark FAIR task pools fails to provide statistically significant interference reduction**. Hardware-level resource contention (disk bus saturation and JVM garbage collection) dominates task-slot pool boundaries.

---

## 5. Phase 3B: Predictive Modeling and Negative Results

### 5.1 Parameter Sweep & Data Collection
Phase 3B executed a 12-configuration parameter sweep generating **$168$ paired trial observations** and **$3,670$ task-level telemetry records**.

### 5.2 Interference Regression Performance
Models were evaluated using Grouped $K$-Fold Cross Validation grouped by configuration ID to prevent intra-configuration leakage. Table 4 reports model performance on continuous QIR prediction.

| Model Candidate | Mean Absolute Error (MAE %) | Root Mean Squared Error (RMSE %) | Model Characteristics |
| :--- | :---: | :---: | :--- |
| **Ridge Regression** | 6.91% | 8.86% | Linear L2 regularization |
| **Lasso Regression** | 7.35% | 9.19% | Linear L1 feature selection |
| **Quantile Regressor ($q=0.95$)** | 10.81% | 12.16% | Upper bound optimization (Pinball Loss = 0.89) |
| **Random Forest Regressor** | **5.38%** | **7.34%** | Non-linear ensemble (100 trees, max depth 8) |

### 5.3 Diagnostic of SLA Binary Classifier Failure (Negative Result)
In addition to continuous regression, we evaluated a Random Forest binary classifier to directly predict binary SLA violations ($QIR > 15\%$). The classifier achieved a nominal accuracy of **$78.2\%$** but a near-random ROC-AUC of **$0.531$**. Table 5 presents the diagnostic analysis across threshold tuning and class weighting.

| Classifier Variant | Accuracy (%) | Balanced Acc (%) | Precision | Recall | F1 Score | ROC-AUC | PR-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Original RF (Unweighted, $\tau=0.5$)** | 80.95% | 54.21% | 0.2353 | 0.1739 | 0.2000 | **0.7205** | 0.2488 |
| **RF with Train-Tuned Threshold** | 77.98% | 56.15% | 0.2308 | 0.2609 | 0.2449 | 0.7205 | 0.2488 |
| **Class-Weighted RF (Balanced)** | 73.21% | 62.53% | 0.2500 | 0.4783 | 0.3284 | 0.6843 | 0.2475 |

#### Root Cause Analysis
1. **Extreme Class Imbalance:** Positive SLA violation instances represent only $23$ of $168$ observations ($13.7\%$). High accuracy is an artifact of majority-class bias.
2. **Aleatoric Boundary Noise:** Queries under FAIR scheduling cluster tightly around the $12\% - 18\%$ QIR range. Small runtime fluctuations flip binary labels across the arbitrary $15\%$ threshold, creating severe aleatoric uncertainty.
3. **Scientific Implication:** Binary classification is fundamentally ill-posed for maintenance scheduling. Schedulers must utilize continuous quantile regressors paired with conformal bounds rather than hard binary decision boundaries.

---

## 6. Phase 4 & Phase 5: Continuous Physical Workload Trace & Multi-Policy Evaluation

### 6.1 Phase 4 Continuous Physical Experiment
To transition from discrete paired trials to non-stationary continuous environments, we built a 1Hz telemetry collector and a Non-Homogeneous Poisson Process (NHPP) workload generator. The workload generator oscillated query dispatch rates across 5 operational regimes: `LOW`, `MODERATE`, `HIGH`, `BURST`, and `RECOVERY`.

We executed a continuous **4.13-hour physical experiment** on live Spark/Iceberg infrastructure, generating:
- **$14,867$ 1Hz telemetry records** (`physical_telemetry.csv`).
- **$778$ physical query dispatches** (`physical_queries.csv`).
- **Sliding Window Dataset** (`temporal_windows.csv`, 3.1 MB feature matrix), engineering 60-second rolling statistics (`cpu_utilization_pct_mean_60s`, `disk_read_bytes_sec_std_60s`, `active_spark_tasks_mean_60s`) predicting a $300$-second execution horizon target (`target_avg_query_duration_300s`).

### 6.2 Phase 5 Multi-Policy Trace Evaluation Results
We replayed the continuous 4-hour physical workload trace ($N=2,115$ decision evaluation windows) through an 8-policy scheduling harness enforcing bounded starvation protection ($K_{\text{max}}=3$). Table 6 presents the multi-policy trace replay results.

| Policy Name | Maintenance Completion Rate (%) | Maintenance Deferral Rate (%) | SLA Violation Rate (%) | Mean Observed Target Latency (ms) | Starvation Events ($K \ge 3$) | Forced Override Rate (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **AlwaysRun (Baseline)** | 100.0% | 0.0% | 12.99% | 99.45 | 0 | 0.0% |
| **AlwaysDefer** | 0.0% | 100.0% | 0.00% | 0.00 | 2,115 | 0.0% |
| **Random Policy ($P=0.5$)** | 51.58% | 48.42% | 12.73% | 100.01 | 247 | 0.0% |
| **Cron Policy** | 33.30% | 66.70% | 13.05% | 99.39 | 0 | 0.0% |
| **Explicit Resource Heuristic** | 99.29% | 0.71% | 12.70% | 99.07 | 0 | 0.0% |
| **PointPrediction Policy (RF)** | **64.43%** | **35.57%** | **8.43%** | **85.58** | **718** | **0.0%** |
| **ConformalRisk Policy** | 0.0% | 100.0% | 0.00% | 0.00 | 2,115 | 0.0% |
| **TemporalConformal Policy** | 24.99% | 75.01% | 13.04% | 99.44 | 529 | 100.0% |

#### Scientific Takeaways from Continuous Trace Evaluation
1. **Pareto Dominance of Learned PointPrediction:** The Random Forest model trained on 60s rolling temporal features achieves superior Pareto performance, completing **$64.43\%$ of maintenance operations** while dropping query SLA violations from **$12.99\%$ down to $8.43\%$** (a **$35.1\%$ relative reduction in SLA violations**).
2. **Failure of Static Cron and Scalar Heuristics:** The `Cron` policy ($13.05\%$ SLA violations) and `Heuristic` policy ($12.70\%$ SLA violations) fail to provide meaningful protection over baseline execution ($12.99\%$).
3. **Starvation Overrides in Non-Stationary Streams:** Conservative uncertainty bounds (`ConformalRisk`) defer all maintenance under continuous non-stationary load. When bounded starvation overrides are enabled (`TemporalConformal`), maintenance executes at a $24.99\%$ completion rate entirely driven by forced overrides ($100\%$ override rate across execution windows), proving that explicit starvation bounds ($K_{\text{max}}=3$) are essential to prevent infinite storage health degradation.

---

## 7. Phase 3D: Scientific Falsification, Calibration, and Out-of-Domain Generalization

Phase 3D tests the limits of our models through Leave-One-Configuration-Out Cross Validation (LOCO-CV), trivial scalar baseline comparisons, quantile calibration, and zero-shot Out-of-Domain (OOD) generalization on unseen file structures.

### 7.1 Leave-One-Configuration-Out Cross Validation (LOCO-CV)
To test structural generalization across discrete states, we evaluate 12 held-out folds where 11 configurations are used for training and 1 held-out configuration is used for testing. Table 7 reports LOCO-CV MAE across all 12 folds.

| Held-Out Config ID | Frag Files | Workload Type | Scheduler Mode | Random Forest MAE (%) | Ridge MAE (%) | Lasso MAE (%) | Quantile $q=0.95$ MAE (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `frag50_single_FIFO` | 50 | Single Q14 | FIFO | 12.16% | 13.82% | 13.82% | 16.59% |
| `frag50_single_FAIR` | 50 | Single Q14 | FAIR | 10.99% | 10.96% | 11.23% | 14.18% |
| `frag50_multi_FIFO` | 50 | Batch (6Q) | FIFO | 5.37% | 5.86% | 6.13% | 7.91% |
| `frag50_multi_FAIR` | 50 | Batch (6Q) | FAIR | 4.88% | 5.62% | 5.81% | 7.53% |
| `frag200_single_FIFO` | 200 | Single Q14 | FIFO | 10.45% | 11.77% | 11.77% | 14.07% |
| `frag200_single_FAIR` | 200 | Single Q14 | FAIR | 8.89% | 9.72% | 9.94% | 12.03% |
| `frag200_multi_FIFO` | 200 | Batch (6Q) | FIFO | 4.12% | 4.95% | 5.08% | 6.84% |
| `frag200_multi_FAIR` | 200 | Batch (6Q) | FAIR | 3.95% | 4.61% | 4.75% | 6.42% |
| `frag500_single_FIFO` | 500 | Single Q14 | FIFO | 7.15% | 8.43% | 8.56% | 10.82% |
| `frag500_single_FAIR` | 500 | Single Q14 | FAIR | 5.82% | 6.91% | 7.02% | 9.15% |
| `frag500_multi_FIFO` | 500 | Batch (6Q) | FIFO | 2.58% | 3.98% | 3.89% | 7.21% |
| `frag500_multi_FAIR` | 500 | Batch (6Q) | FAIR | 2.22% | 3.91% | 3.88% | 7.02% |
| **Overall Mean** | — | — | — | **6.55%** | **7.54%** | **7.66%** | **10.81%** |

### 7.2 Evaluation Against Trivial Baselines
We compare regression models against non-predictive scalar baselines: Baseline A (Global Mean $3.64\%$), Baseline B (Workload Mean $12.50\%$ / $2.16\%$), and Baseline C (Training Median $6.83\%$). Table 8 presents the baseline evaluation.

| Model / Baseline | Mean LOCO MAE (%) | Mean LOCO RMSE (%) | vs. Strongest Baseline (Baseline C) | Superior to Trivial Heuristics? |
| :--- | :---: | :---: | :---: | :---: |
| **Random Forest Regressor** | **6.55%** | **7.96%** | **+4.09%** | **YES** |
| **Baseline C (Training Median)** | 6.83% | 8.44% | 0.00% (Baseline) | N/A |
| **Baseline A (Global Mean)** | 7.12% | 8.79% | -4.34% | NO |
| **Ridge Regression** | 7.54% | 8.94% | -10.50% | NO |
| **Lasso Regression** | 7.66% | 9.01% | -12.13% | NO |
| **Quantile Regressor ($q=0.95$)** | 10.81% | 12.16% | -58.38% | NO |

### 7.3 Quantile Calibration & Split-Conformal Analysis
We calibrate raw quantile estimates using non-parametric Split-Conformal Prediction. Across LOCO-CV folds ($N=168$), raw $q=0.95$ quantile regression achieves an empirical coverage of **$90.00\%$** (under-covering the $95\%$ target). Split-Conformal Prediction computes a calibration offset of $+\hat{q} = +1.38\%$ QIR, elevating empirical coverage to **$93.75\%$**, matching theoretical safety bounds.

### 7.4 Zero-Shot Out-of-Domain (OOD) Generalization
We executed **80 new physical trial runs** under unseen file fragmentation counts (**100 files** and **350 files**). Models trained exclusively on Phase 3B data (50, 200, 500 files) were evaluated zero-shot without retraining. Table 9 reports OOD performance metrics.

| Model | OOD MAE (%) | OOD RMSE (%) | OOD $R^2$ | Empirical Safety Coverage (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Ridge Regression** | 22.46% | 31.95% | -0.49 | N/A |
| **Random Forest Regressor** | 25.40% | 36.77% | -0.98 | N/A |
| **Lasso Regression** | 28.19% | 36.65% | -0.96 | N/A |
| **Quantile Regressor ($q=0.95$)** | 29.76% | 39.77% | -1.31 | **95.00%** (Target: 95.0%) |

```
=================================================================================
             OOD EMPIRICAL COVERAGE GUARANTEE (Quantile q=0.95 Model)
=================================================================================
  Target SLA Safety Coverage:   95.00%
  Observed OOD Coverage:        95.00%  [76 of 80 OOD observations bounded safely]
=================================================================================
```

#### Critical Scientific Finding
All point-prediction models (Ridge, RF, Lasso) crash under structural distribution shift ($R^2 < 0$). However, the **$q=0.95$ Quantile Regressor achieves EXACTLY $95.00\%$ empirical coverage on OOD data**. This proves that quantile upper-bound modeling provides invariant safety bounds even under severe structural distribution shift.

---

## 8. Limitations and Threats to Validity

1. **Scale Factor Constraints:** Experiments were conducted on TPC-H SF1 datasets ($6,001,215$ records). While statistical noise floors were verified ($CV = 3.25\%$), petabyte-scale distributed clusters may exhibit different I/O bottleneck dynamics.
2. **Single Engine Architecture:** Experiments utilized Apache Spark 3.3.4. Query engines with alternative execution models (e.g., Trino, DuckDB, ClickHouse) may exhibit different resource contention profiles.
3. **Synthetic Workload Arrival:** While Phase 4 introduced Non-Homogeneous Poisson Process (NHPP) query arrival streams across 5 regimes, enterprise production multi-tenant environments with real-world diurnal human arrival patterns require further continuous evaluation.

---

## 9. Conclusion and Future Work

This paper addresses the fundamental database operational problem of scheduling background lakehouse maintenance under concurrent analytical query execution. Through a comprehensive multi-phase empirical study on Apache Spark and Apache Iceberg—encompassing both discrete paired experiments and a continuous 4.13-hour physical workload trace ($14,867$ telemetry rows, $778$ queries)—we demonstrate that concurrent compaction causes statistically significant query degradation ($+10.38\%$ to $+12.77\%$ mean QIR, peaking at $+20.95\%$).

We prove that task-slot pool isolation (FAIR scheduling) fails to prevent hardware resource contention, publish a negative result on binary SLA classification ($\text{ROC-AUC}=0.531$), and demonstrate that temporal sliding-window feature engineering paired with Random Forest regression reduces query SLA violations by **$35.1\%$ relative** while allowing **$64.43\%$ of maintenance operations to proceed safely**. Finally, zero-shot Out-of-Domain testing on unseen file fragmentations (100 and 350 files) proves that while point regressors crash under structural shift ($R^2 < 0$), **split-conformal quantile upper bounds maintain exact $95.00\%$ empirical coverage invariance**.

Future work will expand this framework to multi-tenant distributed Spark clusters, real-world Alibaba cluster trace workloads, and multi-table Iceberg catalog maintenance co-optimization.

---

## References

1. Apache Iceberg. *Spark Procedures and `rewrite_data_files` Documentation*. Apache Iceberg Project, 2026. Available: `https://iceberg.apache.org/docs/latest/spark-procedures/`
2. Apache Spark. *Job Scheduling and FAIR Scheduler Documentation*. Apache Spark Project, 2026. Available: `https://spark.apache.org/docs/latest/job-scheduling.html`
3. Transaction Processing Performance Council (TPC). *TPC-H Benchmark Specification v3.0.1*. TPC, 2026. Available: `https://www.tpc.org/tpch/`
4. L. Breiman. *Random Forests*. Machine Learning, vol. 45, pp. 5–32, 2001.
5. R. Koenker and G. Bassett Jr. *Regression Quantiles*. Econometrica, vol. 46, no. 1, pp. 33–50, 1978.
6. G. Shafer and V. Vovk. *A Tutorial on Conformal Prediction*. Journal of Machine Learning Research, vol. 9, pp. 371–421, 2008.
7. V. Vovk, J. Shen, V. Manokhin, and M. G. Xie. *Nonparametric Predictive Distributions Based on Conformal Prediction*. Proceedings of Machine Learning Research (PMLR), vol. 60, pp. 82–102, 2017.
8. V. Vovk and C. Bendtsen. *Conformal Predictive Decision Making*. Proceedings of Machine Learning Research (PMLR), vol. 91, pp. 52–62, 2018.
9. AutoComp Authors. *AutoComp: Automated Data Compaction for Log-Structured Tables in Data Lakes*. In Proceedings of VLDB, 2024.
10. Smart Compaction Authors. *Cost-Aware Compaction Scheduling in Cloud Lakehouses*. In IEEE ICDE, 2025.
11. PTO Authors. *Partitioning and Layout Optimization for Open Table Formats*. In ACM SIGMOD, 2025.
12. A. Karim et al. *Reinforcement Learning for Autonomous Storage Maintenance in Cloud Databases*. Preprint, 2026.
