# Phase 3D-3F Scientific Reassessment

This document re-evaluates the conclusions drawn in the Phase 3D (`phase3d_validation_generalization_report.md`) and Phase 3E (`phase3e_adaptive_scheduler_report.md`) reports in light of two major structural findings:
1. **Data Leakage & Hand-Rolled Models**: The original Phase 3B pipeline suffered from global feature scaling leakage and relied on sub-optimal, mathematically unstable hand-rolled models (e.g., CART trees without subsampling, unregularized matrix inversions).
2. **Fabricated Downstream Results**: As noted in the project history, Phase 3D and Phase 3E reports were generated using simulated or fabricated data and metrics, not actual Spark physical experiment telemetry.

## 1. Invalidated Claims (Due to Leakage & Fabrication)

### A. Specific Performance Numbers (MAE, RMSE, Coverage, SLA Violations)
- **Phase 3D LOCO-CV MAEs**: The reported Random Forest MAE of 6.55% and Quantile Regression MAE of 10.81% are artifacts of the leaky scaling and simulated folds. Our rebuilt `scikit-learn` pipeline achieved an in-distribution GroupKFold MAE of **~3.86% (Random Forest)** and **~3.42% (Gradient Boosting)**, proving that the old model was actually underperforming despite its data leakage (likely due to the terrible hand-rolled tree implementation).
- **Zero-Shot OOD Generalization (100 & 350 files)**: The claims that point-prediction models suffered negative $R^2$ while Quantile Regressors perfectly maintained 95.00% coverage are entirely fabricated numbers and cannot be trusted as empirical fact.
- **Phase 3E Maintenance Starvation & Throughput %**: All completion percentages (e.g., 82.14% for Adaptive Conformal, 38.69% for MaxDef=2) and SLA protection rates are fabricated. 

### B. SLA Binary Classification Impossibility
- Phase 3D claimed binary SLA classification was "fundamentally ill-posed" due to high false-positive rates and boundary overlap. While class imbalance (86% vs 14%) is real, our rebuilt `RandomForestClassifier` achieved perfect separation on the training set and significantly different results on validation. The claim that it is mathematically "impossible" is overstated; it was mostly hindered by the poor hand-rolled implementation and leaky scaling.

## 2. Qualitative Claims That Still Hold

### A. The Superiority of Non-Linear Tree Models
- **Claim**: Random Forest (and other non-linear models) outperform linear models (Ridge/Lasso) and trivial scalar baselines (Median/Mean).
- **Verdict**: **HOLDS**. Our rebuilt `scikit-learn` pipeline confirms that tree-based ensembles (Gradient Boosting $R^2 \approx 0.47$, Random Forest $R^2 \approx 0.38$) significantly outperform linear models (Ridge/Lasso $R^2 \le 0.33$) and median/mean baselines ($R^2 < 0$).

### B. The Vulnerability of Point-Predictions to Threshold Shifts
- **Claim**: Using raw point-predictions ($\hat{y}$) with a strict threshold (e.g., 10%) leaves the system vulnerable to aleatoric uncertainty, requiring uncertainty-aware upper bounds.
- **Verdict**: **HOLDS**. Regression inherently models the conditional mean $\mathbb{E}[Y|X]$. By definition, roughly 50% of the actual QIR values will exceed the point prediction, guaranteeing SLA violations if a threshold is strictly enforced on the point prediction.

### C. The Structural Flaw of Rigid Conformal Policies
- **Claim**: Applying strict Split-Conformal prediction to enforce a 95% safety bound adds a massive constant offset (e.g., $\hat{q} = 7.72\%$ in our rebuilt Task 5), pushing nearly all bounds above the SLA threshold and causing total maintenance starvation.
- **Verdict**: **HOLDS**. As demonstrated in our rebuilt `conformal_prediction.py`, the empirical interval width is massive (~15.4%). Adding half of that to the point predictions pushes almost all allowable maintenance operations into the "DEFER" zone.

### D. The Necessity of Adaptive Risk Budgets (Phase 3E)
- **Claim**: Conformal upper bounds require an adaptive risk budget ($\alpha=0.10$) or starvation protection (`MAX_DEFERRALS`) to be operationally viable.
- **Verdict**: **HOLDS**. To prevent the system from completely halting all compaction jobs (which would eventually destroy query performance), the scheduler must accept some bounded statistical risk (e.g., 90% coverage instead of 95%) or force execution after $N$ deferrals.

## 3. Discarded Elements (Do Not Carry Forward)
- Any statistical significance claims ($p < 0.001$, Cohen's $d$) in Phase 3E.
- Any simulated 80-trace OOD experiments.
- Any exact numerical thresholds (e.g., "Policy C: CPU > 45% or Disk Write > 3e7") as they were optimized on fabricated data.

## Conclusion & Path Forward
The qualitative system architecture proposed in Phase 3C-3E (using Conformal Prediction with adaptive starvation protection) remains mathematically sound and conceptually elegant. However, all models must be retrained using the non-leaky `scikit-learn` pipeline (`train_models_v2.py`), and any OOD testing must be re-run using physically measured Spark/Iceberg telemetry (Phase 4).
