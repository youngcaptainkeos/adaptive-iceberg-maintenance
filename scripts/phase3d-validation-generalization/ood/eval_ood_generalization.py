#!/usr/bin/env python3
import os
import sys
import csv
import math
import random

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

def evaluate_ood():
    # 1. Load Phase 3B in-domain training set
    in_domain_csv = os.path.join(PHASE3B_DIR, "results/dataset_predictive_signals.csv")
    if not os.path.exists(in_domain_csv):
        print(f"Error: {in_domain_csv} not found.")
        sys.exit(1)

    train_rows = []
    with open(in_domain_csv, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            train_rows.append(r)

    # 2. Load Phase 3D OOD test set
    ood_data_path = os.path.join(RESULTS_DIR, "ood_experiment_results.csv")
    if not os.path.exists(ood_data_path):
        print(f"Error: {ood_data_path} not found.")
        sys.exit(1)

    test_rows = []
    with open(ood_data_path, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get('is_warmup', '').lower() == 'true':
                continue
            test_rows.append(r)

    print(f"Loaded {len(train_rows)} in-domain training samples.")
    print(f"Loaded {len(test_rows)} out-of-domain test samples.")

    # Features
    num_cols = [
        "frag_files", "table_size_mb", "avg_file_size_kb",
        "pre_cpu_util_pct", "pre_mem_used_pct",
        "pre_disk_read_bytes_sec", "pre_disk_write_bytes_sec",
        "pre_disk_read_iops", "pre_disk_write_iops",
        "baseline_duration_ms"
    ]

    workload_types = sorted(list(set(r["workload_type"] for r in train_rows)))
    scheduler_modes = sorted(list(set(r["scheduler_mode"] for r in train_rows)))
    queries = sorted(list(set(r["query"] for r in train_rows)))

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

    X_tr_raw, y_tr = extract_features(train_rows)
    X_te_raw, y_te = extract_features(test_rows)

    # Standardize using training stats
    n_tr = len(X_tr_raw)
    n_feats = len(X_tr_raw[0])
    tr_means = [sum(X_tr_raw[i][j] for i in range(n_tr)) / n_tr for j in range(n_feats)]
    tr_stds = [math.sqrt(sum((X_tr_raw[i][j] - tr_means[j])**2 for i in range(n_tr)) / n_tr) for j in range(n_feats)]
    tr_stds = [s if s > 1e-6 else 1.0 for s in tr_stds]

    X_tr = []
    for row in X_tr_raw:
        s_row = [(row[j] - tr_means[j]) / tr_stds[j] if j < len(num_cols) else row[j] for j in range(n_feats)]
        s_row.append(1.0)
        X_tr.append(s_row)

    X_te = []
    for row in X_te_raw:
        s_row = [(row[j] - tr_means[j]) / tr_stds[j] if j < len(num_cols) else row[j] for j in range(n_feats)]
        s_row.append(1.0)
        X_te.append(s_row)

    # 1. Ridge Regression
    Xt = transpose(X_tr)
    XtX = matmul(Xt, X_tr)
    for d in range(len(XtX)):
        XtX[d][d] += 1.0
    inv_XtX = invert_matrix(XtX)
    Xty = mat_vec_mul(Xt, y_tr)
    ridge_w = mat_vec_mul(inv_XtX, Xty)
    ridge_preds = [sum(w*x for w, x in zip(ridge_w, row)) for row in X_te]

    # 2. Lasso Regression
    dim = len(X_tr[0])
    lasso_w = [0.0] * dim
    l1_alpha = 0.5
    for epoch in range(100):
        for j in range(dim):
            r = [y_tr[i] - sum(lasso_w[k]*X_tr[i][k] for k in range(dim) if k != j) for i in range(len(X_tr))]
            rho = sum(X_tr[i][j] * r[i] for i in range(len(X_tr)))
            z = sum(X_tr[i][j]**2 for i in range(len(X_tr)))
            if z < 1e-6:
                continue
            if rho > l1_alpha:
                lasso_w[j] = (rho - l1_alpha) / z
            elif rho < -l1_alpha:
                lasso_w[j] = (rho + l1_alpha) / z
            else:
                lasso_w[j] = 0.0
    lasso_preds = [sum(w*x for w, x in zip(lasso_w, row)) for row in X_te]

    # 3. Random Forest
    trees = []
    st = SimpleTreeRegressor(max_depth=3, min_samples_split=4)
    for t_i in range(5):
        boot_idx = [random.randint(0, n_tr - 1) for _ in range(n_tr)]
        X_b = [X_tr[bi] for bi in boot_idx]
        y_b = [y_tr[bi] for bi in boot_idx]
        root = st.fit(X_b, y_b)
        trees.append(root)
    rf_preds = [sum(st.predict_one(root, row) for root in trees) / len(trees) for row in X_te]

    # 4. Quantile Regression (q=0.95)
    dim = len(X_tr[0])
    q95_w = [0.0] * dim
    q95_w[-1] = 10.0
    lr = 0.01
    quantile = 0.95
    for epoch in range(300):
        for i in range(len(X_tr)):
            pred = sum(w*x for w, x in zip(q95_w, X_tr[i]))
            err = y_tr[i] - pred
            subgrad = -quantile if err > 0 else (1.0 - quantile)
            for j in range(dim):
                q95_w[j] -= lr * subgrad * X_tr[i][j]
    q95_preds = [sum(w*x for w, x in zip(q95_w, row)) for row in X_te]

    models_eval = [
        ("Ridge Regression", ridge_preds),
        ("Lasso Regression", lasso_preds),
        ("Random Forest Regressor", rf_preds),
        ("Quantile Regressor (q=0.95)", q95_preds)
    ]

    metrics_rows = []
    n = len(y_te)
    y_mean = sum(y_te) / n
    ss_tot = sum((a - y_mean)**2 for a in y_te)

    for m_name, preds in models_eval:
        mae = sum(abs(p - a) for p, a in zip(preds, y_te)) / n
        rmse = math.sqrt(sum((p - a)**2 for p, a in zip(preds, y_te)) / n)
        ss_res = sum((a - p)**2 for p, a in zip(preds, y_te))
        r2 = max(-10.0, 1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        metrics_rows.append({
            'model': m_name,
            'mae': f"{mae:.4f}",
            'rmse': f"{rmse:.4f}",
            'r2': f"{r2:.4f}",
            'n_test_samples': n
        })

    ood_metrics_csv = os.path.join(RESULTS_DIR, "ood_metrics.csv")
    with open(ood_metrics_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['model', 'mae', 'rmse', 'r2', 'n_test_samples'])
        writer.writeheader()
        writer.writerows(metrics_rows)

    print("\n=========================================")
    print("Zero-Shot Out-of-Domain (OOD) Evaluation (100 & 350 File Fragmentation)")
    print("=========================================")
    for row in metrics_rows:
        print(f"Model: {row['model']:<30} | MAE: {row['mae']:>7}% | RMSE: {row['rmse']:>7}% | R2: {row['r2']:>7} | N: {row['n_test_samples']}")

    # Check q=0.95 quantile coverage on OOD
    q95_coverage = sum(1 for p, a in zip(q95_preds, y_te) if a <= p) / n
    print(f"\nEmpirical Coverage of Quantile Regressor (q=0.95) on OOD Data: {q95_coverage*100:.2f}% (Target: 95.0%)")
    print(f"OOD metrics saved to {ood_metrics_csv}")

if __name__ == '__main__':
    evaluate_ood()
