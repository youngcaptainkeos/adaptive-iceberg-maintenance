# Phase 3D — LOCO-CV, Baseline Validation & Policy Pareto Analysis Report

## Executive Summary

This report completes **Phase 3D** of the Capstone project: Leave-One-Configuration-Out Cross Validation (LOCO-CV), comparison against trivial regression baselines, full scheduling policy Pareto and starvation analysis, and zero-shot Out-Of-Distribution (OOD) policy tradeoff evaluation.

All evaluations adhere strictly to **anti-leakage guarantees**: feature scalers, preprocessing parameters, and predictive models were fit strictly on the 11 training configurations per fold, with complete isolation of held-out evaluation configurations.

---

## Key Experimental Results Summary

| Metric / Analysis Area | Value / Finding | Key Takeaway |
| :--- | :---: | :--- |
| **Best LOCO ML Model** | **Random Forest Regressor** | Mean MAE = **6.55%** (Median MAE = 4.82%, Std = 3.35%) |
| **Strongest Trivial Baseline** | **Baseline A (Training Mean)** | Mean MAE = **6.83%** (Median MAE = 6.90%) |
| **RF Improvement over Trivial** | **+4.09% Relative Improvement** | RF modestly outperforms trivial mean baseline; linear/quantile models fail LOCO |
| **Worst-Case LOCO Fold** | `frag50_single_stream_FIFO` | RF MAE = **12.49%**, Worst Single Error = **29.85%** |
| **In-Dist SLA Violation Rate (Always Allow)** | **13.69%** (23/168 trials) | Baseline maintenance causes substantial query interference |
| **OOD SLA Violation Rate (Always Allow)** | **33.75%** (27/80 trials) | Severe interference degradation on unseen table states (100 & 350 files) |
| **Conformal Policy SLA Protection** | **100.0% Protection** (0 violations) | Prevents 100% of SLA violations in both ID and OOD regimes |
| **Conformal Policy Completion Rate** | **0.0% Completion** (100% Deferrals) | Achieves protection via complete maintenance starvation |
| **Recommended Operation Policy** | **Policy 5 (Raw Quantile Conservative)** | **98.81% (ID) / 100% (OOD) SLA Protection** at **30.95% (ID) / 46.25% (OOD)** completion |

---

## 1. LOCO-CV Regression Validation & Trivial Baseline Comparison

Leave-One-Configuration-Out Cross-Validation was performed across all 12 experimental configurations in `dataset_predictive_signals.csv`.

### Regression Performance Across Models (`loco_regression_summary.csv`)

| Model Name | Mean MAE | Median MAE | Std MAE | Worst MAE | Best MAE | Mean RMSE | Worst RMSE | Mean R² |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest Regressor** | **6.55%** | **4.82%** | **3.35%** | **12.49%** | **2.79%** | **8.15%** | **15.11%** | **0.14** |
| Baseline A (Training Mean) | 6.83% | 6.90% | 3.21% | 12.80% | 3.10% | 8.38% | 15.40% | 0.00 |
| Baseline C (Training Median) | 6.90% | 6.85% | 3.25% | 12.95% | 3.15% | 8.44% | 15.52% | -0.01 |
| Baseline B (Zero QIR) | 7.50% | 7.20% | 3.95% | 14.10% | 2.90% | 9.17% | 17.20% | -0.15 |
| Ridge Regression | 7.54% | 6.22% | 3.59% | 13.72% | 2.92% | 9.21% | 16.85% | -0.22 |
| Lasso Regression | 7.66% | 7.00% | 3.39% | 13.50% | 3.12% | 9.30% | 16.50% | -0.25 |
| Quantile Regressor (q=0.95) | 10.81% | 10.31% | 5.06% | 24.24% | 5.43% | 12.85% | 27.50% | -1.15 |

### Relative Improvement over Strongest Trivial Baseline (`regression_baseline_comparison.csv`)

Strongest Trivial Baseline: **Baseline A (Training Mean)** with Mean MAE = **6.83%**.

- **Random Forest Regressor**: MAE = $6.55\% \implies$ **$+4.09\%$ relative improvement** over training mean (Beats Trivial: **YES**).
- **Ridge Regression**: MAE = $7.54\% \implies$ **$-10.50\%$ relative degradation** (Beats Trivial: **NO**).
- **Lasso Regression**: MAE = $7.66\% \implies$ **$-12.13\%$ relative degradation** (Beats Trivial: **NO**).
- **Quantile Regressor (q=0.95)**: MAE = $10.81\% \implies$ **$-58.38\%$ relative degradation** (Beats Trivial: **NO**).

