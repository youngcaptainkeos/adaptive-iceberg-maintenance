# Phase 3D Track 1 Scientific Report: Uncertainty & Calibration Analysis

## 1. Objective
In production database systems, executing background maintenance (such as Apache Iceberg `rewrite_data_files` table compaction) concurrently with interactive user queries introduces query latency interference. To prevent Service Level Agreement (SLA) breaches, predictive maintenance schedulers must estimate the expected Query Interference Ratio ($\text{QIR} = \frac{\text{Concurrent} - \text{Baseline}}{\text{Baseline}} \times 100\%$).

However, point prediction models (e.g. Mean Regressors) provide no guarantee regarding upper-tail risk, and uncalibrated risk models can lead to dangerous under-prediction of extreme latency spikes. Before a scheduling policy can be declared **uncertainty-aware**, its upper prediction bounds must undergo rigorous empirical calibration verification. The primary goal of Track 1 is to evaluate whether the Phase 3B nominal $q=0.95$ quantile regression model is empirically calibrated under Leave-One-Configuration-Out Cross Validation (LOCO-CV), and to implement and evaluate a Split-Conformal One-Sided Upper Prediction Bound providing finite-sample marginal safety guarantees.

---

## 2. Raw Quantile Model Calibration

### Methodology
To evaluate structural cross-configuration generalization without data leakage:
- **Validation Framework**: Leave-One-Configuration-Out Cross-Validation (LOCO-CV) across all 12 unique experimental configurations.
- **Folds**: 12 complete folds. In each fold, 11 configurations serve as training data, and 1 complete configuration is held out for evaluation.
- **Preprocessing**: Feature standard-scaling parameters ($\mu, \sigma$) were fit strictly on the 11 training configurations per fold.
- **Model**: Linear Pinball Loss Quantile Regressor minimizing $L_{q}(y, \hat{y}) = \max(q(y - \hat{y}), (q - 1)(y - \hat{y}))$ with $q=0.95$, learning rate $\eta=0.01$ over 300 epochs.

### Empirical Results
- **Nominal Target Coverage**: 95.00%
- **Empirical Overall Coverage**: **91.07%** (153 / 168 observations covered)
- **Overall Undercoverage Rate**: **8.93%** (15 observations exceeded predicted upper bound)
- **Per-Configuration Breakdown**:
  - `frag500_single_stream_FIFO`: 75.0% coverage (1 / 4 undercovered)
  - `frag500_single_stream_FAIR`: 100.0% coverage (4 / 4 covered)
  - `frag50_multi_stream_FIFO`: 95.83% coverage (23 / 24 covered)
  - `frag50_multi_stream_FAIR`: 87.50% coverage (21 / 24 covered)
  - `frag200_single_stream_FAIR`: 50.00% coverage (2 / 4 undercovered)

> [!WARNING]
> **Raw Quantile Model Miscalibration**: Under structural LOCO-CV, the uncalibrated nominal $q=0.95$ quantile regression model failed to achieve the nominal 95% target, achieving only **91.07%** empirical coverage (an undercoverage rate nearly double the allowable 5% budget).

---

## 3. Split-Conformal One-Sided Upper Bound Method

To guarantee reliable coverage on finite datasets, we implemented a non-parametric Split-Conformal Prediction framework around the Phase 3B Random Forest regressor.

### Training / Calibration / Test Separation
To avoid intra-configuration leakage:
1. **Outer Loop (LOCO Test)**: 1 configuration held out for testing.
2. **Inner Configuration-Aware Split**: The remaining 11 training configurations were deterministically partitioned into:
   - **Proper Model-Training Set**: 8 configurations (~112 observations) used exclusively to fit feature scalers and the Random Forest base regressor ensemble (`SimpleTreeRegressor`, `max_depth=3`, `min_samples_split=4`, 5 trees).
   - **Calibration Set**: 3 configurations (~42 observations) used exclusively to compute nonconformity scores.

### Nonconformity Score & Conformal Quantile Formula
- **One-Sided Nonconformity Score**:
  $$\text{score}_i = y_i - \hat{f}(x_i), \quad \forall i \in \text{Calibration Set}$$
- **Finite-Sample Quantile Index**:
  For nominal coverage $1 - \alpha = 0.95$ ($\alpha = 0.05$) on $N_{calib}$ calibration samples, the conformal quantile rank $k$ is computed as:
  $$k = \left\lceil (N_{calib} + 1)(1 - \alpha) \right\rceil$$
  The 1-indexed $k$-th smallest score $q_{conformal} = \text{score}_{(k)}$ is extracted as the conformal offset.
- **Upper Bound Prediction**:
  $$\text{conformal\_upper\_bound} = \hat{f}(x_{test}) + q_{conformal}$$

---

## 4. Empirical Results & Comparison

### Table 4.1: Raw Quantile vs. Split-Conformal Calibration

| Method | Nominal Target Coverage | Empirical LOCO Coverage | Total Undercoverage Count | Worst-Case Config Coverage | Mean Upper Bound (% QIR) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Raw $q=0.95$ Quantile Regression** | 95.0% | **91.07%** | **15** | **50.0%** (`frag200_single_stream_FAIR`) | 14.26% |
| **Split-Conformal Upper Bound** | 95.0% | **98.21%** | **3** | **75.0%** (`frag50_single_stream_FIFO`) | 15.64% |

---

## 5. Scientific Interpretation

Based on empirical data across all 12 LOCO-CV folds:

1. **Raw Quantile Miscalibration**: Uncalibrated $q=0.95$ quantile regression was **miscalibrated**, achieving only 91.07% empirical coverage and leaving 15 query runs vulnerable to unexpected SLA latency spikes.
2. **Conformal Calibration Superiority**: Split-conformal calibration **dramatically improved empirical reliability**, elevating overall coverage to **98.21%** and reducing undercoverage violations from 15 to just 3 observations across all folds.
3. **Formal Language Guardrail**:
   - Split-conformal prediction provides a **valid marginal finite-sample coverage guarantee** under the assumption of data exchangeability.
   - Empirical LOCO coverage on this finite dataset is **98.21%**, slightly exceeding the 95.0% nominal target due to conservative finite-sample quantile selection.
   - Configuration-level conditional coverage is not strictly guaranteed for every individual structural configuration fold.

---

## 6. Assumptions and Scientific Limitations

1. **Limited Configuration Sample Size**: The dataset comprises 168 observations nested within 12 experimental configurations.
2. **Exchangeability Assumption**: Conformal coverage guarantees rely on data exchangeability between calibration and test sets.
3. **Out-of-Distribution (OOD) Sensitivity**: Standard split-conformal prediction does not automatically adapt to severe structural distribution shifts (such as unobserved table fragmentation levels). Conformal bounds provide internal LOCO generalization guarantees, but zero-shot OOD validation remains mandatory to assess behavior under structural distribution shift.
