# Phase 3A: Concurrent Workload Interference Report

## 1. Executive Summary
This report presents the empirical results of Phase 3A, evaluating the performance interference caused by background Apache Iceberg compaction operations (`rewrite_data_files`) on concurrent analytical TPC-H query workloads under FIFO and FAIR Spark scheduling modes.

## 2. Experimental Setup & Concurrency Harness Design
- **Physical Layout**: 200-partition fragmented state (`local.experiment.interference_treatment`).
- **Compaction Operation**: Iceberg `rewrite_data_files` bin-pack compaction.
- **Scheduling Modes**: Default FIFO vs Custom FAIR (`foreground` pool: minShare=12, weight=3; `background` pool: minShare=4, weight=1).
- **Repetitions**: 22 total repetitions per mode (2 warmup + 20 measured repetitions) with counterbalanced ordering.

## 3. Temporal Overlap & Contention Analysis
- **Full Overlap (ratio >= 0.95)**: 264 runs
- **Partial Overlap (0.0 < ratio < 0.95)**: 0 runs
- **No Overlap (ratio = 0.0)**: 0 runs

## 4. Quantitative Interference Results & Statistical Testing
| Mode | Query | Baseline Mean (ms) | Concurrent Mean (ms) | QIR Mean (%) | 95% CI of QIR (%) |
|------|-------|-------------------|----------------------|--------------|-------------------|
| FAIR | Q1 | 4950.09 | 5463.42 | 10.86% | [6.55%, 15.18%] |
| FAIR | Q12 | 2459.85 | 2686.00 | 9.26% | [4.04%, 14.49%] |
| FAIR | Q14 | 2103.90 | 2554.75 | 21.35% | [13.11%, 29.58%] |
| FAIR | Q18 | 5081.12 | 5748.77 | 13.76% | [10.67%, 16.85%] |
| FAIR | Q3 | 2439.64 | 2671.14 | 10.31% | [3.50%, 17.13%] |
| FAIR | Q6 | 1949.04 | 2269.60 | 17.95% | [11.25%, 24.66%] |
| FAIR | Workload | 18983.64 | 21393.68 | 12.77% | [10.54%, 14.99%] |
| FIFO | Q1 | 4563.50 | 4947.04 | 8.90% | [5.04%, 12.77%] |
| FIFO | Q12 | 2306.52 | 2317.11 | 0.78% | [-3.03%, 4.59%] |
| FIFO | Q14 | 1857.90 | 2239.04 | 20.95% | [15.54%, 26.36%] |
| FIFO | Q18 | 4681.49 | 5131.66 | 10.03% | [6.61%, 13.44%] |
| FIFO | Q3 | 2279.23 | 2444.04 | 10.16% | [3.11%, 17.21%] |
| FIFO | Q6 | 1727.37 | 2041.38 | 19.11% | [12.44%, 25.77%] |
| FIFO | Workload | 17416.01 | 19120.25 | 10.38% | [6.94%, 13.82%] |

## 5. Empirical Findings: FIFO vs FAIR Scheduler Performance
- **Observed Workload Interference**: Under FIFO mode, concurrent background compaction increased total workload execution time by +10.38% (95% CI: [+6.94%, +13.82%], p = 0.00161, Cohen's d_z = 1.1651). Under FAIR mode, workload execution time increased by +12.77% (95% CI: [+10.54%, +14.99%], p < 0.00001, Cohen's d_z = 2.4966).
- **Statistical Comparison**: A paired comparison between FIFO and FAIR workload QIR showed no statistically significant difference (t = -1.4373, p = 0.16689; Wilcoxon p = 0.21106, Cohen's d_z = -0.3214).
- **Query-Level Sensitivity**: In both modes, query Q14 (+20.95% FIFO, +21.35% FAIR) and query Q6 (+19.11% FIFO, +17.95% FAIR) experienced the highest statistically significant latency spikes.

## 6. Telemetry Observations & Candidate Mechanisms
- **Direct Observations (Telemetry-Supported)**:
  1. Spark event log inspection confirms `SET spark.scheduler.pool` correctly assigned queries to `foreground` and compaction jobs to `background` pools in FAIR mode.
  2. Task event telemetry confirms concurrent execution of foreground query tasks and background compaction tasks in FAIR mode.
- **Candidate Explanations (Unmeasured Hypotheses)**:
  1. *Resource Bottlenecks*: Shared disk I/O bandwidth, OS page-cache churn, or memory bandwidth saturation may limit performance recovery under FAIR scheduling, but hardware-level counters (e.g. iostat, page cache hit ratios) were not directly logged.
  2. *JVM/Scheduler Overhead*: Thread context-switching or JVM GC pause times under dual-pool scheduling are unmeasured candidate explanations for higher baseline latencies under FAIR mode.

## 7. Threats to Validity & Methodological Safeguards
- **Counterbalancing**: Swapped baseline/concurrent phase ordering across repetitions to control for state and warmup bias.
- **Resilient Logging**: Atomic CSV flushing and workspace event-log persistence.

## 8. Conclusions & Research Directions
Empirical evidence demonstrates that background Iceberg compaction causes statistically significant latency degradation (+10% to +21%) for concurrent analytical queries. Configuring Spark FAIR pool allocations alone does not eliminate workload interference in a single-driver local setup, highlighting the need for predictive scheduling signals and uncertainty-aware maintenance policies in Phase 3B.
