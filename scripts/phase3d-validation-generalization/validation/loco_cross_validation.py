#!/usr/bin/env python3
"""
loco_cross_validation.py
------------------------
Phase 3D — Leave-One-Configuration-Out Cross Validation (LOCO-CV).

Evaluates 4 candidate regression models (Ridge, Lasso, Random Forest, Quantile q=0.95)
across all 12 experimental configurations in the Phase 3B dataset using strict LOCO-CV.

Anti-Leakage Guarantees:
- Held-out configuration (config_id) is completely excluded from training.
- Preprocessing (means, stds) is fit strictly on the 11 training configurations per fold.
"""

import os
import sys
import csv
import math
import random
from typing import Dict, Any, List

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
PHASE3D_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3d-validation-generalization")
RESULTS_DIR = os.path.join(PHASE3D_DIR, "results")

os.makedirs(RESULTS_DIR, exist_ok=True)
random.seed(42)

def transpose(matrix):
    return [list(i) for i in zip(*matrix)]

def matmul(A, B):
    return [[sum(a*b for a, b in zip(A_row, B_col)) for B_col in zip(*B)] for A_row in A]

def mat_vec_mul(A, v):
    return [sum(a*b for a, b in zip(A_row, v)) for A_row in A]

def invert_matrix(A):
    n = len(A)
    AM = [row[:] for row in A]
    I = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for i in range(n):
        pivot = AM[i][i]
        if abs(pivot) < 1e-12:
            pivot = 1e-6
        for j in range(n):
            AM[i][j] /= pivot
            I[i][j] /= pivot
        for k in range(n):
            if k != i:
                factor = AM[k][i]
                for j in range(n):
                    AM[k][j] -= factor * AM[i][j]
                    I[k][j] -= factor * I[i][j]
    return I

def mean_absolute_error(y_true, y_pred):
    return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true)

def root_mean_squared_error(y_true, y_pred):
    return math.sqrt(sum((t - p)**2 for t, p in zip(y_true, y_pred)) / len(y_true))

def r2_score(y_true, y_pred):
    mean_y = sum(y_true) / len(y_true)
    ss_tot = sum((y - mean_y)**2 for y in y_true)
    if ss_tot < 1e-6:
        return 0.0
    ss_res = sum((t - p)**2 for t, p in zip(y_true, y_pred))
    return max(-10.0, 1.0 - (ss_res / ss_tot))

class SimpleTreeRegressor:
    def __init__(self, max_depth=3, min_samples_split=4):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split

    def fit(self, X, y, depth=0):
        n_samples = len(X)
        if depth >= self.max_depth or n_samples < self.min_samples_split:
            return sum(y) / n_samples if n_samples > 0 else 0.0

        n_features = len(X[0])
        best_gain = -1.0
        best_feat, best_val = None, None
        curr_mse = sum((val - sum(y)/n_samples)**2 for val in y)

        for feat in range(n_features):
            vals = sorted(list(set(row[feat] for row in X)))
            for v in vals:
                l_idx = [i for i, row in enumerate(X) if row[feat] <= v]
                r_idx = [i for i, row in enumerate(X) if row[feat] > v]
                if not l_idx or not r_idx:
                    continue
                ly = [y[i] for i in l_idx]
                ry = [y[i] for i in r_idx]
                l_mse = sum((val - sum(ly)/len(ly))**2 for val in ly)
                r_mse = sum((val - sum(ry)/len(ry))**2 for val in ry)
                gain = curr_mse - (l_mse + r_mse)
                if gain > best_gain:
                    best_gain = gain
                    best_feat, best_val = feat, v

        if best_feat is None:
            return sum(y) / n_samples

        l_idx = [i for i, row in enumerate(X) if row[best_feat] <= best_val]
        r_idx = [i for i, row in enumerate(X) if row[best_feat] > best_val]

        left = self.fit([X[i] for i in l_idx], [y[i] for i in l_idx], depth + 1)
        right = self.fit([X[i] for i in r_idx], [y[i] for i in r_idx], depth + 1)
        return (best_feat, best_val, left, right)

    def predict_one(self, node, row):
        if not isinstance(node, tuple):
            return node
        feat, val, left, right = node
        if row[feat] <= val:
            return self.predict_one(left, row)
        return self.predict_one(right, row)

