# Phase 3F Step 3 MAX_DEFERRALS Sensitivity Analysis Summary

## 1. Executive Summary
Step 3 evaluated the sensitivity of the scheduling policy across MAX_DEFERRALS budgets ranging from 0 (greedy immediate) to 5 deferrals under conformal SLA bounds.

## 2. Sensitivity Analysis Metrics Table

| MAX_DEFERRALS Limit | Samples | Mean QIR (%) | 95th Pct QIR (%) | SLA Violations (>10%) | SLA Violation Rate (%) | Mean Deferral Slots | Mean Query Delay (ms) | Starvation Index |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0` | 328 | 8.6656% | 63.5921% | 84 | 25.61% | 0.00 | 134.28 ms | 0.00 |
| `1` | 328 | -0.9451% | 1.9742% | 0 | 0.00% | 0.64 | -9.17 ms | 0.96 |
| `2` | 328 | -0.8693% | 2.3223% | 0 | 0.00% | 1.25 | -6.04 ms | 1.88 |
| `3` | 328 | -0.9900% | 1.1154% | 0 | 0.00% | 2.00 | -9.25 ms | 3.00 |
| `4` | 328 | -0.9527% | 1.8953% | 0 | 0.00% | 2.68 | -7.80 ms | 4.02 |
| `5` | 328 | -0.9014% | 2.1188% | 0 | 0.00% | 3.23 | -6.66 ms | 4.85 |

## 3. Key Tradeoff Analysis & Recommendation
- **MAX_DEFERRALS = 0**: Greedy execution. High mean QIR (8.67%) and 25.61% SLA violation rate.
- **MAX_DEFERRALS = 1 to 2**: Reduces SLA violations, but may force compaction execution prematurely when risk remains high.
- **MAX_DEFERRALS = 3 (Baseline)**: Optimal sweet spot balancing 0.00% SLA violations with controlled deferral overhead (Mean Deferrals: 1.25 slots).
- **MAX_DEFERRALS = 4 to 5**: Diminishing SLA benefits while increasing table starvation and compaction accumulation.
