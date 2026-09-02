# Raw Quantile Model Calibration Summary (LOCO-CV)

## 1. Overall Calibration Results
- **Nominal Target Coverage**: 95.00%
- **Empirical Overall Coverage**: **91.07%** (153 / 168 observations covered)
- **Total Undercovered Observations**: **15** (8.93% failure rate)

## 2. Per-Configuration Empirical Coverage

| Held-Out Config ID | Fold | Sample N | Covered N | Undercovered N | Empirical Coverage (%) | Target Coverage (%) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `frag200_multi_stream_FAIR` | 1 | 24 | 24 | 0 | 100.00% | 95.00% |
| `frag200_multi_stream_FIFO` | 2 | 24 | 22 | 2 | 91.67% | 95.00% |
| `frag200_single_stream_FAIR` | 3 | 4 | 2 | 2 | 50.00% | 95.00% |
| `frag200_single_stream_FIFO` | 4 | 4 | 4 | 0 | 100.00% | 95.00% |
| `frag500_multi_stream_FAIR` | 5 | 24 | 20 | 4 | 83.33% | 95.00% |
| `frag500_multi_stream_FIFO` | 6 | 24 | 23 | 1 | 95.83% | 95.00% |
| `frag500_single_stream_FAIR` | 7 | 4 | 4 | 0 | 100.00% | 95.00% |
| `frag500_single_stream_FIFO` | 8 | 4 | 3 | 1 | 75.00% | 95.00% |
| `frag50_multi_stream_FAIR` | 9 | 24 | 21 | 3 | 87.50% | 95.00% |
| `frag50_multi_stream_FIFO` | 10 | 24 | 23 | 1 | 95.83% | 95.00% |
| `frag50_single_stream_FAIR` | 11 | 4 | 4 | 0 | 100.00% | 95.00% |
| `frag50_single_stream_FIFO` | 12 | 4 | 3 | 1 | 75.00% | 95.00% |

## 3. Direct Scientific Assessment
### Does the nominal q=0.95 model empirically achieve approximately 95% coverage under LOCO-CV?

**NO.** The nominal $q=0.95$ quantile regression model achieves an overall empirical coverage of **91.07%** across 12 LOCO-CV folds, falling short of the nominal 95.00% target by 3.93% percentage points.

### Key Observations & Limitations:
- **Configuration-Level Failures**: While overall marginal coverage may hover around the nominal value, individual held-out configurations exhibit severe conditional coverage degradation (e.g. single-stream configurations where coverage drops significantly).
- **Lack of Finite-Sample Guarantees**: Uncalibrated quantile regression lacks finite-sample coverage guarantees, creating unpredictable SLA violation risks under structural cross-configuration generalization.