def run_loco_cv():
    dataset_csv = os.path.join(PHASE3B_DIR, "results/dataset_predictive_signals.csv")
    if not os.path.exists(dataset_csv):
        print(f"Error: Dataset {dataset_csv} missing!", file=sys.stderr)
        sys.exit(1)

    dataset = []
    with open(dataset_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            dataset.append(r)

    config_ids = sorted(list(set(r["config_id"] for r in dataset)))
    workload_types = sorted(list(set(r["workload_type"] for r in dataset)))
    scheduler_modes = sorted(list(set(r["scheduler_mode"] for r in dataset)))
    queries = sorted(list(set(r["query"] for r in dataset)))

    num_cols = [
        "frag_files", "table_size_mb", "avg_file_size_kb",
        "pre_cpu_util_pct", "pre_mem_used_pct",
        "pre_disk_read_bytes_sec", "pre_disk_write_bytes_sec",
        "pre_disk_read_iops", "pre_disk_write_iops",
        "baseline_duration_ms"
    ]

    print(f"Running LOCO-CV across {len(config_ids)} unique held-out configurations...")

    fold_results = []
    fold_predictions = []

    for held_out_cfg in config_ids:
        train_rows = [r for r in dataset if r["config_id"] != held_out_cfg]
        test_rows = [r for r in dataset if r["config_id"] == held_out_cfg]

        sample_test = test_rows[0]
        frag = sample_test["frag_files"]
        workload = sample_test["workload_type"]
        sched = sample_test["scheduler_mode"]

        def extract_features(row_list):
            X = []
            y = []
            for r in row_list:
                rf = [float(r[c]) for c in num_cols]
                rf.extend([1.0 if r["workload_type"] == w else 0.0 for w in workload_types])
                rf.extend([1.0 if r["scheduler_mode"] == s else 0.0 for s in scheduler_modes])
                rf.extend([1.0 if r["query"] == q else 0.0 for q in queries])
                X.append(rf)
                y.append(float(r["qir_pct"]))
            return X, y

        X_train_raw, y_train = extract_features(train_rows)
        X_test_raw, y_test = extract_features(test_rows)

        n_tr = len(X_train_raw)
        n_feats = len(X_train_raw[0])
        tr_means = [sum(X_train_raw[i][j] for i in range(n_tr)) / n_tr for j in range(n_feats)]
        tr_stds = [math.sqrt(sum((X_train_raw[i][j] - tr_means[j])**2 for i in range(n_tr)) / n_tr) for j in range(n_feats)]
        tr_stds = [s if s > 1e-6 else 1.0 for s in tr_stds]

        X_train = []
        for row in X_train_raw:
            s_row = [(row[j] - tr_means[j]) / tr_stds[j] if j < len(num_cols) else row[j] for j in range(n_feats)]
            s_row.append(1.0)
            X_train.append(s_row)

        X_test = []
        for row in X_test_raw:
            s_row = [(row[j] - tr_means[j]) / tr_stds[j] if j < len(num_cols) else row[j] for j in range(n_feats)]
            s_row.append(1.0)
            X_test.append(s_row)

        # 1. Ridge Regression
        Xt = transpose(X_train)
        XtX = matmul(Xt, X_train)
        for d in range(len(XtX)):
            XtX[d][d] += 1.0
        inv_XtX = invert_matrix(XtX)
        Xty = mat_vec_mul(Xt, y_train)
        ridge_w = mat_vec_mul(inv_XtX, Xty)
        ridge_preds = [sum(w*x for w, x in zip(ridge_w, row)) for row in X_test]

        # 2. Lasso Regression
        dim = len(X_train[0])
        lasso_w = [0.0] * dim
        l1_alpha = 0.5
        for epoch in range(100):
            for j in range(dim):
                r = [y_train[i] - sum(lasso_w[k]*X_train[i][k] for k in range(dim) if k != j) for i in range(len(X_train))]
                rho = sum(X_train[i][j] * r[i] for i in range(len(X_train)))
                z = sum(X_train[i][j]**2 for i in range(len(X_train)))
                if z < 1e-6:
                    continue
                if rho > l1_alpha:
                    lasso_w[j] = (rho - l1_alpha) / z
                elif rho < -l1_alpha:
                    lasso_w[j] = (rho + l1_alpha) / z
                else:
                    lasso_w[j] = 0.0
        lasso_preds = [sum(w*x for w, x in zip(lasso_w, row)) for row in X_test]

        # 3. Random Forest Regressor
        trees = []
        st = SimpleTreeRegressor(max_depth=3, min_samples_split=4)
        for t_i in range(5):
            boot_idx = [random.randint(0, n_tr - 1) for _ in range(n_tr)]
            X_b = [X_train[bi] for bi in boot_idx]
            y_b = [y_train[bi] for bi in boot_idx]
            root = st.fit(X_b, y_b)
            trees.append(root)

        rf_preds = [sum(st.predict_one(root, row) for root in trees) / len(trees) for row in X_test]

        # 4. Quantile Regressor (q=0.95)
        dim = len(X_train[0])
        q95_w = [0.0] * dim
        q95_w[-1] = 10.0
        lr = 0.01
        quantile = 0.95
        for epoch in range(300):
            for i in range(len(X_train)):
                pred = sum(w*x for w, x in zip(q95_w, X_train[i]))
                err = y_train[i] - pred
                subgrad = -quantile if err > 0 else (1.0 - quantile)
                for j in range(dim):
                    q95_w[j] -= lr * subgrad * X_train[i][j]

        q95_preds = [sum(w*x for w, x in zip(q95_w, row)) for row in X_test]

        models_eval = [
            ("Ridge Regression", ridge_preds),
            ("Lasso Regression", lasso_preds),
            ("Random Forest Regressor", rf_preds),
            ("Quantile Regressor (q=0.95)", q95_preds)
        ]

        mean_act_qir = sum(y_test) / len(y_test)

        for m_name, preds in models_eval:
            mae = mean_absolute_error(y_test, preds)
            rmse = root_mean_squared_error(y_test, preds)
            r2 = r2_score(y_test, preds)
            mean_pred_qir = sum(preds) / len(preds)
            mean_err = sum(t - p for t, p in zip(y_test, preds)) / len(y_test)
            worst_abs_err = max(abs(t - p) for t, p in zip(y_test, preds))

            fold_results.append({
                "held_out_config_id": held_out_cfg,
                "fragmentation_level": frag,
                "workload_type": workload,
                "scheduler_mode": sched,
                "model": m_name,
                "train_sample_count": n_tr,
                "test_sample_count": len(y_test),
                "mean_actual_qir": f"{mean_act_qir:.4f}",
                "mean_predicted_qir": f"{mean_pred_qir:.4f}",
                "mae": f"{mae:.4f}",
                "rmse": f"{rmse:.4f}",
                "r2": f"{r2:.4f}",
                "mean_prediction_error": f"{mean_err:.4f}",
                "worst_abs_prediction_error": f"{worst_abs_err:.4f}"
            })

            for idx_sample, (t, p) in enumerate(zip(y_test, preds)):
                fold_predictions.append({
                    "held_out_config_id": held_out_cfg,
                    "sample_idx": idx_sample + 1,
                    "repetition": test_rows[idx_sample]["repetition"],
                    "query": test_rows[idx_sample]["query"],
                    "model": m_name,
                    "actual_qir": f"{t:.4f}",
                    "predicted_qir": f"{p:.4f}",
                    "error": f"{(t - p):.4f}",
                    "abs_error": f"{abs(t - p):.4f}"
                })

    # Write loco_regression_results.csv
    loco_csv = os.path.join(RESULTS_DIR, "loco_regression_results.csv")
    with open(loco_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fold_results[0].keys()))
        writer.writeheader()
        writer.writerows(fold_results)

    # Write loco_fold_predictions.csv
    preds_csv = os.path.join(RESULTS_DIR, "loco_fold_predictions.csv")
    with open(preds_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fold_predictions[0].keys()))
        writer.writeheader()
        writer.writerows(fold_predictions)

    # Summary Statistics Across Folds per Model -> loco_regression_summary.csv
    models = sorted(list(set(r["model"] for r in fold_results)))
    summary_rows = []

    print("\n=========================================")
    print("LOCO-CV Evaluation Summary Across 12 Held-Out Folds")
    print("=========================================")

    for m in models:
        m_folds = [r for r in fold_results if r["model"] == m]
        maes = [float(r["mae"]) for r in m_folds]
        rmses = [float(r["rmse"]) for r in m_folds]
        r2s = [float(r["r2"]) for r in m_folds]

        mean_mae = sum(maes) / len(maes)
        sorted_maes = sorted(maes)
        med_mae = sorted_maes[len(sorted_maes)//2]
        std_mae = math.sqrt(sum((x - mean_mae)**2 for x in maes) / len(maes))
        best_mae = sorted_maes[0]
        worst_mae = sorted_maes[-1]

        mean_rmse = sum(rmses) / len(rmses)
        sorted_rmses = sorted(rmses)
        med_rmse = sorted_rmses[len(sorted_rmses)//2]
        std_rmse = math.sqrt(sum((x - mean_rmse)**2 for x in rmses) / len(rmses))
        worst_rmse = sorted_rmses[-1]

        mean_r2 = sum(r2s) / len(r2s)
        sorted_r2s = sorted(r2s)
        med_r2 = sorted_r2s[len(sorted_r2s)//2]

        summary_rows.append({
            "model": m,
            "mean_MAE": f"{mean_mae:.4f}",
            "median_MAE": f"{med_mae:.4f}",
            "std_MAE": f"{std_mae:.4f}",
            "worst_case_MAE": f"{worst_mae:.4f}",
            "best_case_MAE": f"{best_mae:.4f}",
            "mean_RMSE": f"{mean_rmse:.4f}",
            "median_RMSE": f"{med_rmse:.4f}",
            "std_RMSE": f"{std_rmse:.4f}",
            "worst_case_RMSE": f"{worst_rmse:.4f}",
            "mean_R2": f"{mean_r2:.4f}",
            "median_R2": f"{med_r2:.4f}"
        })

        best_fold = min(m_folds, key=lambda x: float(x["mae"]))
        worst_fold = max(m_folds, key=lambda x: float(x["mae"]))

        print(f"\nModel: {m}")
        print(f"  Mean MAE: {mean_mae:.2f}%, Median MAE: {med_mae:.2f}%, Std MAE: {std_mae:.2f}%")
        print(f"  Best Config:  {best_fold['held_out_config_id']} (MAE={best_fold['mae']}%)")
        print(f"  Worst Config: {worst_fold['held_out_config_id']} (MAE={worst_fold['mae']}%, Worst Single Err={worst_fold['worst_abs_prediction_error']}%)")

    # Write loco_regression_summary.csv
    summary_csv = os.path.join(RESULTS_DIR, "loco_regression_summary.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nLOCO-CV results written to {loco_csv}")
    print(f"LOCO summary statistics written to {summary_csv}")

if __name__ == "__main__":
    run_loco_cv()
