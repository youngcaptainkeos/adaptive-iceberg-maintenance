#!/usr/bin/env python3
import os
import sys
import csv
import math

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
PHASE3D_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3d-validation-generalization")
RESULTS_DIR = os.path.join(PHASE3D_DIR, "results")

os.makedirs(RESULTS_DIR, exist_ok=True)

def mean_absolute_error(y_true, y_pred):
    return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true)

def root_mean_squared_error(y_true, y_pred):
    return math.sqrt(sum((t - p)**2 for t, p in zip(y_true, y_pred)) / len(y_true))

def run_trivial_baselines():
    dataset_csv = os.path.join(PHASE3B_DIR, "results/dataset_predictive_signals.csv")
    loco_csv = os.path.join(RESULTS_DIR, "loco_regression_results.csv")

    if not os.path.exists(dataset_csv) or not os.path.exists(loco_csv):
        print(f"Error: Required CSV missing!", file=sys.stderr)
        sys.exit(1)

    dataset = []
    with open(dataset_csv, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            dataset.append(r)

    config_ids = sorted(list(set(r["config_id"] for r in dataset)))

    loco_rows = []
    with open(loco_csv, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            loco_rows.append(r)

    baseline_results = []

    # Evaluate trivial baselines fold-by-fold
    base_a_maes, base_a_rmses = [], []
    base_b_maes, base_b_rmses = [], []
    base_c_maes, base_c_rmses = [], []

    for held_out_cfg in config_ids:
        train_rows = [r for r in dataset if r["config_id"] != held_out_cfg]
        test_rows = [r for r in dataset if r["config_id"] == held_out_cfg]

        y_train = [float(r["qir_pct"]) for r in train_rows]
        y_test = [float(r["qir_pct"]) for r in test_rows]

        # Baseline A: Training Mean
        mean_tr = sum(y_train) / len(y_train)
        preds_a = [mean_tr] * len(y_test)
        mae_a = mean_absolute_error(y_test, preds_a)
        rmse_a = root_mean_squared_error(y_test, preds_a)
        base_a_maes.append(mae_a)
        base_a_rmses.append(rmse_a)

        # Baseline B: Zero QIR
        preds_b = [0.0] * len(y_test)
        mae_b = mean_absolute_error(y_test, preds_b)
        rmse_b = root_mean_squared_error(y_test, preds_b)
        base_b_maes.append(mae_b)
        base_b_rmses.append(rmse_b)

        # Baseline C: Training Median
        sorted_y_tr = sorted(y_train)
        med_tr = sorted_y_tr[len(sorted_y_tr) // 2]
        preds_c = [med_tr] * len(y_test)
        mae_c = mean_absolute_error(y_test, preds_c)
        rmse_c = root_mean_squared_error(y_test, preds_c)
        base_c_maes.append(mae_c)
        base_c_rmses.append(rmse_c)

    mean_base_a_mae = sum(base_a_maes) / len(base_a_maes)
    mean_base_b_mae = sum(base_b_maes) / len(base_b_maes)
    mean_base_c_mae = sum(base_c_maes) / len(base_c_maes)

    mean_base_a_rmse = sum(base_a_rmses) / len(base_a_rmses)
    mean_base_b_rmse = sum(base_b_rmses) / len(base_b_rmses)
    mean_base_c_rmse = sum(base_c_rmses) / len(base_c_rmses)

    strongest_trivial_mae = min(mean_base_a_mae, mean_base_b_mae, mean_base_c_mae)
    strongest_trivial_name = "Baseline B (Zero QIR)" if strongest_trivial_mae == mean_base_b_mae else ("Baseline C (Median QIR)" if strongest_trivial_mae == mean_base_c_mae else "Baseline A (Mean QIR)")

    print("=========================================")
    print("LOCO-CV Comparison vs Trivial Baselines")
    print("=========================================")
    print(f"Baseline A (Training Mean):   Mean MAE = {mean_base_a_mae:.2f}%, RMSE = {mean_base_a_rmse:.2f}%")
    print(f"Baseline B (Zero Interference): Mean MAE = {mean_base_b_mae:.2f}%, RMSE = {mean_base_b_rmse:.2f}%")
    print(f"Baseline C (Training Median): Mean MAE = {mean_base_c_mae:.2f}%, RMSE = {mean_base_c_rmse:.2f}%")
    print(f"Strongest Trivial Baseline:  {strongest_trivial_name} (Mean MAE = {strongest_trivial_mae:.2f}%)\n")

    all_models = [
        ("Baseline A (Training Mean)", mean_base_a_mae, mean_base_a_rmse),
        ("Baseline B (Zero Interference)", mean_base_b_mae, mean_base_b_rmse),
        ("Baseline C (Training Median)", mean_base_c_mae, mean_base_c_rmse),
    ]

    # Add LOCO ML models
    ml_model_names = sorted(list(set(r["model"] for r in loco_rows)))
    for m in ml_model_names:
        m_rows = [r for r in loco_rows if r["model"] == m]
        m_maes = [float(r["mae"]) for r in m_rows]
        m_rmses = [float(r["rmse"]) for r in m_rows]
        avg_mae = sum(m_maes) / len(m_maes)
        avg_rmse = sum(m_rmses) / len(m_rmses)
        all_models.append((m, avg_mae, avg_rmse))

    out_comparison = []
    for name, mae, rmse in all_models:
        pct_impr = ((strongest_trivial_mae - mae) / strongest_trivial_mae) * 100.0 if mae <= strongest_trivial_mae else -((mae - strongest_trivial_mae) / strongest_trivial_mae) * 100.0
        beats_trivial = "YES" if mae < strongest_trivial_mae else "NO"
        out_comparison.append({
            "model_or_baseline": name,
            "mean_loco_mae_pct": f"{mae:.4f}",
            "mean_loco_rmse_pct": f"{rmse:.4f}",
            "strongest_trivial_mae_pct": f"{strongest_trivial_mae:.4f}",
            "pct_improvement_over_strongest_trivial": f"{pct_impr:.2f}%",
            "beats_strongest_trivial": beats_trivial
        })
        print(f"Model/Baseline: {name:<32} | MAE: {mae:.2f}% | Impr: {pct_impr:+.2f}% | Beats Trivial: {beats_trivial}")

    # Write regression_baseline_comparison.csv
    comp_csv = os.path.join(RESULTS_DIR, "regression_baseline_comparison.csv")
    with open(comp_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_comparison[0].keys()))
        writer.writeheader()
        writer.writerows(out_comparison)

    print(f"\nBaseline comparison written to {comp_csv}")

if __name__ == "__main__":
    run_trivial_baselines()
