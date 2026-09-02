# Phase 3D Track 1 — Model Audit Summary

## 1. Overview & Dataset Audit
- **Predictive Dataset Path:** `scripts/phase3b-predictive-signals/results/dataset_predictive_signals.csv`
- **Total Observations:** 168 paired-trial observations (excluding warmups).
- **Configuration Structure:** 12 unique experimental configurations (`config_id`):
  - 3 Fragmentation Levels: 50, 200, 500 files
  - 2 Workload Intensities: `single_stream` (Q14) vs `multi_stream` (TPC-H 6-query batch: Q1, Q3, Q6, Q12, Q14, Q18)
  - 2 Scheduler Modes: `FIFO` vs `FAIR`
  - 4 Repetitions per configuration.

## 2. Prediction-Time Features ($X_{\text{pred}}$) vs. Forbidden Features
- **Allowed Prediction-Time Features (10 Numerical + One-Hot Categoricals + Bias):**
  - Physical Table Metadata: `frag_files`, `table_size_mb`, `avg_file_size_kb`
  - Pre-decision Host CPU & Memory: `pre_cpu_util_pct`, `pre_mem_used_pct`
  - Pre-decision Host Disk I/O: `pre_disk_read_bytes_sec`, `pre_disk_write_bytes_sec`, `pre_disk_read_iops`, `pre_disk_write_iops`
  - Baseline Query Latency Reference: `baseline_duration_ms`
  - One-Hot Categoricals: `workload_type`, `scheduler_mode`, `query`
  - Intercept / Bias: `1.0`
- **Forbidden Execution / Telemetry Features (Data Leakage Protection):**
  - `concurrent_duration_ms`, `qir_pct`, `sla_violation_10pct`

## 3. Model Architecture & Preprocessing
- **Feature Scaling:** Numerical features scaled strictly using mean and std computed on training fold data:
  $$\hat{x}_{ij} = \frac{x_{ij} - \mu_{j,\text{train}}}{\sigma_{j,\text{train}} + \epsilon}$$
- **Random Forest Regressor:** Ensemble of decision trees (`SimpleTreeRegressor`, `max_depth=3`, `min_samples_split=4`) trained via bootstrap resampling (`random.seed(42)`).
- **Pinball Loss Quantile Regressor ($q=0.95$):** Linear gradient descent minimizing pinball loss $L_{q}(y, \hat{y}) = \max(q(y - \hat{y}), (q - 1)(y - \hat{y}))$ with learning rate $\eta=0.01$ over 300 epochs, initialized with bias $+10.0$.
- **Validation Methodology:** GroupKFold cross-validation grouped strictly by `config_id` to prevent cross-configuration data leakage.
