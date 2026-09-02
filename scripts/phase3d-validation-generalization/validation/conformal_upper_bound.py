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

def train_rf_ensemble(X_tr, y_tr, n_trees=5, max_depth=3, min_samples_split=4, seed=42):
    random.seed(seed)
    n_tr = len(X_tr)
    st = SimpleTreeRegressor(max_depth=max_depth, min_samples_split=min_samples_split)
    trees = []
    for _ in range(n_trees):
        boot_idx = [random.randint(0, n_tr - 1) for _ in range(n_tr)]
        X_b = [X_tr[bi] for bi in boot_idx]
        y_b = [y_tr[bi] for bi in boot_idx]
        root = st.fit(X_b, y_b)
        trees.append((st, root))
    return trees

def predict_rf_ensemble(trees, X):
    preds = []
    for row in X:
        val = sum(st.predict_one(root, row) for st, root in trees) / len(trees)
        preds.append(val)
    return preds

def run_conformal_upper_bound():
    dataset_csv = os.path.join(PHASE3B_DIR, "results/dataset_predictive_signals.csv")
    if not os.path.exists(dataset_csv):
        print(f"Error: {dataset_csv} missing!", file=sys.stderr)
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

    conformal_predictions = []
    config_results = []
    alpha = 0.05 # 95% target coverage (1 - alpha)

    print(f"Running Split-Conformal Upper Bound LOCO-CV across {len(config_ids)} configurations...")

    for fold_idx, held_out_cfg in enumerate(config_ids, start=1):
        # Outer evaluation: held_out_cfg is test set
        test_rows = [r for r in dataset if r["config_id"] == held_out_cfg]
        remaining_rows = [r for r in dataset if r["config_id"] != held_out_cfg]

        # Inner split: configuration-aware split among remaining 11 configs
        remaining_configs = sorted(list(set(r["config_id"] for r in remaining_rows)))
        
        # Select 3 configs deterministically for calibration, 8 for model training
        # To avoid bias, use fold index to rotate calibration configs:
        calib_cfg_indices = [(fold_idx - 1 + k) % len(remaining_configs) for k in range(3)]
        calib_configs = [remaining_configs[idx] for idx in calib_cfg_indices]
        train_configs = [cfg for cfg in remaining_configs if cfg not in calib_configs]

        train_rows = [r for r in remaining_rows if r["config_id"] in train_configs]
        calib_rows = [r for r in remaining_rows if r["config_id"] in calib_configs]

        X_tr_raw, y_tr = extract_features(train_rows)
        X_cal_raw, y_cal = extract_features(calib_rows)
        X_te_raw, y_te = extract_features(test_rows)

        # Standardize strictly using model-training data statistics
        n_tr = len(X_tr_raw)
        n_feats = len(X_tr_raw[0])
        tr_means = [sum(X_tr_raw[i][j] for i in range(n_tr)) / n_tr for j in range(n_feats)]
        tr_stds = [math.sqrt(sum((X_tr_raw[i][j] - tr_means[j])**2 for i in range(n_tr)) / n_tr) for j in range(n_feats)]
        tr_stds = [s if s > 1e-6 else 1.0 for s in tr_stds]

        def scale_X(X_raw):
            X_scaled = []
            for row in X_raw:
                s_row = [(row[j] - tr_means[j]) / tr_stds[j] if j < len(num_cols) else row[j] for j in range(n_feats)]
                s_row.append(1.0)
                X_scaled.append(s_row)
            return X_scaled

        X_tr = scale_X(X_tr_raw)
        X_cal = scale_X(X_cal_raw)
        X_te = scale_X(X_te_raw)

        # Fit Random Forest Regressor base model on training split
        rf_trees = train_rf_ensemble(X_tr, y_tr, n_trees=5, max_depth=3, min_samples_split=4, seed=42 + fold_idx)

        # Calculate nonconformity scores on calibration split
        # One-sided upper bound score: score_i = actual_y_i - pred_y_i
        cal_preds = predict_rf_ensemble(rf_trees, X_cal)
        scores = [actual_y - pred_y for actual_y, pred_y in zip(y_cal, cal_preds)]
        scores_sorted = sorted(scores)

        n_cal = len(scores)
        # Finite-sample conformal quantile formula for nominal 1 - alpha = 0.95:
        # index = ceil((n_cal + 1) * (1 - alpha))
        # 1-indexed rank k = min(n_cal, max(1, math.ceil((n_cal + 1) * 0.95)))
        k = math.ceil((n_cal + 1) * (1.0 - alpha))
        k_idx = min(n_cal - 1, max(0, k - 1))
        conformal_offset = scores_sorted[k_idx]

        # Predict held-out test configuration
        test_point_preds = predict_rf_ensemble(rf_trees, X_te)

        fold_covered_count = 0
        for test_row, actual_y, point_p in zip(test_rows, y_te, test_point_preds):
            conformal_ub = point_p + conformal_offset
            is_covered = (actual_y <= conformal_ub)
            if is_covered:
                fold_covered_count += 1

            conformal_predictions.append({
                "config_id": held_out_cfg,
                "fold": fold_idx,
                "repetition": test_row["repetition"],
                "query": test_row["query"],
                "actual_qir": f"{actual_y:.4f}",
                "point_prediction": f"{point_p:.4f}",
                "conformal_offset": f"{conformal_offset:.4f}",
                "conformal_upper_bound": f"{conformal_ub:.4f}",
                "covered_conformal": "TRUE" if is_covered else "FALSE"
            })

        n_test = len(test_rows)
        fold_cov_pct = (fold_covered_count / n_test) * 100.0
        config_results.append({
            "config_id": held_out_cfg,
            "fold": fold_idx,
            "sample_count": n_test,
            "covered_count": fold_covered_count,
            "undercovered_count": n_test - fold_covered_count,
            "conformal_coverage_pct": f"{fold_cov_pct:.2f}",
            "conformal_offset": f"{conformal_offset:.4f}",
            "mean_point_pred": f"{sum(test_point_preds)/n_test:.4f}",
            "mean_conformal_ub": f"{sum(test_point_preds)/n_test + conformal_offset:.4f}",
            "target_coverage_pct": "95.00"
        })

    # Write results/conformal_predictions.csv
    conf_preds_path = os.path.join(RESULTS_DIR, "conformal_predictions.csv")
    with open(conf_preds_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(conformal_predictions[0].keys()))
        writer.writeheader()
        writer.writerows(conformal_predictions)

    # Write results/conformal_calibration_results.csv
    conf_results_path = os.path.join(RESULTS_DIR, "conformal_calibration_results.csv")
    with open(conf_results_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(config_results[0].keys()))
        writer.writeheader()
        writer.writerows(config_results)

    total_obs = len(conformal_predictions)
    total_covered = sum(1 for r in conformal_predictions if r["covered_conformal"] == "TRUE")
    total_undercovered = total_obs - total_covered
    overall_cov_pct = (total_covered / total_obs) * 100.0

    print(f"\n=========================================")
    print(f"Split-Conformal Upper Bound Calibration Summary")
    print(f"=========================================")
    print(f"Total Observations: {total_obs}")
    print(f"Covered Observations (actual <= conformal_ub): {total_covered} ({overall_cov_pct:.2f}%)")
    print(f"Undercovered Observations (actual > conformal_ub): {total_undercovered} ({100.0 - overall_cov_pct:.2f}%)")
    print(f"Nominal Target Coverage: 95.00%")
    print(f"Saved conformal predictions to: {conf_preds_path}")
    print(f"Saved conformal results to: {conf_results_path}")

if __name__ == "__main__":
    run_conformal_upper_bound()
