import pandas as pd
import numpy as np
import joblib
import json
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os

import os
WORKSPACE_DIR = os.environ.get("REPO_DIR", "/media/shashank/Data1/PDocuments/Capstone/implementation")
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
RESULTS_DIR = os.path.join(PHASE3B_DIR, "results")

def evaluate_ood():
    print("Loading model and metadata...")
    model_path = os.path.join(PHASE3B_DIR, "models", "best_regressor.joblib")
    meta_path = os.path.join(PHASE3B_DIR, "models", "best_regressor_metadata.json")
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        return
        
    model = joblib.load(model_path)
    with open(meta_path, 'r') as f:
        meta = json.load(f)
        
    feature_names = meta['feature_names']
    
    print("Loading OOD dataset...")
    df_path = os.path.join(RESULTS_DIR, "dataset_ood_signals.csv")
    if not os.path.exists(df_path):
        print(f"Error: Dataset not found at {df_path}")
        return
        
    df = pd.read_csv(df_path)
    
    print("Applying feature engineering...")
    exclude_cols = ["config_id", "qir_pct", "sla_violation_10pct", "repetition", "window_id", "timestamp", "client_start_time_concurrent", "client_end_time_concurrent"]
    
    # One-hot encode categorical features identically
    X = pd.get_dummies(df, columns=["workload_type", "scheduler_mode", "query"], drop_first=False)
    
    # Ensure all required columns exist, fill with 0 if missing (e.g., if a query type is missing)
    for col in feature_names:
        if col not in X.columns:
            X[col] = 0
            
    # Filter only the features used in training, in the exact same order
    X = X[feature_names]
    
    # Ensure they are numeric
    X = X.astype(float)
    y = df["qir_pct"]
    
    print("Generating predictions...")
    y_pred = model.predict(X)
    df["predicted_qir_pct"] = y_pred
    df["absolute_error"] = np.abs(y - y_pred)
    
    # Calculate overall metrics
    overall_mae = mean_absolute_error(y, y_pred)
    overall_rmse = np.sqrt(mean_squared_error(y, y_pred))
    overall_r2 = r2_score(y, y_pred)
    
    print(f"\nOverall OOD Metrics:")
    print(f"MAE:  {overall_mae:.4f}%")
    print(f"RMSE: {overall_rmse:.4f}%")
    print(f"R2:   {overall_r2:.4f}")
    
    # Compute per-fragmentation level metrics
    df["frag_level"] = df["frag_files"].astype(int)
    frag_results = []
    
    for frag in sorted(df["frag_level"].unique()):
        subset = df[df["frag_level"] == frag]
        mae = mean_absolute_error(subset["qir_pct"], subset["predicted_qir_pct"])
        frag_results.append({"frag_level": frag, "mae": mae})
        
    frag_df = pd.DataFrame(frag_results)
    
    # Interpolation (100, 350) vs Extrapolation (750)
    df["ood_type"] = df["frag_level"].apply(lambda x: "Extrapolation" if x > 500 else "Interpolation")
    inter_df = df[df["ood_type"] == "Interpolation"]
    extra_df = df[df["ood_type"] == "Extrapolation"]
    
    inter_mae = mean_absolute_error(inter_df["qir_pct"], inter_df["predicted_qir_pct"]) if not inter_df.empty else None
    extra_mae = mean_absolute_error(extra_df["qir_pct"], extra_df["predicted_qir_pct"]) if not extra_df.empty else None
    
    print("\nInterpolation vs Extrapolation:")
    print(f"Interpolation MAE: {inter_mae:.4f}%")
    print(f"Extrapolation MAE: {extra_mae:.4f}%")
    
    # Save overall summary
    eval_results = pd.DataFrame([{
        "metric_type": "overall",
        "mae": overall_mae,
        "rmse": overall_rmse,
        "r2": overall_r2,
        "interpolation_mae": inter_mae,
        "extrapolation_mae": extra_mae
    }])
    eval_results.to_csv(os.path.join(RESULTS_DIR, "ood_evaluation_results.csv"), index=False)
    
    # Save per-config results
    per_config = df.groupby(["config_id", "frag_level", "ood_type"]).agg(
        mean_actual_qir=("qir_pct", "mean"),
        mean_predicted_qir=("predicted_qir_pct", "mean"),
        mae=("absolute_error", "mean")
    ).reset_index()
    
    per_config.to_csv(os.path.join(RESULTS_DIR, "ood_per_config_results.csv"), index=False)
    
    # Save predictions onto dataset for plots
    df.to_csv(os.path.join(RESULTS_DIR, "dataset_ood_predictions.csv"), index=False)
    print("Saved all evaluation results successfully.")

if __name__ == "__main__":
    evaluate_ood()
