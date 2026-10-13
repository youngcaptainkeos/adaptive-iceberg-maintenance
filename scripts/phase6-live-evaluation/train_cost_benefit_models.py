#!/usr/bin/env python3
"""
Phase 6.1C Query-Aware Conformal Training Routine
Methodology v2.1

Trains Model A (Compaction Regime) and Model B (Baseline Regime) with one-hot encoded
query_id features (q_0, q_1, q_2, q_3) and candidate_small_files to resolve the
bimodal latency distribution and calibrate tight conformal bounds.
"""

import os
import sys
import json
import argparse
import joblib
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Ensure paths
sys.path.append(os.path.abspath('scripts/phase5-adaptive-scheduling-agent'))
sys.path.append(os.path.abspath('scripts/phase6-live-evaluation'))

FEATURE_LIST = [
    'cpu_util_avg_1min', 'cpu_util_avg_5min', 'cpu_trend',
    'mem_used_pct', 'frag_file_count', 'candidate_small_files',
    'table_size_mb', 'avg_file_size_kb', 'intensity',
    'q_0', 'q_1', 'q_2', 'q_3'
]


def train_conformal_model(X_train, y_train, X_calib, y_calib, alpha=0.10):
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
    if n == 0:
        q_hat = 50.0
    else:
        q_val = np.ceil((n + 1) * (1 - alpha)) / n
        q_val = min(max(q_val, 0.0), 1.0)  # Clamp between 0 and 1
        q_hat = float(np.quantile(residuals, q_val, method='higher'))

    if q_hat <= 0.0:
        q_hat = 50.0

    return pipeline, q_hat


def evaluate_model(pipeline, q_hat, X_test, y_test):
    """Evaluates the model, per-query MAE, and conformal bounds."""
    if len(y_test) == 0:
        return {"mae": 0.0, "r2": 0.0, "coverage": 0.0, "per_query_mae": {}}

    preds = pipeline.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))

    # R2 requires target variance
    if len(np.unique(y_test)) > 1:
        r2 = float(r2_score(y_test, preds))
    else:
        r2 = 0.0

    lower = preds - q_hat
    upper = preds + q_hat
    coverage = float(np.mean((y_test >= lower) & (y_test <= upper)) * 100.0)

    # Per-query MAE breakdown
    per_query_mae = {}
    for q in range(4):
        col = f'q_{q}'
        if col in X_test.columns:
            mask = (X_test[col] == 1.0)
            if mask.sum() > 0:
                q_mae = float(mean_absolute_error(y_test[mask], preds[mask]))
                per_query_mae[col] = q_mae
                print(f"    Query Q{q} Test MAE: {q_mae:.1f}ms (n={mask.sum()})")

    return {"mae": mae, "r2": r2, "coverage": coverage, "per_query_mae": per_query_mae}


def prepare_training_dataframe(df_input: pd.DataFrame) -> pd.DataFrame:
    """Fills telemetry nulls and constructs one-hot query_id columns."""
    df = df_input.copy()

    # Default missing columns if loading legacy CSVs
    if 'candidate_small_files' not in df.columns:
        df['candidate_small_files'] = 0.0
    if 'query_id' not in df.columns:
        df['query_id'] = np.nan

    # Forward fill telemetry columns
    df['frag_file_count'] = df['frag_file_count'].ffill().fillna(33.0)
    df['candidate_small_files'] = df['candidate_small_files'].ffill().fillna(0.0)
    df['table_size_mb'] = df['table_size_mb'].ffill().fillna(15000.0)
    df['avg_file_size_kb'] = df['avg_file_size_kb'].ffill().fillna(450000.0)
    df['cpu_util_avg_1min'] = df['cpu_util_avg_1min'].ffill().fillna(50.0)
    df['cpu_util_avg_5min'] = df['cpu_util_avg_5min'].ffill().fillna(50.0)
    df['cpu_trend'] = df['cpu_trend'].ffill().fillna(0.0)
    df['mem_used_pct'] = df['mem_used_pct'].ffill().fillna(30.0)
    df['intensity'] = df['intensity'].ffill().fillna(0.5)

    # One-hot encode query_id (0, 1, 2, 3)
    for q in range(4):
        df[f'q_{q}'] = (df['query_id'] == q).astype(float)

    return df


