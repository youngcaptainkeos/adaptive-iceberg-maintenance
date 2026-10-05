import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

WORKSPACE_DIR = "/media/shashank/Data1/PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
RESULTS_DIR = os.path.join(PHASE3B_DIR, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Set global style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.4)
sns.set_palette("Set2")

def generate_ood_plots():
    print("Loading data for plots...")
    
    ood_df = pd.read_csv(os.path.join(RESULTS_DIR, "conformal_ood_results.csv"))
    orig_df = pd.read_csv(os.path.join(RESULTS_DIR, "dataset_predictive_signals.csv"))
    
    with open(os.path.join(RESULTS_DIR, "ood_conformal_summary.txt"), "r") as f:
        summary_lines = f.readlines()
        
    summary = {}
    for line in summary_lines:
        k, v = line.strip().split(": ")
        summary[k] = float(v)
        
    # Plot 1: Actual vs Predicted Scatter
    plt.figure(figsize=(8, 8))
    sns.scatterplot(data=ood_df, x="predicted_qir_pct", y="qir_pct", hue="frag_level", palette="viridis", alpha=0.8, s=100)
    
    # Add y=x line
    min_val = min(ood_df["predicted_qir_pct"].min(), ood_df["qir_pct"].min())
    max_val = max(ood_df["predicted_qir_pct"].max(), ood_df["qir_pct"].max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', label="Perfect Prediction")
    
    from sklearn.metrics import r2_score
    r2 = r2_score(ood_df["qir_pct"], ood_df["predicted_qir_pct"])
    plt.text(0.05, 0.95, f"Overall R²: {r2:.3f}", transform=plt.gca().transAxes, fontsize=14,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
             
    plt.title("OOD Actual vs Predicted QIR (%)")
    plt.xlabel("Predicted QIR (%)")
    plt.ylabel("Actual QIR (%)")
    plt.legend(title="Frag Level")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "ood_actual_vs_predicted.png"), dpi=300)
    plt.close()
    
    # Plot 2: MAE by Frag Level
    plt.figure(figsize=(10, 6))
    
    # Compute MAEs
    frag_maes = ood_df.groupby("frag_level")["absolute_error"].mean().reset_index()
    # Add in-distribution for comparison
    frag_maes.loc[len(frag_maes.index)] = ['In-Distribution', 3.42] # Hardcoded from Phase 3 baseline
    
    sns.barplot(data=frag_maes, x="frag_level", y="absolute_error", palette="coolwarm")
    plt.axvline(x=1.5, color='black', linestyle='--', linewidth=2, label="Interpolation / Extrapolation Boundary")
    
    plt.title("MAE by Fragmentation Level (OOD vs In-Distribution)")
    plt.xlabel("Fragmentation Level")
    plt.ylabel("Mean Absolute Error (%)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "ood_mae_by_frag_level.png"), dpi=300)
    plt.close()
    
    # Plot 3: Residuals by Frag
    plt.figure(figsize=(10, 6))
    ood_df["residual"] = ood_df["qir_pct"] - ood_df["predicted_qir_pct"]
    sns.boxplot(data=ood_df, x="frag_level", y="residual", palette="pastel")
    plt.axhline(0, color='red', linestyle='--')
    plt.title("Prediction Residuals by Fragmentation Level")
    plt.xlabel("Fragmentation Level")
    plt.ylabel("Residual (Actual - Predicted) (%)")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "ood_residuals_by_frag.png"), dpi=300)
    plt.close()
    
    # Plot 4: Conformal Coverage
    plt.figure(figsize=(12, 6))
    
    # Sort for visual clarity
    sorted_df = ood_df.sort_values("predicted_qir_pct").reset_index(drop=True)
    
    plt.fill_between(sorted_df.index, sorted_df["conformal_lower_bound"], sorted_df["conformal_upper_bound"], 
                     color="gray", alpha=0.3, label="Conformal Prediction Interval")
    
    # Color by coverage
    covered = sorted_df[sorted_df["is_covered"]]
    uncovered = sorted_df[~sorted_df["is_covered"]]
    
    plt.scatter(covered.index, covered["qir_pct"], color="blue", label="Covered", alpha=0.7)
    plt.scatter(uncovered.index, uncovered["qir_pct"], color="red", label="Uncovered", alpha=0.9, marker="x", s=100)
    plt.plot(sorted_df.index, sorted_df["predicted_qir_pct"], color="black", linestyle="--", label="Point Prediction", alpha=0.7)
    
    plt.title(f"OOD Conformal Coverage (Empirical: {summary['overall_coverage']:.1f}%)")
    plt.xlabel("OOD Test Instances (Sorted by Prediction)")
    plt.ylabel("QIR (%)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "ood_conformal_coverage.png"), dpi=300)
    plt.close()
    
    # Plot 5: Interpolation vs Extrapolation
    plt.figure(figsize=(10, 6))
    
    metrics = {
        "Group": ["Interpolation", "Interpolation", "Extrapolation", "Extrapolation"],
        "Metric": ["MAE", "Coverage", "MAE", "Coverage"],
        "Value": [
            ood_df[ood_df["ood_type"]=="Interpolation"]["absolute_error"].mean(),
            summary["interpolation_coverage"],
            ood_df[ood_df["ood_type"]=="Extrapolation"]["absolute_error"].mean(),
            summary["extrapolation_coverage"]
        ]
    }
    metrics_df = pd.DataFrame(metrics)
    
    g = sns.catplot(
        data=metrics_df, kind="bar",
        x="Group", y="Value", hue="Metric",
        palette="dark", alpha=.6, height=6, aspect=1.2
    )
    g.despine(left=True)
    g.set_axis_labels("OOD Type", "Value (%)")
    plt.title("Interpolation vs Extrapolation Performance")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "ood_interpolation_vs_extrapolation.png"), dpi=300)
    plt.close()
    
    # Plot 6: Combined Dataset Scatter
    plt.figure(figsize=(10, 8))
    
    # Plot original in gray
    sns.scatterplot(data=orig_df, x="baseline_duration_ms", y="concurrent_duration_ms", 
                    color="lightgray", alpha=0.6, label="Training Data (In-Dist)", s=50)
                    
    # Plot OOD colored by frag
    sns.scatterplot(data=ood_df, x="baseline_duration_ms", y="concurrent_duration_ms", 
                    hue="frag_level", palette="viridis", alpha=0.9, s=100)
                    
    plt.title("Combined Dataset: Original vs OOD Configurations")
    plt.xlabel("Baseline Duration (ms)")
    plt.ylabel("Concurrent Duration (ms)")
    plt.legend(title="Data Source / Frag")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "ood_combined_dataset_scatter.png"), dpi=300)
    plt.close()
    
    # Plot 7: Feature Distribution Shift
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    features = ["baseline_duration_ms", "concurrent_duration_ms", "pre_cpu_util_pct"]
    titles = ["Baseline Duration (ms)", "Concurrent Duration (ms)", "Pre-CPU Utilization (%)"]
    
    orig_df["Dataset"] = "Training (In-Dist)"
    ood_df["Dataset"] = "OOD Test"
    
    combined = pd.concat([orig_df[features + ["Dataset"]], ood_df[features + ["Dataset"]]], ignore_index=True)
    
    for i, (feat, title) in enumerate(zip(features, titles)):
        sns.violinplot(data=combined, x="Dataset", y=feat, ax=axes[i], palette="muted", split=False)
        axes[i].set_title(title)
        axes[i].set_ylabel("")
        
    plt.suptitle("Covariate Shift: Feature Distributions between Training and OOD Data", y=1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "ood_feature_distribution_shift.png"), dpi=300)
    plt.close()
    
    print("Successfully generated all OOD plots in results/plots/")

if __name__ == "__main__":
    generate_ood_plots()
