#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor

WORKSPACE_DIR = "/media/shashank/Data1/PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
RESULTS_DIR = os.path.join(PHASE3B_DIR, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

sns.set_theme(style="whitegrid", font_scale=1.2)

def run_conformal_prediction():
    print("=== Phase 4: Split Conformal Prediction (Task 5) ===")
    
    dataset_csv = os.path.join(RESULTS_DIR, "dataset_predictive_signals.csv")
    df = pd.read_csv(dataset_csv)
    
    # Feature Engineering
    exclude_cols = ["config_id", "qir_pct", "sla_violation_10pct", "repetition", "window_id", "timestamp"]
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    categorical_cols = [c for c in ["workload_type", "scheduler_mode", "query"] if c in feature_cols]
    X_df = pd.get_dummies(df[feature_cols], columns=categorical_cols, drop_first=False)
    
    X = X_df.values
    y = df["qir_pct"].values
    groups = df["config_id"].values
    
    # Split by config_id
    # We have 12 configs. Let's do 8 Train, 2 Calibration, 2 Test
    unique_configs = np.unique(groups)
    np.random.seed(42)
    np.random.shuffle(unique_configs)
    
    train_configs = unique_configs[:8]
    calib_configs = unique_configs[8:10]
    test_configs = unique_configs[10:]
    
    train_mask = np.isin(groups, train_configs)
    calib_mask = np.isin(groups, calib_configs)
    test_mask = np.isin(groups, test_configs)
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_calib, y_calib = X[calib_mask], y[calib_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    
    print(f"Train samples: {len(X_train)} (Configs: {train_configs})")
    print(f"Calibration samples: {len(X_calib)} (Configs: {calib_configs})")
    print(f"Test samples: {len(X_test)} (Configs: {test_configs})")
    
    # Train Best Regressor (GradientBoosting)
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("model", GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42))
    ])
    model.fit(X_train, y_train)
    
    # Compute conformity scores on calibration set
    calib_preds = model.predict(X_calib)
    conformity_scores = np.abs(y_calib - calib_preds)
    
    # Calculate q_hat for alpha=0.05
    alpha = 0.05
    n_cal = len(conformity_scores)
    quantile = (1 - alpha) * (1 + 1 / n_cal)
    
    if quantile > 1.0:
        quantile = 1.0
        
    q_hat = np.quantile(conformity_scores, quantile, method="higher")
    print(f"Calculated q_hat: {q_hat:.4f} for alpha={alpha} (Target Coverage 95%)")
    
    # Evaluate on test set
    test_preds = model.predict(X_test)
    lower_bounds = test_preds - q_hat
    upper_bounds = test_preds + q_hat
    
    covered = (y_test >= lower_bounds) & (y_test <= upper_bounds)
    empirical_coverage = np.mean(covered) * 100
    average_width = np.mean(upper_bounds - lower_bounds)
    
    print(f"Empirical Coverage on Test Set: {empirical_coverage:.2f}%")
    print(f"Average Interval Width: {average_width:.4f}")
    
    # Save Results
    results = []
    for i in range(len(y_test)):
        results.append({
            "test_sample_idx": i,
            "actual_qir": y_test[i],
            "predicted_qir": test_preds[i],
            "lower_bound": lower_bounds[i],
            "upper_bound": upper_bounds[i],
            "covered": covered[i],
            "interval_width": upper_bounds[i] - lower_bounds[i]
        })
        
    res_df = pd.DataFrame(results)
    res_csv = os.path.join(RESULTS_DIR, "conformal_results.csv")
    res_df.to_csv(res_csv, index=False)
    print(f"Saved conformal results to {res_csv}")
    
    # Plot 1: Conformal Coverage
    plt.figure(figsize=(10, 6))
    
    # Sort by predicted value for cleaner visualization
    sort_idx = np.argsort(test_preds)
    test_preds_sorted = test_preds[sort_idx]
    y_test_sorted = y_test[sort_idx]
    lower_sorted = lower_bounds[sort_idx]
    upper_sorted = upper_bounds[sort_idx]
    covered_sorted = covered[sort_idx]
    
    x = np.arange(len(y_test))
    
    # Plot intervals
    plt.fill_between(x, lower_sorted, upper_sorted, color='lightblue', alpha=0.5, label='95% Prediction Interval')
    plt.plot(x, test_preds_sorted, 'k--', label='Point Prediction')
    
    # Plot actuals
    plt.scatter(x[covered_sorted], y_test_sorted[covered_sorted], color='green', marker='o', s=40, label='Covered (Actual)')
    plt.scatter(x[~covered_sorted], y_test_sorted[~covered_sorted], color='red', marker='x', s=60, label='Uncovered (Actual)')
    
    plt.title(f"Conformal Prediction Coverage (Target: 95%, Empirical: {empirical_coverage:.1f}%)")
    plt.xlabel("Test Sample Index (Sorted by Prediction)")
    plt.ylabel("QIR %")
    plt.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "conformal_coverage.png"), dpi=300)
    plt.close()
    
    # Plot 2: Interval Width
    plt.figure(figsize=(8, 6))
    widths = upper_bounds - lower_bounds
    sns.histplot(widths, bins=1, kde=False, color="purple") # It's a constant width for standard split conformal!
    plt.title("Conformal Prediction Interval Widths")
    plt.xlabel("Interval Width (QIR %)")
    plt.ylabel("Count")
    
    # Add annotation that it's constant
    plt.annotate(f"Constant width: {q_hat*2:.2f}\n(Standard Split Conformal property)", 
                 xy=(0.5, 0.5), xycoords='axes fraction', ha='center',
                 fontsize=12, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray"))
                 
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "conformal_interval_width.png"), dpi=300)
    plt.close()
    
    print(f"Saved plots to {PLOTS_DIR}")

if __name__ == "__main__":
    run_conformal_prediction()
