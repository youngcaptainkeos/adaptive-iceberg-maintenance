#!/usr/bin/env python3
"""
conformal_policy_interface.py
-----------------------------
Clean policy handoff interface for Phase 3D uncertainty-aware scheduling.
Exposes callable functions to predict the calibrated 95% conformal upper bound on QIR
and make deterministic maintenance scheduling decisions.

Note: This policy does NOT rely on the binary SLA classifier (documented negative result).
The uncertainty mechanism is strictly derived from the calibrated split-conformal
one-sided upper prediction bound around the Random Forest regressor.
The 10.0% threshold represents an operational SLA threshold.
"""

import os
import sys
import csv
import math
import random
from typing import Dict, Any, Tuple

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
PHASE3D_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3d-validation-generalization")

# Global cached model and calibration parameters
_CACHED_MODEL = None
_CACHED_SCALER = None
_CACHED_CONFORMAL_OFFSET = None

NUM_COLS = [
    "frag_files", "table_size_mb", "avg_file_size_kb",
    "pre_cpu_util_pct", "pre_mem_used_pct",
    "pre_disk_read_bytes_sec", "pre_disk_write_bytes_sec",
    "pre_disk_read_iops", "pre_disk_write_iops",
    "baseline_duration_ms"
]

WORKLOAD_TYPES = ["multi_stream", "single_stream"]
SCHEDULER_MODES = ["FAIR", "FIFO"]
QUERIES = ["Q1", "Q12", "Q14", "Q18", "Q3", "Q6"]

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

