# Phase 4 Output Manifest

This manifest documents all artifacts (CSVs and SVGs) generated during the Phase 4 Continuous Physical Experiment and Temporal ML Modeling.

## 1. Physical Experiment Outputs

The 4-8 hour continuous physical experiment using NHPP (Non-Homogeneous Poisson Process) regimes on live Spark/Iceberg produces these foundational datasets:

- **`physical_telemetry.csv`**
  - **Purpose**: Continuous 1Hz logging of system state.
  - **Columns**: `timestamp`, `cpu_utilization_pct`, `memory_used_pct`, `disk_read_bytes_sec`, `disk_write_bytes_sec`, `disk_read_iops`, `disk_write_iops`, `active_spark_jobs`, `active_spark_tasks`, `queued_queries`, `running_queries`, `compaction_active`, `frag_file_count`, `table_size_mb`, `last_query_duration_ms`, `last_compaction_duration_ms`.
  - **Interpretation**: This forms the fundamental chronological backbone of the ML dataset.

- **`physical_queries.csv`**
  - **Purpose**: Logs every physical query dispatched during the 4 hours.
  - **Columns**: `query_start_time`, `query_end_time`, `query_duration_ms`, `regime`, `query_type`, `query_id`, `status`.
  - **Interpretation**: Captures exact start and end times, allowing us to align query latency targets ($Y$) with the telemetry state.

## 2. Advanced Visualizations (Task 2)

These plots visually confirm the experiment execution and the effect of interference:

- **`telemetry_timeline.svg`**
  - **Purpose**: Displays the full 4-hour chronological timeline of CPU Utilization and Disk IOPS, with shaded gray regions indicating active background compaction.
  - **Interpretation**: Used to visually confirm that resource consumption spikes when Iceberg is rewriting data files.

- **`query_latency_timeline.svg`**
  - **Purpose**: Scatter plot mapping individual query execution times (log scale) across the timeline. Compaction regions are shaded.
  - **Interpretation**: Proves the existence of "Query Interference" – latency should exhibit vertical spikes during compaction blocks.

- **`regime_distribution.svg`**
  - **Purpose**: Bar chart showing the volume of queries executed under each NHPP regime (LOW, MODERATE, HIGH, BURST, RECOVERY).
  - **Interpretation**: Confirms the workload generator successfully oscillated between high-pressure and low-pressure states.

## 3. Temporal Window Engineering (Task 3)

Converts raw logs into a sliding window temporal dataset suitable for ML:

- **`temporal_windows.csv`**
  - **Purpose**: The final ML-ready chronological dataset.
  - **Columns**: Includes base 1Hz features + rolling 60s features (e.g. `cpu_utilization_pct_mean_60s`, `cpu_utilization_pct_std_60s`) + the target `target_avg_query_duration_300s` + chronological `split` marker (`train`, `val`, `test`).
  - **Interpretation**: A strict temporal mapping where features at time $t$ predict interference in window $t$ to $t+300$.

- **`rolling_feature_distributions.svg`**
  - **Purpose**: KDE plots comparing the density distribution of selected features (CPU mean, IOPS mean, Target) between the `train` split and `test` split.
  - **Interpretation**: Evaluates covariate shift – ensuring the chronological test set has similar support to the training set.

## 4. Chronological ML Modeling (Task 4)

Evaluates how well ML models predict future interference using chronological data:

- **`chronological_residuals.svg`**
  - **Purpose**: Scatter plot comparing the residual errors of the Baseline Point-In-Time model vs the Temporal-Aware (RidgeCV) model on the test block.
  - **Interpretation**: Demonstrates whether adding lag features (60s rolling windows) reduces error compared to instantaneous snapshots.

- **`temporal_conformal_coverage.svg`**
  - **Purpose**: Plots the predicted target along with the 95% conformal prediction upper/lower bounds. Actual test points are overlaid as dots/crosses depending on coverage.
  - **Interpretation**: Validates the uncertainty model on sequential, temporally-dependent data. A successful result shows empirical coverage close to the 95% target, unlike the collapsed coverage seen during OOD point-prediction.
