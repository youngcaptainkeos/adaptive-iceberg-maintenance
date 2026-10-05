# ML Foundation Audit Report

This report documents the severe implementation flaws discovered in the Phase 3 ML pipeline, specifically the data leakage and the misuse of custom hand-rolled implementations instead of standard ML frameworks.

## 1. `scripts/phase3b-predictive-signals/analysis/train_predictive_models.py`
1. **Data Leakage (Lines 205-207)**
   - *Code*: `means = [sum(X_raw[i][j] for i in range(n_samples)) / n_samples...`
   - *Explanation*: Standard scaling (`means` and `stds`) is calculated on `X_raw`, which contains the entire dataset. This happens *before* the `GroupKFold` split, meaning information about the held-out validation configurations leaks into the training sets.
2. **Hand-Rolled Tree Model (Lines 93-144)**
   - *Code*: `class SimpleTreeRegressor:...`
   - *Explanation*: A custom CART-like tree is built from scratch and then loosely bagged (Lines 299-326) instead of utilizing `sklearn.ensemble.RandomForestRegressor`. This lacks proper feature subsampling and optimization.
3. **Hand-Rolled Linear Models (Lines 225-296)**
   - *Code*: Matrix inversion for Ridge (`invert_matrix(XtX)`) and manual gradient descent for Lasso.
   - *Explanation*: Numerically unstable and lacks regularization path optimization provided by `sklearn.linear_model`.
4. **Hand-Rolled Classification Metrics (Lines 56-91)**
   - *Code*: `roc_auc_score`, `pr_auc_score` implemented via manual iteration.
   - *Explanation*: Reinvents the wheel poorly instead of using `sklearn.metrics`.
5. **Pseudo-Conformal Quantile Regressor (Lines 335-361)**
   - *Code*: Linear regression optimized with pinball loss (q=0.95).
   - *Explanation*: This provides a quantile regression estimate but lacks any valid conformal calibration set or conformity scores. It is inappropriately marketed as an "Upper Bound".
6. **Missing Trivial Baselines & Serialization**
   - *Explanation*: No mean/median baseline is computed for comparison. Models are not serialized (e.g., via `joblib`), requiring everything downstream to retrain from scratch.

## 2. `scripts/phase3c-uncertainty-aware-scheduler/runner/run_phase3c_experiment.py`
1. **Data Leakage (Lines 52-54)**
   - *Explanation*: Identical scaling leakage over the full dataset before splitting/testing.
2. **Hand-Rolled ML Retraining (Lines 75-110, 135-147)**
   - *Explanation*: Repeats the exact same hand-rolled `SimpleTree` and Quantile regression implementations rather than importing a trained serialized model.

## 3. `scripts/phase3d-validation-generalization/validation/conformal_upper_bound.py`
1. **Hand-Rolled Tree Model (Lines 16-63)**
   - *Explanation*: Once again manually implements `SimpleTreeRegressor`.
2. **Hand-Rolled Conformal Algorithm (Lines 173-183)**
   - *Explanation*: Implements finite-sample conformal quantile calculations manually. While structurally better than Phase 3B because it uses a calibration split, it still relies on a hand-rolled base model and custom interval logic rather than a robust library like `mapie`.

## 4. `scripts/phase3d-validation-generalization/validation/conformal_policy_interface.py`
1. **Data Leakage (Lines 131-133)**
   - *Code*: Scales over `X_tr_raw` which technically isolates the test set, but it includes the calibration set in the scaler fitting.
2. **On-the-fly Retraining (Lines 92-164)**
   - *Explanation*: `_load_and_train_conformal_model` retrains the hand-rolled RF on every execution instead of loading `best_regressor.joblib`.

## 5. `scripts/phase3d-validation-generalization/validation/loco_cross_validation.py`
1. **Hand-Rolled ML Models (Lines 72-119, 193-248)**
   - *Explanation*: Repeats the hand-rolled implementations for Ridge, Lasso, Random Forest, and Quantile regressor inside the LOCO evaluation loops.

## 6. `scripts/phase3d-validation-generalization/ood/eval_ood_generalization.py`
1. **Hand-Rolled ML Models (Lines 44-91, 170-223)**
   - *Explanation*: Repeats the exact same bad implementations to evaluate Out-Of-Domain (OOD) data.

---
**BASELINE EVIDENCE**:
Running the leaky `train_predictive_models.py` produces the following benchmark for Random Forest Regression:
- **MAE**: 5.38% QIR
- **RMSE**: 7.34% QIR

These numbers will be directly compared against the leakage-free, properly implemented `scikit-learn` version in Task 3.
