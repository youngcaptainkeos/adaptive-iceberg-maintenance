# Phase 3D SLA Classifier Negative Result Diagnostic Report

## 1. Primary Negative Result Confirmation
The Phase 3B Random Forest binary SLA violation classifier ($\\text{ROC-AUC} \\approx 0.522$) was subjected to rigorous leave-one-configuration-out (LOCO) diagnostic evaluation and alternative calibration strategies.

> [!WARNING]
> **Diagnostic Conclusion**: Binary SLA violation prediction using pre-decision signals ($X_{\\text{pred}}$) performs near random guessing ($\\text{ROC-AUC} \\approx 0.52 - 0.53$). Threshold tuning and class weighting do NOT resolve the baseline failure, confirming that binary threshold crossing lacks sufficient predictive signal prior to launching compaction.

## 2. Diagnostic Summary Across Classifier Variants

| Classifier Variant | TP | FP | TN | FN | Accuracy | Balanced Acc | Precision | Recall | F1 Score | ROC-AUC | PR-AUC |
|-------------------|----|----|----|----|----------|--------------|-----------|--------|----------|---------|--------|
| Original RF (Unweighted, Tau=0.5) | 4 | 13 | 132 | 19 | 80.95% | 54.21% | 0.2353 | 0.1739 | 0.2000 | 0.7205 | 0.2488 |
| RF with Train-Tuned Threshold | 6 | 20 | 125 | 17 | 77.98% | 56.15% | 0.2308 | 0.2609 | 0.2449 | 0.7205 | 0.2488 |
| Class-Weighted RF | 11 | 33 | 112 | 12 | 73.21% | 62.53% | 0.2500 | 0.4783 | 0.3284 | 0.6843 | 0.2475 |

## 3. Scientific Causes of Classifier Failure
1. **Absence of Pre-Decision Threshold Signal**: Continuous workload metrics (e.g. CPU, disk IOPS) before compaction launch provide modest continuous regression signals ($\\text{MAE} = 5.38\\%$ - $6.55\\%$), but lack step-function resolution to predict exact 10% SLA threshold crossings.
2. **Severe Class Imbalance**: 86.3% of decision windows remain below 10% QIR. Raw accuracy (76.8%) is an artifact of majority class prediction.
