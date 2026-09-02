# Phase 3D Track 1: Conformal vs. Raw Quantile Calibration Summary

## 1. Primary Empirical Comparison

| Method | Nominal Coverage | Empirical Coverage | Undercoverage Count | Worst Config Coverage | Mean Upper Bound (% QIR) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Raw $q=0.95$ Quantile Regression** | 95.0% | **91.07%** | **15** | **50.00%** | 12.56% |
| **Split-Conformal Upper Bound** | 95.0% | **98.21%** | **3** | **50.00%** | 23.06% |

## 2. Detailed Performance Breakdowns

### Raw Quantile Regression ($q=0.95$):
- **Overall Empirical Coverage**: 91.07% (153 / 168)
- **Undercoverage Count**: 15 observations violated the upper bound (8.93%)
- **Worst-Case Configuration**: `frag200_single_stream_FAIR` (50.00% coverage)
- **Best-Case Configurations**: `frag200_multi_stream_FAIR` (100.00% coverage)

### Split-Conformal Upper Bound (Random Forest Base Model):
- **Overall Empirical Coverage**: 98.21% (165 / 168)
- **Undercoverage Count**: 3 observations violated the upper bound (1.79%)
- **Mean Conformal Offset**: +18.83% QIR added to point predictions
- **Worst-Case Configuration**: `frag200_single_stream_FAIR` (50.00% coverage)
- **Best-Case Configurations**: `frag200_multi_stream_FAIR` (100.00% coverage)

## 3. Scientific Interpretation & Formal Language Guardrails
- **Finite-Sample Marginal Guarantee**: Split-conformal prediction provides a valid marginal finite-sample coverage guarantee under the assumption of data exchangeability.
- **Empirical LOCO Variability**: Empirical Leave-One-Configuration-Out (LOCO) cross-validation coverage on this finite dataset is **98.21%**, slightly exceeding the 95.0% nominal target due to conservative finite-sample quantile selection.
- **Conditional Coverage Limitation**: While conformal prediction significantly improves empirical reliability over uncalibrated quantile regression (reducing undercoverage from 15 observations to 3 observations), configuration-level conditional coverage is not strictly guaranteed for every individual structural configuration fold.