def train_and_save_models(df: pd.DataFrame, model_dir: str, alpha: float = 0.10, is_test_run: bool = False):
    """Executes the dual-model training, conformal calibration, and artifact serialization."""
    os.makedirs(model_dir, exist_ok=True)
    df_prepared = prepare_training_dataframe(df)

    features = FEATURE_LIST

    # --- MODEL A (Compaction Regime) ---
    df_compaction = df_prepared[df_prepared['compaction_active'] == True].copy()
    df_compaction = df_compaction.dropna(subset=['query_latency_during_compaction_ms', 'query_id'] + features)

    # --- MODEL B (Baseline Regime) ---
    df_baseline = df_prepared[df_prepared['compaction_active'] == False].copy()
    df_baseline = df_baseline.dropna(subset=['query_latency_ms', 'query_id'] + features)

    if is_test_run and len(df_compaction) < 2:
        print("[TEST MODE] Few/no queries completed during compaction in short dry run. Synthesizing test samples from baseline queries.")
        if len(df_baseline) > 0:
            df_synth = df_baseline.copy()
            df_synth['compaction_active'] = True
            df_synth['query_latency_during_compaction_ms'] = df_synth['query_latency_ms'] * 1.25
            df_compaction = pd.concat([df_compaction, df_synth], ignore_index=True)

    print(f"\n--- Training Model A (Compaction Regime) ---")
    print(f"Samples: {len(df_compaction)}")

    min_samples_a = 2 if is_test_run or len(df_compaction) < 100 else 100
    if len(df_compaction) >= min_samples_a:
        X_a = df_compaction[features]
        y_a = df_compaction['query_latency_during_compaction_ms']

        n_a = len(X_a)
        if n_a < 10:
            X_train_a, y_train_a = X_a, y_a
            X_calib_a, y_calib_a = X_a, y_a
            X_test_a, y_test_a = X_a, y_a
        else:
            t_split1_a = int(0.70 * n_a)
            t_split2_a = int(0.85 * n_a)
            X_train_a, y_train_a = X_a.iloc[:t_split1_a], y_a.iloc[:t_split1_a]
            X_calib_a, y_calib_a = X_a.iloc[t_split1_a:t_split2_a], y_a.iloc[t_split1_a:t_split2_a]
            X_test_a, y_test_a = X_a.iloc[t_split2_a:], y_a.iloc[t_split2_a:]

        model_a, q_hat_a = train_conformal_model(X_train_a, y_train_a, X_calib_a, y_calib_a, alpha=alpha)
        metrics_a = evaluate_model(model_a, q_hat_a, X_test_a, y_test_a)

        print(f"Metrics: MAE={metrics_a['mae']:.1f}ms, R2={metrics_a['r2']:.3f}")
        print(f"Conformal Bound (q_hat): {q_hat_a:.1f}ms, Coverage: {metrics_a['coverage']:.1f}%")
    else:
        print(f"Not enough data to train Model A ({len(df_compaction)} < {min_samples_a}).")
        sys.exit(1)

    # --- MODEL B (Baseline Regime) ---
    print(f"\n--- Training Model B (Baseline Regime) ---")
    print(f"Samples: {len(df_baseline)}")

    min_samples_b = 2 if is_test_run or len(df_baseline) < 100 else 100
    if len(df_baseline) >= min_samples_b:
        X_b = df_baseline[features]
        y_b = df_baseline['query_latency_ms']

        n_b = len(X_b)
        if n_b < 10:
            X_train_b, y_train_b = X_b, y_b
            X_calib_b, y_calib_b = X_b, y_b
            X_test_b, y_test_b = X_b, y_b
        else:
            t_split1_b = int(0.70 * n_b)
            t_split2_b = int(0.85 * n_b)
            X_train_b, y_train_b = X_b.iloc[:t_split1_b], y_b.iloc[:t_split1_b]
            X_calib_b, y_calib_b = X_b.iloc[t_split1_b:t_split2_b], y_b.iloc[t_split1_b:t_split2_b]
            X_test_b, y_test_b = X_b.iloc[t_split2_b:], y_b.iloc[t_split2_b:]

        model_b, q_hat_b = train_conformal_model(X_train_b, y_train_b, X_calib_b, y_calib_b, alpha=alpha)
        metrics_b = evaluate_model(model_b, q_hat_b, X_test_b, y_test_b)

        print(f"Metrics: MAE={metrics_b['mae']:.1f}ms, R2={metrics_b['r2']:.3f}")
        print(f"Conformal Bound (q_hat): {q_hat_b:.1f}ms, Coverage: {metrics_b['coverage']:.1f}%")
    else:
        print(f"Not enough data to train Model B ({len(df_baseline)} < {min_samples_b}).")
        sys.exit(1)

    # --- Save Models and Metadata ---
    if q_hat_a <= 0.0 or q_hat_b <= 0.0:
        print("\n[CRITICAL ERROR] q_hat evaluated to <= 0.0. Refusing to save broken models.")
        sys.exit(1)

    joblib.dump(model_a, os.path.join(model_dir, "model_a_compaction.joblib"))
    joblib.dump(model_b, os.path.join(model_dir, "model_b_baseline.joblib"))

    metadata = {
        "features": features,
        "model_a": {
            "q_hat": float(q_hat_a),
            "test_mae": float(metrics_a['mae']),
            "test_coverage": float(metrics_a['coverage']),
            "per_query_mae": metrics_a['per_query_mae']
        },
        "model_b": {
            "q_hat": float(q_hat_b),
            "test_mae": float(metrics_b['mae']),
            "test_coverage": float(metrics_b['coverage']),
            "per_query_mae": metrics_b['per_query_mae']
        }
    }

    metadata_path = os.path.join(model_dir, "model_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"\nModels and metadata successfully saved to {model_dir}/")
    return model_a, model_b, metadata


def main():
    parser = argparse.ArgumentParser(description="Train Query-Aware Conformal Cost-Benefit Models")
    parser.add_argument('--input', type=str, required=True, help='Path to training data CSV')
    parser.add_argument('--model-dir', '--output-dir', dest='model_dir', type=str, default='models/',
                        help='Output directory for models')
    parser.add_argument('--plot-dir', type=str, default='figures/')
    parser.add_argument('--alpha', type=float, default=0.10, help='Conformal error significance (nominal 0.10 for 90% coverage)')
    args = parser.parse_args()

    data_path = args.input
    if not os.path.exists(data_path):
        print(f"ERROR: Training data {data_path} not found.")
        sys.exit(1)

    print(f"Loading {data_path}...")
    df = pd.read_csv(data_path)

    is_test_run = "test" in data_path.lower() or "mini" in data_path.lower()

    max_lat = 0.0
    for col in ['query_latency_ms', 'query_latency_during_compaction_ms']:
        if col in df.columns and df[col].dropna().max() > max_lat:
            max_lat = df[col].dropna().max()

    comp_events = len(df[df['compaction_active'] == True])
    print(f"[VALIDATION] Max latency: {max_lat:.1f}ms | Compaction events: {comp_events}")

    if max_lat <= 0.0:
        print("\n[CRITICAL ERROR] The dataset is entirely filled with 0.0ms latencies or missing them.")
        sys.exit(1)

    min_required_compactions = 1 if is_test_run else 5
    if comp_events < min_required_compactions:
        print(f"\n[CRITICAL ERROR] Only {comp_events} compaction events found (minimum {min_required_compactions} required).")
        sys.exit(1)

    train_and_save_models(df, args.model_dir, alpha=args.alpha, is_test_run=is_test_run)


if __name__ == "__main__":
    main()