def _load_and_train_conformal_model():
    global _CACHED_MODEL, _CACHED_SCALER, _CACHED_CONFORMAL_OFFSET
    if _CACHED_MODEL is not None:
        return

    dataset_csv = os.path.join(PHASE3B_DIR, "results/dataset_predictive_signals.csv")
    dataset = []
    with open(dataset_csv, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            dataset.append(r)

    # Perform a 80-20 configuration-aware train-calibration split
    configs = sorted(list(set(r["config_id"] for r in dataset)))
    random.seed(42)
    shuffled_cfgs = configs[:]
    random.shuffle(shuffled_cfgs)

    n_cal = 3
    calib_cfgs = set(shuffled_cfgs[:n_cal])
    train_cfgs = set(shuffled_cfgs[n_cal:])

    train_rows = [r for r in dataset if r["config_id"] in train_cfgs]
    calib_rows = [r for r in dataset if r["config_id"] in calib_cfgs]

    def build_vector(r):
        vec = [float(r[c]) for c in NUM_COLS]
        vec.extend([1.0 if r["workload_type"] == w else 0.0 for w in WORKLOAD_TYPES])
        vec.extend([1.0 if r["scheduler_mode"] == s else 0.0 for s in SCHEDULER_MODES])
        vec.extend([1.0 if r["query"] == q else 0.0 for q in QUERIES])
        return vec

    X_tr_raw = [build_vector(r) for r in train_rows]
    y_tr = [float(r["qir_pct"]) for r in train_rows]

    X_cal_raw = [build_vector(r) for r in calib_rows]
    y_cal = [float(r["qir_pct"]) for r in calib_rows]

    n_tr = len(X_tr_raw)
    n_feats = len(X_tr_raw[0])
    means = [sum(X_tr_raw[i][j] for i in range(n_tr)) / n_tr for j in range(n_feats)]
    stds = [math.sqrt(sum((X_tr_raw[i][j] - means[j])**2 for i in range(n_tr)) / n_tr) for j in range(n_feats)]
    stds = [s if s > 1e-6 else 1.0 for s in stds]

    _CACHED_SCALER = (means, stds)

    def scale_row(row):
        s = [(row[j] - means[j]) / stds[j] if j < len(NUM_COLS) else row[j] for j in range(n_feats)]
        s.append(1.0)
        return s

    X_tr = [scale_row(row) for row in X_tr_raw]
    X_cal = [scale_row(row) for row in X_cal_raw]

    # Fit Random Forest
    random.seed(42)
    trees = []
    st = SimpleTreeRegressor(max_depth=3, min_samples_split=4)
    for _ in range(5):
        boot_idx = [random.randint(0, n_tr - 1) for _ in range(n_tr)]
        X_b = [X_tr[bi] for bi in boot_idx]
        y_b = [y_tr[bi] for bi in boot_idx]
        root = st.fit(X_b, y_b)
        trees.append((st, root))

    _CACHED_MODEL = trees

    # Calculate nonconformity scores on calibration set
    cal_preds = [sum(st.predict_one(root, row) for st, root in trees) / len(trees) for row in X_cal]
    scores = sorted([actual_y - pred_y for actual_y, pred_y in zip(y_cal, cal_preds)])
    n_cal_samples = len(scores)
    k = math.ceil((n_cal_samples + 1) * 0.95)
    k_idx = min(n_cal_samples - 1, max(0, k - 1))
    _CACHED_CONFORMAL_OFFSET = scores[k_idx]

def _vectorize_feature_dict(features: Dict[str, Any]) -> list:
    row = [float(features[c]) for c in NUM_COLS]
    wt = str(features.get("workload_type", "single_stream"))
    sm = str(features.get("scheduler_mode", "FIFO"))
    q = str(features.get("query", "Q14"))

    row.extend([1.0 if wt == w else 0.0 for w in WORKLOAD_TYPES])
    row.extend([1.0 if sm == s else 0.0 for s in SCHEDULER_MODES])
    row.extend([1.0 if q == q_i else 0.0 for q_i in QUERIES])
    return row

def predict_qir_upper_bound(features: Dict[str, Any]) -> Tuple[float, float]:
    """
    Computes point prediction and 95% split-conformal upper prediction bound for expected QIR.

    Parameters:
        features: Dictionary containing prediction-time features (NUM_COLS + workload_type, scheduler_mode, query)

    Returns:
        Tuple[float, float]: (point_prediction_qir, conformal_upper_bound_qir)
    """
    _load_and_train_conformal_model()

    raw_vec = _vectorize_feature_dict(features)
    means, stds = _CACHED_SCALER
    n_num = len(NUM_COLS)
    n_feats = len(raw_vec)

    scaled_vec = [(raw_vec[j] - means[j]) / stds[j] if j < n_num else raw_vec[j] for j in range(n_feats)]
    scaled_vec.append(1.0)

    trees = _CACHED_MODEL
    point_pred = sum(st.predict_one(root, scaled_vec) for st, root in trees) / len(trees)
    conformal_ub = point_pred + _CACHED_CONFORMAL_OFFSET
    return point_pred, conformal_ub

def should_allow_maintenance(features: Dict[str, Any], sla_threshold: float = 10.0) -> bool:
    """
    Deterministic maintenance scheduling decision helper.

    Policy Rule:
        IF conformal_upper_bound > sla_threshold:
            DEFER maintenance (returns False)
        ELSE:
            ALLOW maintenance (returns True)

    Parameters:
        features: Pre-decision features dictionary
        sla_threshold: Operational SLA maximum allowable QIR percentage (default: 10.0%)

    Returns:
        bool: True to ALLOW maintenance, False to DEFER maintenance.
    """
    _, conformal_ub = predict_qir_upper_bound(features)
    if conformal_ub > sla_threshold:
        return False
    return True

if __name__ == "__main__":
    sample_feature = {
        "frag_files": 200.0,
        "table_size_mb": 145.0,
        "avg_file_size_kb": 842.0,
        "pre_cpu_util_pct": 35.0,
        "pre_mem_used_pct": 75.0,
        "pre_disk_read_bytes_sec": 1000000.0,
        "pre_disk_write_bytes_sec": 15000000.0,
        "pre_disk_read_iops": 50.0,
        "pre_disk_write_iops": 200.0,
        "baseline_duration_ms": 2000.0,
        "workload_type": "single_stream",
        "scheduler_mode": "FIFO",
        "query": "Q14"
    }

    pt, cub = predict_qir_upper_bound(sample_feature)
    allowed = should_allow_maintenance(sample_feature, sla_threshold=10.0)

    print("=========================================")
    print("Conformal Policy Interface Verification")
    print("=========================================")
    print(f"Sample Query: {sample_feature['query']} under {sample_feature['scheduler_mode']} with {sample_feature['frag_files']} files")
    print(f"Predicted QIR Point Estimate: {pt:.2f}%")
    print(f"95% Conformal Upper Bound QIR: {cub:.2f}%")
    print(f"Operational SLA Threshold: 10.0%")
    print(f"Decision: {'ALLOW Maintenance' if allowed else 'DEFER Maintenance'}")
