# Capstone Data Pipeline Audit Report

## 1. Inventory Summary
- **Total CSV Files Analyzed**: 112
- **Total Telemetry Rows**: 58,630
- **Sources with Temporal Features**: 38

## 2. Assessment of Temporal ML Feasibility ($X_{t-k:t} \rightarrow Y_{t+h}$)
Based on the audit, the current telemetry pipeline collects timestamps and sequences (e.g., `window_id`, `launch_time`, `finish_time`, `timestamp`). However, the data is heavily fragmented across independent short-lived experiment phases (Phase 3a, 3b, 3c, etc.) rather than a continuous, contiguous timeline.

**Gap Analysis:**
- **Fragmentation**: Data is generated in isolated runs. A true temporal dataset requires a long, continuous history (hours or days) to capture seasonality, gradual fragmentation build-up, and sustained interference patterns.
- **Sampling Frequency**: System metrics are collected, but Spark task telemetry is bound to discrete query execution windows. The connection between background compaction events and continuous query streams is broken between experiment boundaries.
- **State Transitions**: To model sequences $X_{t-k:t} \rightarrow Y_{t+h}$, the state matrix $X$ needs continuous system state, table state, and queue state. The current setup only logs final table states or discrete metric snapshots per phase.

**Conclusion**: The existing data is **insufficient** to construct a valid, industry-relevant temporal machine-learning dataset without heavy synthetic generation or interpolation.

## 3. Recommendation for New Physical Experiment
**Minimum Viable Temporal Experiment (Continuous Workload Trace)**
To generate an industry-relevant dataset, a new experiment must be executed with the following specifications:
1. **Duration**: 4-8 hours of contiguous execution without restarting the Spark cluster or resetting the Iceberg table.
2. **Workload Stream**: A Poisson-distributed arrival of queries (both reads and updates) representing daily cyclical load.
3. **Background Maintenance**: Background compaction processes running concurrently, driven by actual file fragmentation counts, generating realistic interference.
4. **Unified Telemetry Logger (Global Clock Sync)**: A daemon that outputs `(timestamp, cpu, mem, active_tasks, queued_tasks, maintenance_status)` at a fixed frequency (e.g., 1Hz). This is critical for ML sequence modeling.