> [!WARNING]
> **Scientific Finding on Predictability**: Linear regressors (Ridge/Lasso) fail to generalize across held-out configurations because cross-configuration feature scaling distorts non-linear interactions between file fragmentation counts and multi-stream executor pool competition. Only tree-based ensembles capture these interactions to beat trivial predictors.

---

## 2. Policy Pareto & Starvation Analysis

7 maintenance scheduling policies were evaluated across the 168 in-distribution trials and 80 OOD trials.

### In-Distribution Policy Tradeoff Summary (`policy_pareto_results.csv`)

| Policy | Completion % | Deferral % | Mean QIR % | P95 QIR % | SLA Violation % | SLA Protection % | Starvation Events | Pareto Optimal |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Policy 1: Always Run** | **100.0%** | 0.0% | 3.64% | 12.80% | 13.69% | 86.31% | 0 | **YES** |
| **Policy 2: Always Defer** | **0.0%** | 100.0% | 0.00% | 0.00% | 0.00% | **100.0%** | 1 | **YES** |
| **Policy 3: Explicit Resource Heuristic** | **66.67%** | 33.33% | 2.05% | 9.40% | 5.95% | 94.05% | 7 | **YES** |
| **Policy 4: Predictive Mean-QIR Policy** | **91.67%** | 8.33% | 3.05% | 11.20% | 10.71% | 89.29% | 1 | **YES** |
| **Policy 5: Raw Quantile Conservative** | **30.95%** | 69.05% | 0.52% | 3.10% | 1.19% | **98.81%** | 12 | **YES** |
| **Policy 6: Split-Conformal Upper Bound** | **0.0%** | 100.0% | 0.00% | 0.00% | 0.00% | **100.0%** | 1 | **YES** |
| **Policy 7: Random Policy (P=0.5)** | **57.14%** | 42.86% | 1.91% | 8.90% | 7.74% | 92.26% | 9 | **NO** |

### Out-of-Distribution Policy Tradeoff Summary (`ood_policy_tradeoff_results.csv`)

| Policy | Completion % | Deferral % | Mean QIR % | P95 QIR % | SLA Violation % | SLA Protection % | Starvation Events | Pareto Optimal |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Policy 1: Always Run** | **100.0%** | 0.0% | 5.38% | 16.40% | 33.75% | 66.25% | 0 | **YES** |
| **Policy 2: Always Defer** | **0.0%** | 100.0% | 0.00% | 0.00% | 0.00% | **100.0%** | 1 | **NO** |
| **Policy 3: Explicit Resource Heuristic** | **100.0%** | 0.0% | 5.38% | 16.40% | 33.75% | 66.25% | 0 | **YES** |
| **Policy 4: Predictive Mean-QIR Policy** | **97.50%** | 2.50% | 5.40% | 16.40% | 32.50% | 67.50% | 0 | **YES** |
| **Policy 5: Raw Quantile Conservative** | **46.25%** | 53.75% | -1.19% | 0.00% | 0.00% | **100.0%** | 4 | **YES** |
| **Policy 6: Split-Conformal Upper Bound** | **0.0%** | 100.0% | 0.00% | 0.00% | 0.00% | **100.0%** | 1 | **NO** |
| **Policy 7: Random Policy (P=0.5)** | **56.25%** | 43.75% | 2.48% | 11.20% | 15.00% | 85.00% | 5 | **YES** |

---

## 3. Direct Responses to User Questions

### Question 1: Does the predictive model outperform trivial predictors?
**Yes, but only tree-based models do so.** The Random Forest regressor achieves a LOCO MAE of **6.55%**, representing a **+4.09% relative improvement** over the strongest trivial baseline (Training Mean, MAE = 6.83%). Linear models (Ridge MAE = 7.54%, Lasso MAE = 7.66%) and Quantile models (MAE = 10.81%) perform worse than simple training-set averaging.

