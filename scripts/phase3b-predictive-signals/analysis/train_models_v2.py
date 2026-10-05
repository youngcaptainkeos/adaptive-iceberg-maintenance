#!/usr/bin/env python3
import os
import sys
import pandas as pd
import numpy as np
import json
import joblib

from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.dummy import DummyRegressor, DummyClassifier
from sklearn.linear_model import Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
                             roc_auc_score, average_precision_score, precision_score,
                             recall_score, f1_score, confusion_matrix)

WORKSPACE_DIR = "/media/shashank/Data1/PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
RESULTS_DIR = os.path.join(PHASE3B_DIR, "results")
MODELS_DIR = os.path.join(PHASE3B_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

def run():
    print("=== 3a. Data Loading ===")
    dataset_csv = os.path.join(RESULTS_DIR, "dataset_predictive_signals.csv")
    df = pd.read_csv(dataset_csv)
    
    print(f"Dataset Shape: {df.shape}")
    print("\nColumn Names and Dtypes:")
    print(df.dtypes)
    
    print("\nClass Distribution (sla_violation_10pct):")
    print(df["sla_violation_10pct"].value_counts(normalize=True) * 100)
    
    print("\nPer-config_id Sample Counts:")
    print(df["config_id"].value_counts())
    
    print("\n=== 3b. Feature Engineering ===")
    
    exclude_cols = ["config_id", "qir_pct", "sla_violation_10pct", "repetition", "window_id", "timestamp", "client_start_time_concurrent", "client_end_time_concurrent"]
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    
    # Identify categorical columns and get dummies
    categorical_cols = ["workload_type", "scheduler_mode", "query"]
    categorical_cols = [c for c in categorical_cols if c in feature_cols]
    
    X_df = pd.get_dummies(df[feature_cols], columns=categorical_cols, drop_first=False)
    
    X = X_df.values
    y_reg = df["qir_pct"].values
    y_cls = df["sla_violation_10pct"].values
    groups = df["config_id"].values
    
    print(f"Final feature count: {X.shape[1]}")
    
    print("\n=== 3c & 3d. Models to Train and Evaluate ===")
    
    reg_models = {
        "Mean_Baseline": DummyRegressor(strategy='mean'),
        "Median_Baseline": DummyRegressor(strategy='median'),
        "Ridge": Ridge(alpha=1.0),
        "Lasso": Lasso(alpha=0.1),
        "RandomForest": RandomForestRegressor(n_estimators=100, max_depth=4, min_samples_split=4, random_state=42),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)
    }
    
    cls_models = {
        "Majority_Baseline": DummyClassifier(strategy='most_frequent'),
        "RandomForest_Classifier": RandomForestClassifier(n_estimators=100, max_depth=4, class_weight='balanced', random_state=42)
    }
    
    gkf = GroupKFold(n_splits=4)
    
    reg_results = []
    cls_results = []
    
    # Store out of fold predictions for analysis later
    oof_preds_reg = {name: np.zeros(len(df)) for name in reg_models}
    oof_preds_cls = {name: np.zeros(len(df)) for name in cls_models}
    
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y_reg, groups)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train_reg, y_val_reg = y_reg[train_idx], y_reg[val_idx]
        y_train_cls, y_val_cls = y_cls[train_idx], y_cls[val_idx]
        
        # Regression
        for name, model in reg_models.items():
            pipe = Pipeline([
                ("scaler", StandardScaler()),
                ("model", model)
            ])
            pipe.fit(X_train, y_train_reg)
            preds = pipe.predict(X_val)
            oof_preds_reg[name][val_idx] = preds
            
            mae = mean_absolute_error(y_val_reg, preds)
            rmse = np.sqrt(mean_squared_error(y_val_reg, preds))
            r2 = r2_score(y_val_reg, preds)
            
            reg_results.append({
                "Model": name,
                "Fold": fold,
                "MAE": mae,
                "RMSE": rmse,
                "R2": r2
            })
            
        # Classification
        for name, model in cls_models.items():
            pipe = Pipeline([
                ("scaler", StandardScaler()),
                ("model", model)
            ])
            pipe.fit(X_train, y_train_cls)
            preds = pipe.predict(X_val)
            
            if hasattr(pipe, "predict_proba"):
                probs = pipe.predict_proba(X_val)[:, 1]
            else:
                probs = preds
                
            oof_preds_cls[name][val_idx] = probs
            
            try:
                roc_auc = roc_auc_score(y_val_cls, probs)
            except ValueError:
                roc_auc = np.nan
                
            pr_auc = average_precision_score(y_val_cls, probs)
            prec = precision_score(y_val_cls, preds, zero_division=0)
            rec = recall_score(y_val_cls, preds, zero_division=0)
            f1 = f1_score(y_val_cls, preds, average='macro', zero_division=0)
            cm = confusion_matrix(y_val_cls, preds, labels=[0, 1])
            cm_str = f"TN={cm[0,0]}, FP={cm[0,1]}, FN={cm[1,0]}, TP={cm[1,1]}"
            
            cls_results.append({
                "Model": name,
                "Fold": fold,
                "ROC_AUC": roc_auc,
                "PR_AUC": pr_auc,
                "Precision": prec,
                "Recall": rec,
                "F1_Macro": f1,
                "Confusion_Matrix": cm_str
            })

    # Aggregating Results
    reg_df = pd.DataFrame(reg_results)
    reg_agg = reg_df.groupby("Model").agg({
        "MAE": ["mean", "std"],
        "RMSE": ["mean", "std"],
        "R2": ["mean", "std"]
    }).reset_index()
    
    # Flatten multi-index columns
    reg_agg.columns = ["_".join(a).strip("_") for a in reg_agg.columns.to_flat_index()]
    
    cls_df = pd.DataFrame(cls_results)
    cls_agg = cls_df.groupby("Model").agg({
        "ROC_AUC": ["mean", "std"],
        "PR_AUC": ["mean", "std"],
        "F1_Macro": ["mean", "std"]
    }).reset_index()
    cls_agg.columns = ["_".join(a).strip("_") for a in cls_agg.columns.to_flat_index()]
    
    # Save detailed and aggregated results
    reg_df.to_csv(os.path.join(RESULTS_DIR, "v2_regression_results_per_fold.csv"), index=False)
    reg_agg.to_csv(os.path.join(RESULTS_DIR, "v2_regression_results_agg.csv"), index=False)
    
    cls_df.to_csv(os.path.join(RESULTS_DIR, "v2_classification_results_per_fold.csv"), index=False)
    cls_agg.to_csv(os.path.join(RESULTS_DIR, "v2_classification_results_agg.csv"), index=False)
    
    # Generate OOF predictions CSV for plots
    oof_df = df[["config_id", "qir_pct", "sla_violation_10pct"]].copy()
    for name, preds in oof_preds_reg.items():
        oof_df[f"pred_reg_{name}"] = preds
    for name, probs in oof_preds_cls.items():
        oof_df[f"pred_cls_prob_{name}"] = probs
        oof_df[f"pred_cls_class_{name}"] = (probs >= 0.5).astype(int)
    oof_df.to_csv(os.path.join(RESULTS_DIR, "v2_oof_predictions.csv"), index=False)

    print("\n=== 3e. Comparison Table ===")
    
    new_rf_mae = reg_agg[reg_agg["Model"] == "RandomForest"]["MAE_mean"].values[0]
    new_rf_r2 = reg_agg[reg_agg["Model"] == "RandomForest"]["R2_mean"].values[0]
    
    # Old model numbers manually inserted based on baseline run output
    old_rf_mae = 5.38
    old_rf_r2 = float('nan') # Old code did not output R2
    
    comp_data = []
    for model in reg_agg["Model"].unique():
        new_mae = reg_agg[reg_agg["Model"] == model]["MAE_mean"].values[0]
        new_r2 = reg_agg[reg_agg["Model"] == model]["R2_mean"].values[0]
        
        old_mae = float('nan')
        old_r2 = float('nan')
        if model == "RandomForest":
            old_mae = old_rf_mae
            old_r2 = old_rf_r2
        elif model == "Ridge":
            old_mae = 6.91
        elif model == "Lasso":
            old_mae = 7.35
            
        comp_data.append({
            "Model": model,
            "Old MAE (leaky)": old_mae,
            "New MAE (correct)": new_mae,
            "Old R2": old_r2,
            "New R2": new_r2
        })
        
    comp_df = pd.DataFrame(comp_data)
    print(comp_df.to_string(index=False))
    comp_df.to_csv(os.path.join(RESULTS_DIR, "v2_comparison_old_vs_new.csv"), index=False)
    
    print("\n=== 3g. Save Trained Models ===")
    
    # We find the best model (lowest MAE_mean)
    best_model_name = reg_agg.loc[reg_agg["MAE_mean"].idxmin()]["Model"]
    print(f"Best Regressor found: {best_model_name}")
    
    # Train it on the full dataset to serialize it
    final_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", reg_models[best_model_name])
    ])
    final_pipe.fit(X, y_reg)
    
    joblib.dump(final_pipe, os.path.join(MODELS_DIR, "best_regressor.joblib"))
    
    meta = {
        "model_name": best_model_name,
        "feature_names": X_df.columns.tolist(),
        "training_config_ids": df["config_id"].unique().tolist(),
        "hyperparams": final_pipe.named_steps["model"].get_params(),
        "scaler_mean": final_pipe.named_steps["scaler"].mean_.tolist(),
        "scaler_scale": final_pipe.named_steps["scaler"].scale_.tolist()
    }
    
    with open(os.path.join(MODELS_DIR, "best_regressor_metadata.json"), "w") as f:
        json.dump(meta, f, indent=4)
        
    print("Saved best_regressor.joblib and metadata.")

if __name__ == "__main__":
    run()
