import pandas as pd
import numpy as np
import os
import argparse
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import RidgeCV, LinearRegression
from sklearn.dummy import DummyRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Set seaborn style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.4)

def conformal_q_hat(y_true, y_pred, alpha=0.05):
    residuals = np.abs(y_true - y_pred)
    n = len(residuals)
    q_level = np.ceil((n + 1) * (1 - alpha)) / n
    q_level = min(q_level, 1.0)
    return np.quantile(residuals, q_level, method='higher')

def train_and_evaluate(input_csv):
    print(f"Loading {input_csv}...")
    df = pd.read_csv(input_csv)
    
    # Base point-in-time features vs Temporal Features
    base_features = [
        'cpu_utilization_pct', 'memory_used_pct', 
        'disk_read_iops', 'disk_write_iops',
        'active_spark_jobs', 'compaction_active'
    ]
    
    temporal_features = base_features + [
        'cpu_utilization_pct_mean_60s', 'cpu_utilization_pct_std_60s',
        'memory_used_pct_mean_60s', 'memory_used_pct_std_60s',
        'disk_read_iops_mean_60s', 'disk_read_iops_std_60s',
        'disk_write_iops_mean_60s', 'disk_write_iops_std_60s'
    ]
    
    target = 'target_avg_query_duration_300s'
    
    # Split
    train_df = df[df['split'] == 'train']
    val_df = df[df['split'] == 'val']
    test_df = df[df['split'] == 'test']
    
    print(f"Train samples: {len(train_df)}, Val samples: {len(val_df)}, Test samples: {len(test_df)}")
    
    X_train_base = train_df[base_features].astype(float)
    X_train_temp = train_df[temporal_features].astype(float)
    y_train = train_df[target].astype(float)
    
    X_val_base = val_df[base_features].astype(float)
    X_val_temp = val_df[temporal_features].astype(float)
    y_val = val_df[target].astype(float)
    
    X_test_base = test_df[base_features].astype(float)
    X_test_temp = test_df[temporal_features].astype(float)
    y_test = test_df[target].astype(float)
    
    print("Training Baselines...")
    dummy = DummyRegressor(strategy='mean')
    dummy.fit(X_train_base, y_train)
    
    lr = LinearRegression()
    lr.fit(X_train_base, y_train)
    
    rf = RandomForestRegressor(random_state=42)
    rf.fit(X_train_base, y_train)
    
    baseline_model = GradientBoostingRegressor(random_state=42)
    baseline_model.fit(X_train_base, y_train)
    
    print("Training Temporal-Aware Model (RidgeCV with Lag Features)...")
    scaler = StandardScaler()
    X_train_temp_scaled = scaler.fit_transform(X_train_temp)
    X_val_temp_scaled = scaler.transform(X_val_temp)
    X_test_temp_scaled = scaler.transform(X_test_temp)
    
    # Fit RidgeCV ONLY on training data to prevent data contamination
    alphas = np.logspace(-3, 3, 100)
    temporal_model = RidgeCV(alphas=alphas)
    temporal_model.fit(X_train_temp_scaled, y_train)
                       
    # ---------------- Evaluation ----------------
    print("\n--- Chronological Test Evaluation ---")
    dummy_preds = dummy.predict(X_test_base)
    lr_preds = lr.predict(X_test_base)
    rf_preds = rf.predict(X_test_base)
    base_preds = baseline_model.predict(X_test_base)
    temp_preds = temporal_model.predict(X_test_temp_scaled)
    
    print(f"Dummy (Mean) MAE:           {mean_absolute_error(y_test, dummy_preds):.2f} ms (R²: {r2_score(y_test, dummy_preds):.3f})")
    print(f"Linear Regression MAE:      {mean_absolute_error(y_test, lr_preds):.2f} ms (R²: {r2_score(y_test, lr_preds):.3f})")
    print(f"Random Forest MAE:          {mean_absolute_error(y_test, rf_preds):.2f} ms (R²: {r2_score(y_test, rf_preds):.3f})")
    
    base_mae = mean_absolute_error(y_test, base_preds)
    temp_mae = mean_absolute_error(y_test, temp_preds)
    
    base_r2 = r2_score(y_test, base_preds)
    temp_r2 = r2_score(y_test, temp_preds)
    
    print(f"Baseline (Point-in-Time) MAE: {base_mae:.2f} ms (R²: {base_r2:.3f})")
    print(f"Temporal (Lag-Aware) MAE:     {temp_mae:.2f} ms (R²: {temp_r2:.3f})")
    
    # ---------------- Conformal Prediction ----------------
    # Compute q_hat on the validation set for the temporal model
    val_preds_temp = temporal_model.predict(X_val_temp_scaled)
    q_hat = conformal_q_hat(y_val, val_preds_temp, alpha=0.05)
    print(f"\nConformal q_hat computed on chronological validation set: {q_hat:.2f} ms")
    
    test_df = test_df.copy()
    test_df['pred_baseline'] = base_preds
    test_df['pred_temporal'] = temp_preds
    test_df['residual_baseline'] = y_test - base_preds
    test_df['residual_temporal'] = y_test - temp_preds
    
    test_df['conformal_lower'] = test_df['pred_temporal'] - q_hat
    test_df['conformal_upper'] = test_df['pred_temporal'] + q_hat
    
    coverage = ((y_test >= test_df['conformal_lower']) & (y_test <= test_df['conformal_upper'])).mean()
    print(f"Temporal Model Test Coverage: {coverage*100:.2f}% (Target: 95%)")
    
    results_dir = os.path.dirname(input_csv)
    
    # ---------------- Visualization 1: Chronological Residuals ----------------
    print("Generating chronological_residuals.svg...")
    plt.figure(figsize=(15, 6))
    
    plt.scatter(test_df['timestamp'], test_df['residual_baseline'], color='red', alpha=0.5, label='Baseline Residuals', s=10)
    plt.scatter(test_df['timestamp'], test_df['residual_temporal'], color='blue', alpha=0.5, label='Temporal Residuals', s=10)
    plt.axhline(0, color='black', linestyle='--')
    
    plt.title('Chronological Residuals on Test Block (Point-in-Time vs Temporal-Aware)')
    plt.xlabel('Timestamp')
    plt.ylabel('Residual Error (ms)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "chronological_residuals.svg"), format='svg')
    plt.close()
    
    # ---------------- Visualization 2: Conformal Coverage Timeline ----------------
    print("Generating temporal_conformal_coverage.svg...")
    plt.figure(figsize=(15, 6))
    
    # Downsample for plotting clarity if too many points
    plot_df = test_df.iloc[::5] # plot every 5th second
    
    plt.fill_between(plot_df['timestamp'], plot_df['conformal_lower'], plot_df['conformal_upper'], 
                     color='gray', alpha=0.3, label='Temporal 95% Conformal Bound')
                     
    plt.plot(plot_df['timestamp'], plot_df['pred_temporal'], color='black', linestyle='--', label='Temporal Prediction')
    
    covered = plot_df[(plot_df[target] >= plot_df['conformal_lower']) & (plot_df[target] <= plot_df['conformal_upper'])]
    uncovered = plot_df[(plot_df[target] < plot_df['conformal_lower']) | (plot_df[target] > plot_df['conformal_upper'])]
    
    plt.scatter(covered['timestamp'], covered[target], color='blue', alpha=0.7, s=15, label='Actual (Covered)')
    plt.scatter(uncovered['timestamp'], uncovered[target], color='red', marker='x', alpha=1.0, s=30, label='Actual (Uncovered)')
    
    plt.title(f'Temporal Conformal Coverage on Test Block (Empirical Coverage: {coverage*100:.1f}%)')
    plt.xlabel('Timestamp')
    plt.ylabel('Query Duration (ms)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "temporal_conformal_coverage.svg"), format='svg')
    plt.close()
    
    print("Finished training and evaluation.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model/results/temporal_windows.csv")
    args = parser.parse_args()
    
    train_and_evaluate(args.input)