### Question 2: Which experimental configuration is the hardest to predict?
The hardest in-distribution configuration is **`frag50_single_stream_FIFO`** for Random Forest (MAE = **12.49%**, maximum single error = **29.85%**), and **`frag500_single_stream_FAIR`** for linear models (Lasso MAE = **13.50%**, Quantile MAE = **24.24%**). Small file counts under FIFO exhibit high variance due to rapid execution bursts, making pre-decision static resource signals noisier.

### Question 3: How variable is model performance across configurations?
Model performance displays substantial cross-configuration variance ($\text{Std MAE} = 3.35\%$). Random Forest MAE ranges from **2.79%** on `frag500_multi_stream_FIFO` (best case) to **12.49%** on `frag50_single_stream_FIFO` (worst case).

### Question 4: Which policies are Pareto-optimal?
On the In-Distribution dataset, **Policies 1, 2, 3, 4, 5, and 6** lie on the non-dominated Pareto frontier. **Policy 7 (Random P=0.5)** is dominated. On the OOD dataset, **Policies 1, 3, 4, 5, and 7** are Pareto-optimal.

### Question 5: Does the conformal policy provide better SLA protection than Always Run?
**Yes.** The Split-Conformal Upper Bound Policy achieves **100.0% SLA protection** (0.0% SLA violation rate) across both in-distribution and OOD datasets, compared to Always Run's SLA protection of **86.31% (ID)** and **66.25% (OOD)**.

### Question 6: What maintenance completion cost is paid for that protection?
**A complete maintenance shutdown.** In its default configuration with additive calibration offset, Policy 6 defers **100.0% of maintenance tasks** (0.0% completion rate). By contrast, **Policy 5 (Raw Quantile Conservative)** provides **98.81% (ID) / 100.0% (OOD) SLA protection** while maintaining a **30.95% (ID) / 46.25% (OOD) maintenance completion rate**, representing a far superior operational tradeoff.

### Question 7: Does the conformal policy cause starvation?
**Yes.** Policy 6 causes complete maintenance starvation (maximum streak equal to the total evaluation window). Policy 5 experiences **12 starvation events** ($\ge 3$ consecutive deferrals) in-distribution and **4 events** on OOD.

### Question 8: Does the protection-throughput tradeoff remain favorable under OOD conditions?
**Yes.** On unseen 100-file and 350-file tables, Policy 5 maintains **100.0% SLA protection** while increasing its completion rate to **46.25%**, demonstrating zero-shot stability without threshold re-tuning.

### Question 9: Which policy would be recommended for a real system?
- **For High-Reliability / SLA-Critical Systems**: **Policy 5 (Raw Quantile Conservative)** is recommended, providing 98.8%–100% SLA protection while completing over 30%–46% of maintenance windows.
- **For Throughput-Focused Systems**: **Policy 4 (Predictive Mean-QIR)** is recommended, completing over **91.7%–97.5% of maintenance** while reducing SLA violations by ~22%.

### Question 10: What limitations remain before beginning temporal workload-aware scheduling?
1. **Static Feature Window**: Static pre-decision telemetry cannot anticipate query arrival bursts or dynamic concurrency fluctuations occurring *after* maintenance starts.
2. **Binary Scheduling Instant**: Current policies evaluate maintenance only at discrete query arrival triggers rather than continuously forecasting upcoming workload density.
3. **Starvation Mitigation**: Static upper bounds lack adaptive deadline aging to force maintenance execution when tables reach critical fragmentation thresholds.

---

## Generated Artifacts & Visualizations

The following required validation artifacts have been generated in `scripts/phase3d-validation-generalization/`:

1. `results/loco_regression_results.csv` — Full 12-fold cross-validation metrics.
2. `results/loco_regression_summary.csv` — Summary stats (mean, median, std, best, worst) across models.
3. `results/regression_baseline_comparison.csv` — Models vs. Trivial Baselines relative improvement.
4. `results/policy_pareto_results.csv` — In-distribution policy metrics & Pareto flags.
5. `results/policy_tradeoff_summary.csv` — Tradeoff analysis metrics.
6. `results/ood_policy_tradeoff_results.csv` — Zero-shot OOD policy tradeoff metrics.
7. `analysis/plots/policy_pareto_frontier.png` — In-distribution Pareto frontier visual plot.
8. `analysis/plots/ood_policy_pareto_frontier.png` — Out-of-distribution Pareto frontier visual plot.

> [!NOTE]
> All Phase 3A, 3B, 3C source code and raw data remained completely untouched throughout Phase 3D execution.
