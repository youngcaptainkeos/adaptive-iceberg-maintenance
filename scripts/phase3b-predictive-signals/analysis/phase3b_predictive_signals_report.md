# Phase 3B: Interference Characterization & Predictive Signals Report (Corrected)

## 1. Executive Summary
This report presents the Phase 3B empirical evaluation, establishing a leak-free dataset and exploratory predictive modeling framework to forecast query interference ratio (QIR) before deciding whether to launch Apache Iceberg data-file compaction (`rewrite_data_files`).

## 2. Multi-Factor Parameter Sweep Matrix & Configuration Limitations
- **Total Measured Samples**: 168 paired trial samples across counterbalanced repetitions.
- **Total Unique Configurations**: 12 unique parameter configurations ($3 \text{ frag levels} \times 2 \text{ workload intensities} \times 2 \text{ scheduler modes}$).
- **Factor 1 (Fragmentation Level)**: 50 partitions (~3.3 MB avg size), 200 partitions (~842 KB avg size), 500 partitions (~330 KB avg size).
- **Factor 2 (Workload Intensity)**: Single-Stream Query (Q14) vs Multi-Stream Batch (TPC-H 6-query suite: Q1, Q3, Q6, Q12, Q14, Q18).
- **Factor 3 (Scheduler Mode)**: FIFO vs FAIR pool allocation.

> [!WARNING]
> **Configuration Diversity Limitation**: While the dataset contains 168 observations, they are nested within a limited set of 12 experimental configurations. GroupKFold cross-validation by `config_id` strictly prevents intra-config sample leakage, but all predictive modeling findings must be interpreted as **exploratory predictive modeling under limited configuration diversity** rather than proof of broad generalization.

## 3. Strict Prediction-Time Feature Availability Constraint ($X_{\text{pred}}$)
> [!IMPORTANT]
> **Anti-Leakage Guardrail**: All predictive models rely strictly on pre-decision features ($X_{\text{pred}}$) observable before the maintenance scheduling decision is made. During/post-execution telemetry is strictly isolated for offline analysis.

### Pre-Decision Features ($X_{\text{pred}}$):
- Physical Layout Metadata: `frag_files`, `table_size_mb`, `avg_file_size_kb`
- Host System Load (Pre-Decision Sample): `pre_cpu_util_pct`, `pre_mem_used_pct`
- Host Storage Throughput (Pre-Decision Sample): `pre_disk_read_bytes_sec`, `pre_disk_write_bytes_sec`, `pre_disk_read_iops`, `pre_disk_write_iops`
- Baseline Latency Reference: `baseline_duration_ms`
- Execution Context: `workload_type`, `scheduler_mode`, `query`

## 4. Model Evaluation & Scientific Diagnostic Corrective Analysis
Models were evaluated using **GroupKFold cross-validation** grouped strictly by `config_id` across unseen configurations.

| Model | Model Type | MAE / Acc | RMSE / ROC-AUC | Primary Metric |
|-------|------------|-----------|----------------|----------------|
| Ridge Regression (L2) | Regression | 6.91% | 8.86% | MAE / RMSE |
| Lasso Regression (L1) | Regression | 7.35% | 9.19% | MAE / RMSE |
| Random Forest Regressor | Regression (Continuous QIR) | 5.38% | 7.34% | MAE / RMSE |
| Quantile Regressor (95th %ile) | Quantile Upper Bound | Pinball: 0.89 | N/A | Pinball Loss (q=0.95) |
| Random Forest Classifier | SLA Violation (10%) | Acc: 76.8% | ROC-AUC: 0.522 | Diagnostic Matrix |

### A. Correct SLA Classifier Diagnostic Interpretation
- **Class Distribution**: Class 0 ($\\le 10\\% \\text{ QIR}$) = 145 samples (86.3\\%), Class 1 ($> 10\\% \\text{ QIR}$) = 23 samples (13.7\\%).
- **Confusion Matrix**: TP = 4, FP = 20, TN = 125, FN = 19.
- **Diagnostic Metrics**: Precision = 0.167, Recall = 0.174, F1-Score = 0.170, Balanced Accuracy = 51.8\\%, PR-AUC = 0.131.
> [!CAUTION]
> **Corrective Interpretation**: The raw accuracy of 76.8\\% is driven entirely by severe class imbalance (majority class baseline = 86.3\\%) rather than predictive power. An ROC-AUC of 0.522 (\\approx 0.5) confirms that binary SLA violation classification performs near random guessing in this dataset. Binary SLA classification capability is **NOT** established.

### B. Correct Quantile Regression Interpretation
> [!NOTE]
> The $q=0.95$ quantile regression model provides a **conservative conditional upper-bound estimate** of expected interference. It does **NOT** compute or represent a calibrated probability estimate $P(\text{QIR} > 10\%)$. It serves solely as a risk-averse thresholding bound for decision policies.

### C. Strongest Valid Result: Continuous QIR Regression
The strongest valid Phase 3B predictive finding is continuous QIR forecasting using the **Random Forest Regressor**, achieving an **MAE of 5.38% QIR** and **RMSE of 7.34% QIR**. This provides promising exploratory evidence that continuous interference ratio can be estimated from pre-decision signals.

## 5. Conclusions & Transition to Phase 3C Policy Evaluation
1. **Exploratory Predictive Capability**: Continuous QIR regression demonstrates that pre-decision physical layout and system signals contain predictive signal for query interference.
2. **Foundation for Phase 3C**: The continuous Random Forest regressor and conservative 95th-percentile quantile bound will be evaluated as decision functions inside the Phase 3C uncertainty-aware maintenance scheduler.
