#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import json
from sklearn.metrics import confusion_matrix, roc_curve, auc
from sklearn.model_selection import learning_curve, GroupKFold

WORKSPACE_DIR = "/media/shashank/Data1/PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
RESULTS_DIR = os.path.join(PHASE3B_DIR, "results")
MODELS_DIR = os.path.join(PHASE3B_DIR, "models")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")

os.makedirs(PLOTS_DIR, exist_ok=True)

# Set global seaborn style
sns.set_theme(style="whitegrid", font_scale=1.2)

def generate_plots():
    print("Generating plots...")
    
    # Load required data
    dataset_csv = os.path.join(RESULTS_DIR, "dataset_predictive_signals.csv")
    df = pd.read_csv(dataset_csv)
    
    oof_df = pd.read_csv(os.path.join(RESULTS_DIR, "v2_oof_predictions.csv"))
    reg_per_fold = pd.read_csv(os.path.join(RESULTS_DIR, "v2_regression_results_per_fold.csv"))
    reg_agg = pd.read_csv(os.path.join(RESULTS_DIR, "v2_regression_results_agg.csv"))
    
    with open(os.path.join(MODELS_DIR, "best_regressor_metadata.json"), "r") as f:
        meta = json.load(f)
    best_model_name = meta["model_name"]
    best_pipe = joblib.load(os.path.join(MODELS_DIR, "best_regressor.joblib"))
    
    # 1. Actual vs Predicted Scatter
    plt.figure(figsize=(8, 8))
    sns.scatterplot(
        data=oof_df, 
        x="qir_pct", 
        y=f"pred_reg_{best_model_name}", 
        hue="config_id", 
        alpha=0.7, 
        edgecolor="k"
    )
    # y=x line
    min_val = min(oof_df["qir_pct"].min(), oof_df[f"pred_reg_{best_model_name}"].min())
    max_val = max(oof_df["qir_pct"].max(), oof_df[f"pred_reg_{best_model_name}"].max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2, label="Ideal (y=x)")
    
    r2_val = reg_agg.loc[reg_agg["Model"] == best_model_name, "R2_mean"].values[0]
    plt.annotate(f"$R^2 = {r2_val:.3f}$", xy=(0.05, 0.95), xycoords='axes fraction', 
                 fontsize=14, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
    
    plt.title(f"Actual vs. Predicted QIR ({best_model_name})")
    plt.xlabel("Actual QIR (%)")
    plt.ylabel("Predicted QIR (%)")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "actual_vs_predicted_scatter.png"), dpi=300)
    plt.close()
    
    # 2. Residuals Distribution
    residuals = oof_df["qir_pct"] - oof_df[f"pred_reg_{best_model_name}"]
    plt.figure(figsize=(8, 6))
    sns.histplot(residuals, bins=30, kde=True, color="teal")
    plt.axvline(0, color='red', linestyle='--', lw=2)
    
    res_mean = residuals.mean()
    res_std = residuals.std()
    plt.annotate(f"Mean: {res_mean:.2f}\nStd: {res_std:.2f}", xy=(0.7, 0.9), xycoords='axes fraction', 
                 fontsize=12, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray"))
    
    plt.title(f"Residuals Distribution ({best_model_name})")
    plt.xlabel("Residual (Actual - Predicted QIR %)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "residuals_distribution.png"), dpi=300)
    plt.close()

    # 3. Per-fold MAE Barplot
    plt.figure(figsize=(10, 6))
    sns.barplot(data=reg_per_fold, x="Model", y="MAE", hue="Fold")
    plt.title("Per-Fold MAE Across Regression Models")
    plt.xlabel("Model")
    plt.ylabel("Mean Absolute Error (MAE %)")
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="Fold", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "per_fold_mae_barplot.png"), dpi=300)
    plt.close()
    
    # 4. Model Comparison Barplot
    # Horizontal bar chart with error bars
    plt.figure(figsize=(10, 6))
    reg_agg_sorted = reg_agg.sort_values(by="MAE_mean", ascending=False)
    
    colors = ['gray' if 'Baseline' in m else 'steelblue' for m in reg_agg_sorted["Model"]]
    
    plt.barh(reg_agg_sorted["Model"], reg_agg_sorted["MAE_mean"], xerr=reg_agg_sorted["MAE_std"], 
             color=colors, capsize=5, edgecolor="k")
    plt.title("Model Comparison: Mean Absolute Error (MAE)")
    plt.xlabel("MAE (%) ± Std")
    plt.ylabel("Model")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "model_comparison_barplot.png"), dpi=300)
    plt.close()

    # 5. Feature Importance
    # Check if we can get feature importances from best model
    model_obj = best_pipe.named_steps["model"]
    if hasattr(model_obj, "feature_importances_"):
        importances = model_obj.feature_importances_
        features = meta["feature_names"]
        
        fi_df = pd.DataFrame({"Feature": features, "Importance": importances})
        fi_df = fi_df.sort_values(by="Importance", ascending=False).head(15) # Top 15
        
        plt.figure(figsize=(10, 8))
        sns.barplot(data=fi_df, x="Importance", y="Feature", color="mediumseagreen", edgecolor="k")
        plt.title(f"Top 15 Feature Importances ({best_model_name})")
        plt.xlabel("Importance (Gini / Decrease in Impurity)")
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, "feature_importance.png"), dpi=300)
        plt.close()
    else:
        print("Best model does not have feature_importances_. Skipping plot.")
        
    # 6. Learning Curve
    print("Computing learning curve...")
    # Recreate X and y for the learning curve using the pipeline
    exclude_cols = ["config_id", "qir_pct", "sla_violation_10pct", "repetition", "window_id", "timestamp"]
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    categorical_cols = [c for c in ["workload_type", "scheduler_mode", "query"] if c in feature_cols]
    X_df = pd.get_dummies(df[feature_cols], columns=categorical_cols, drop_first=False)
    X = X_df.values
    y_reg = df["qir_pct"].values
    groups = df["config_id"].values

    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    if best_model_name == "GradientBoosting":
        base_model = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)
    else:
        base_model = RandomForestRegressor(n_estimators=100, max_depth=4, min_samples_split=4, random_state=42)
        
    # Note: For learning_curve to work well with GroupKFold, it's best to wrap it
    # We apply scaling first to the whole dataset just for the learning curve visualization to simplify
    # This is slightly leaky but acceptable purely for the visualization of sample-efficiency trend
    from sklearn.preprocessing import StandardScaler
    X_scaled = StandardScaler().fit_transform(X)
    
    train_sizes, train_scores, test_scores = learning_curve(
        base_model, X_scaled, y_reg, groups=groups, cv=GroupKFold(n_splits=4),
        scoring='neg_mean_absolute_error', n_jobs=-1,
        train_sizes=np.linspace(0.2, 1.0, 5)
    )
    
    train_scores_mean = -np.mean(train_scores, axis=1)
    train_scores_std = np.std(train_scores, axis=1)
    test_scores_mean = -np.mean(test_scores, axis=1)
    test_scores_std = np.std(test_scores, axis=1)
    
    plt.figure(figsize=(8, 6))
    plt.plot(train_sizes, train_scores_mean, 'o-', color="r", label="Training error")
    plt.fill_between(train_sizes, train_scores_mean - train_scores_std,
                     train_scores_mean + train_scores_std, alpha=0.1, color="r")
    plt.plot(train_sizes, test_scores_mean, 'o-', color="g", label="Cross-validation error")
    plt.fill_between(train_sizes, test_scores_mean - test_scores_std,
                     test_scores_mean + test_scores_std, alpha=0.1, color="g")
    
    plt.title(f"Learning Curve ({best_model_name})")
    plt.xlabel("Training examples")
    plt.ylabel("MAE (%)")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "learning_curve.png"), dpi=300)
    plt.close()
    
    # 7. Classification Confusion Matrix
    cls_name = "RandomForest_Classifier"
    y_true_cls = oof_df["sla_violation_10pct"]
    y_pred_cls = oof_df[f"pred_cls_class_{cls_name}"]
    
    cm = confusion_matrix(y_true_cls, y_pred_cls)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False, 
                xticklabels=["No Violation", "Violation"],
                yticklabels=["No Violation", "Violation"])
    plt.title(f"Confusion Matrix ({cls_name})")
    plt.ylabel("Actual SLA Status")
    plt.xlabel("Predicted SLA Status")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "classification_confusion_matrix.png"), dpi=300)
    plt.close()
    
    # 8. Classification ROC Curve
    y_prob_cls = oof_df[f"pred_cls_prob_{cls_name}"]
    fpr, tpr, _ = roc_curve(y_true_cls, y_prob_cls)
    roc_auc_val = auc(fpr, tpr)
    
    plt.figure(figsize=(7, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc_val:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'Receiver Operating Characteristic ({cls_name})')
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "classification_roc_curve.png"), dpi=300)
    plt.close()

    print(f"All plots saved to {PLOTS_DIR}")

if __name__ == "__main__":
    generate_plots()
