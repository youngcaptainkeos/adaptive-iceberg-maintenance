#!/usr/bin/env python3
import os
import sys
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Ensure paths
sys.path.append(os.path.abspath('scripts/phase5-adaptive-scheduling-agent'))

def train_conformal_model(X_train, y_train, X_calib, y_calib, alpha=0.05):
    """Trains a regression pipeline and computes conformal bound q_hat."""
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('model', GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42))
    ])
    
    # Train
    pipeline.fit(X_train, y_train)
    
    # Calibrate conformal bound
    calib_preds = pipeline.predict(X_calib)
    residuals = np.abs(y_calib - calib_preds)
    
    n = len(residuals)
    q_val = np.ceil((n + 1) * (1 - alpha)) / n
    q_val = min(max(q_val, 0.0), 1.0) # Clamp between 0 and 1
    
    if len(residuals) == 0:
        q_hat = 0.0
    else:
        q_hat = np.quantile(residuals, q_val, method='higher')
        
    return pipeline, q_hat

def evaluate_model(pipeline, q_hat, X_test, y_test):
    """Evaluates the model and conformal bounds."""
    if len(y_test) == 0:
        return {"mae": 0, "r2": 0, "coverage": 0}
        
    preds = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    
    # R2 requires variance
    if len(np.unique(y_test)) > 1:
        r2 = r2_score(y_test, preds)
    else:
        r2 = 0.0
        
    lower = preds - q_hat
    upper = preds + q_hat
    coverage = np.mean((y_test >= lower) & (y_test <= upper)) * 100
    
    return {"mae": mae, "r2": r2, "coverage": coverage}

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True, help='Path to training data CSV')
    parser.add_argument('--model-dir', type=str, default='models/')
    parser.add_argument('--plot-dir', type=str, default='figures/')
    args = parser.parse_args()
    
    data_path = args.input
    if not os.path.exists(data_path):
        print(f"ERROR: Training data {data_path} not found.")
        sys.exit(1)
        
    print(f"Loading {data_path}...")
    df = pd.read_csv(data_path)
    
    max_lat = df['query_latency_ms'].max() if 'query_latency_ms' in df.columns else 0.0
    comp_events = len(df[df['compaction_active'] == True])
    print(f"[VALIDATION] Max latency: {max_lat:.1f}ms | Compaction events: {comp_events}")
    
    if max_lat <= 0.0:
        print("\n[CRITICAL ERROR] The dataset is entirely filled with 0.0ms latencies or missing them. You cannot train on fake data.")
        sys.exit(1)
        
    if comp_events < 5:
        print(f"\n[CRITICAL ERROR] Only {comp_events} compaction events found. The dataset is invalid. You must run Phase 6A properly.")
        sys.exit(1)
        
    # Forward fill NaNs for telemetry, drop NaNs in targets
    df['frag_file_count'] = df['frag_file_count'].ffill()
    df['table_size_mb'] = df['table_size_mb'].ffill()
    df['avg_file_size_kb'] = df['avg_file_size_kb'].ffill()
    
    features = [
        'cpu_util_avg_1min', 'cpu_util_avg_5min', 'cpu_trend', 
        'mem_used_pct', 'frag_file_count', 'table_size_mb', 
        'avg_file_size_kb', 'intensity'
    ]
    
    # --- MODEL A (Compaction Regime) ---
    df_compaction = df[df['compaction_active'] == True].copy()
    df_compaction = df_compaction.dropna(subset=['query_latency_during_compaction_ms'] + features)
    
    print(f"\n--- Training Model A (Compaction Regime) ---")
    print(f"Samples: {len(df_compaction)}")
    
    if len(df_compaction) > 100:
        X_a = df_compaction[features]
        y_a = df_compaction['query_latency_during_compaction_ms']
        
        n_a = len(X_a)
        t_split1_a = int(0.7 * n_a)
        t_split2_a = int(0.85 * n_a)
        
        X_train_a, y_train_a = X_a.iloc[:t_split1_a], y_a.iloc[:t_split1_a]
        X_calib_a, y_calib_a = X_a.iloc[t_split1_a:t_split2_a], y_a.iloc[t_split1_a:t_split2_a]
        X_test_a, y_test_a = X_a.iloc[t_split2_a:], y_a.iloc[t_split2_a:]
        
        model_a, q_hat_a = train_conformal_model(X_train_a, y_train_a, X_calib_a, y_calib_a)
        metrics_a = evaluate_model(model_a, q_hat_a, X_test_a, y_test_a)
        
        print(f"Metrics: MAE={metrics_a['mae']:.1f}ms, R2={metrics_a['r2']:.3f}")
        print(f"Conformal Bound (q_hat): {q_hat_a:.1f}ms, Coverage: {metrics_a['coverage']:.1f}%")
    else:
        print("Not enough data to train Model A. Exiting.")
        sys.exit(1)

    # --- MODEL B (Baseline Regime) ---
    df_baseline = df[df['compaction_active'] == False].copy()
    df_baseline = df_baseline.dropna(subset=['query_latency_ms'] + features)
    
    print(f"\n--- Training Model B (Baseline Regime) ---")
    print(f"Samples: {len(df_baseline)}")
    
    if len(df_baseline) > 100:
        X_b = df_baseline[features]
        y_b = df_baseline['query_latency_ms']
        
        n_b = len(X_b)
        t_split1_b = int(0.7 * n_b)
        t_split2_b = int(0.85 * n_b)
        
        X_train_b, y_train_b = X_b.iloc[:t_split1_b], y_b.iloc[:t_split1_b]
        X_calib_b, y_calib_b = X_b.iloc[t_split1_b:t_split2_b], y_b.iloc[t_split1_b:t_split2_b]
        X_test_b, y_test_b = X_b.iloc[t_split2_b:], y_b.iloc[t_split2_b:]
        
        model_b, q_hat_b = train_conformal_model(X_train_b, y_train_b, X_calib_b, y_calib_b)
        metrics_b = evaluate_model(model_b, q_hat_b, X_test_b, y_test_b)
        
        print(f"Metrics: MAE={metrics_b['mae']:.1f}ms, R2={metrics_b['r2']:.3f}")
        print(f"Conformal Bound (q_hat): {q_hat_b:.1f}ms, Coverage: {metrics_b['coverage']:.1f}%")
    else:
        print("Not enough data to train Model B. Exiting.")
        sys.exit(1)

    # --- Save Models ---
    if q_hat_a <= 0.0 or q_hat_b <= 0.0:
        print("\n[CRITICAL ERROR] q_hat evaluated to 0.0. The models learned nothing. Refusing to save broken models.")
        sys.exit(1)
        
    out_dir = args.model_dir
    os.makedirs(out_dir, exist_ok=True)
    
    joblib.dump(model_a, f"{out_dir}/model_a_compaction.joblib")
    joblib.dump(model_b, f"{out_dir}/model_b_baseline.joblib")
    
    metadata = {
        "features": features,
        "model_a": {
            "q_hat": float(q_hat_a),
            "test_mae": float(metrics_a['mae']),
            "test_coverage": float(metrics_a['coverage'])
        },
        "model_b": {
            "q_hat": float(q_hat_b),
            "test_mae": float(metrics_b['mae']),
            "test_coverage": float(metrics_b['coverage'])
        }
    }
    
    with open(f"{out_dir}/model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"\nModels and metadata successfully saved to {out_dir}/")

if __name__ == "__main__":
    main()