## 4. Detailed Telemetry Inventory (Top 50)
| File | Rows | Has Temporal | Temporal Columns |
|---|---|---|---|
| `cab/benchmark-results/snowflake_individual_1h_38s_4tb/all.csv` | 7516 | True | `runtime` |
| `cab/benchmark-results/snowflake_shared_1h_32s_4tb/all.csv` | 7516 | True | `runtime` |
| `cab/benchmark-results/snowflake_shared_1h_16s_1tb/all.csv` | 5508 | True | `runtime` |
| `cab/benchmark-results/snowflake_shared_1h_2s_1tb/all.csv` | 5508 | True | `runtime` |
| `cab/benchmark-results/snowflake_shared_1h_4s_1tb/all.csv` | 5508 | True | `runtime` |
| `cab/benchmark-results/snowflake_shared_1h_8s_1tb/all.csv` | 5508 | True | `runtime` |
| `scripts/phase3-concurrent-interference/results/task_telemetry.csv` | 4994 | True | `launch_time, finish_time, cpu_time_ms, gc_time_ms` |
| `scripts/phase3b-predictive-signals/results/phase3b_task_telemetry.csv` | 3670 | True | `launch_time, finish_time, executor_cpu_time_ms, jvm_gc_time_ms, deserialize_time_ms, serialize_time_ms` |
| `scripts/phase3b-predictive-signals/results/phase3b_system_metrics.csv` | 3493 | True | `timestamp` |
| `scripts/phase3-concurrent-interference/results/stage_telemetry.csv` | 1166 | True | `submission_time, completion_time` |
| `scripts/phase3-concurrent-interference/results/telemetry_extracted.csv` | 1166 | True | `spark_start_time, spark_end_time, compaction_start_time, compaction_end_time` |
| `scripts/phase3c-uncertainty-aware-scheduler/results/policy_decisions.csv` | 840 | True | `window_id` |
| `scripts/phase3d-validation-generalization/results/loco_fold_predictions.csv` | 672 | False | `None` |
| `scripts/phase3-concurrent-interference/results/query_runs.csv` | 528 | True | `client_start_time, client_end_time` |
| `scripts/phase3b-predictive-signals/results/phase3b_query_runs.csv` | 420 | True | `client_start_time, client_end_time` |
| `scripts/phase2-validated-layout-comparison/results/raw_statement_results.csv` | 396 | False | `None` |
| `scripts/phase2-validated-layout-comparison/results/raw_telemetry.csv` | 396 | True | `start_time, end_time` |
| `scripts/phase3-concurrent-interference/results/overlap_validation.csv` | 264 | True | `query_start_time, query_end_time, compaction_start_time, compaction_end_time` |
| `scripts/phase3-concurrent-interference/results/overlap_vs_interference.csv` | 264 | False | `None` |
| `scripts/phase2-task-telemetry-verification/results/task_telemetry_raw.csv` | 254 | True | `launch_time, finish_time, executor_run_time_ms, executor_cpu_time_ms, jvm_gc_time_ms, executor_deserialize_time_ms, result_serialization_time_ms` |
| `scripts/phase2-compaction/results/pre_compaction_file_metrics.csv` | 200 | False | `None` |
| `scripts/phase2-fragmentation/results/fragmented_file_metrics.csv` | 200 | False | `None` |
| `scripts/phase3b-predictive-signals/results/dataset_predictive_signals.csv` | 168 | True | `client_start_time_concurrent, client_end_time_concurrent` |
| `scripts/phase3d-validation-generalization/results/conformal_predictions.csv` | 168 | False | `None` |
| `scripts/phase3d-validation-generalization/results/quantile_raw_predictions.csv` | 168 | False | `None` |
| `scripts/phase2-statistical-validation/results/paired_observations.csv` | 140 | False | `None` |
| `scripts/phase2-validated-layout-comparison/results/paired_state_differences.csv` | 140 | True | `control_runtime, fragmented_runtime, compacted_runtime` |
| `scripts/phase2-methodology-validation/results/noise_floor_statement_results.csv` | 132 | True | `start_time, end_time` |
| `scripts/phase3d-validation-generalization/results/ood_compaction_runs.csv` | 100 | False | `None` |
| `scripts/phase3d-validation-generalization/results/ood_system_metrics.csv` | 100 | True | `timestamp` |
| `scripts/phase3f-scheduler-validation/results/extrapolation_compaction_runs.csv` | 100 | False | `None` |
| `scripts/phase3f-scheduler-validation/results/extrapolation_system_metrics.csv` | 100 | True | `timestamp` |
| `scripts/phase3e-adaptive-scheduler/results/adaptive_policy_pareto_results.csv` | 98 | False | `None` |
| `scripts/phase3d-validation-generalization/results/ood_experiment_results.csv` | 80 | True | `timestamp_start, timestamp_end` |
| `scripts/phase3d-validation-generalization/results/ood_predictions.csv` | 80 | False | `None` |
| `scripts/phase3f-scheduler-validation/results/extrapolation_experiment_results.csv` | 80 | True | `timestamp_start, timestamp_end` |
| `scripts/phase2-task-telemetry-verification/results/stage_telemetry_summary.csv` | 63 | False | `None` |
| `scripts/phase3b-predictive-signals/results/phase3b_compaction_runs.csv` | 60 | True | `client_start_time, client_end_time` |
| `scripts/phase3b-predictive-signals/results/phase3b_pre_decision_signals.csv` | 60 | True | `decision_timestamp` |
| `scripts/phase3e-adaptive-scheduler/results/starvation_protection_results.csv` | 50 | False | `None` |
| `scripts/phase3d-validation-generalization/results/loco_regression_results.csv` | 48 | False | `None` |
| `scripts/phase3e-adaptive-scheduler/results/threshold_sweep_results.csv` | 48 | False | `None` |
| `scripts/phase3-concurrent-interference/results/compaction_runs.csv` | 44 | True | `client_start_time, client_end_time` |
| `scripts/phase3d-validation-generalization/results/dataset_audit.csv` | 24 | False | `None` |
| `scripts/phase2-validated-layout-comparison/results/execution_order.csv` | 22 | False | `None` |
| `scripts/phase2-statistical-hardening/results/statistical_hardened_results.csv` | 21 | False | `None` |
| `scripts/phase2-statistical-validation/results/formal_statistical_tests.csv` | 21 | False | `None` |
| `scripts/phase2-statistical-validation/results/normality_tests.csv` | 21 | False | `None` |
| `scripts/phase2-statistical-validation/results/paired_difference_summary.csv` | 21 | False | `None` |
| `scripts/phase2-statistical-validation/results/per_state_variability.csv` | 21 | False | `None` |
