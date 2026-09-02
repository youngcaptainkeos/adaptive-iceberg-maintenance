#!/usr/bin/env python3
import os
import sys
import csv
import math
import random

# Import policies
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from policy.always_run import AlwaysRunPolicy
from policy.always_defer import AlwaysDeferPolicy
from policy.heuristic_policy import HeuristicPolicy
from policy.predictive_qir_policy import PredictiveQIRPolicy
from policy.conservative_quantile_policy import ConservativeQuantilePolicy

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
PHASE3C_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3c-uncertainty-aware-scheduler")
RESULTS_DIR = os.path.join(PHASE3C_DIR, "results")

os.makedirs(RESULTS_DIR, exist_ok=True)

# Helper functions for models
def train_rf_and_q95_models(dataset):
    # Fit model predictors to generate out-of-fold predictions
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

    groups = [r["config_id"] for r in dataset]
    y_reg = [float(r["qir_pct"]) for r in dataset]

    X_raw = []
    for r in dataset:
        row_feat = [float(r[col]) for col in num_cols]
        row_feat.extend([1.0 if r["workload_type"] == w else 0.0 for w in workload_types])
        row_feat.extend([1.0 if r["scheduler_mode"] == s else 0.0 for s in scheduler_modes])
        row_feat.extend([1.0 if r["query"] == q else 0.0 for q in queries])
        X_raw.append(row_feat)

    n_samples = len(X_raw)
    n_feats = len(X_raw[0])
    means = [sum(X_raw[i][j] for i in range(n_samples)) / n_samples for j in range(n_feats)]
    stds = [math.sqrt(sum((X_raw[i][j] - means[j])**2 for i in range(n_samples)) / n_samples) for j in range(n_feats)]
    stds = [s if s > 1e-6 else 1.0 for s in stds]

    X_scaled = []
    for i in range(n_samples):
        scaled_row = [(X_raw[i][j] - means[j]) / stds[j] if j < len(num_cols) else X_raw[i][j] for j in range(n_feats)]
        scaled_row.append(1.0)
        X_scaled.append(scaled_row)

    # GroupKFold
    random.seed(42)
    shuffled_configs = config_ids[:]
    random.shuffle(shuffled_configs)
    
    n_folds = 4
    fold_size = len(shuffled_configs) // n_folds
    folds = [shuffled_configs[i*fold_size : (i+1)*fold_size] for i in range(n_folds)]

    rf_oof_preds = [0.0] * n_samples
    q95_oof_preds = [0.0] * n_samples

    # RF Tree Helper
    class SimpleTree:
        def fit(self, X, y, max_depth=3, min_samples_split=4, depth=0):
            n_s = len(X)
            if depth >= max_depth or n_s < min_samples_split:
                return sum(y) / n_s if n_s > 0 else 0.0
            best_gain, best_feat, best_val = -1.0, None, None
            curr_mse = sum((val - sum(y)/n_s)**2 for val in y)
            for feat in range(len(X[0])):
                vals = sorted(list(set(row[feat] for row in X)))
                for v in vals:
                    l_idx = [i for i, row in enumerate(X) if row[feat] <= v]
                    r_idx = [i for i, row in enumerate(X) if row[feat] > v]
                    if not l_idx or not r_idx:
                        continue
                    ly, ry = [y[i] for i in l_idx], [y[i] for i in r_idx]
                    l_mse = sum((val - sum(ly)/len(ly))**2 for val in ly)
                    r_mse = sum((val - sum(ry)/len(ry))**2 for val in ry)
                    gain = curr_mse - (l_mse + r_mse)
                    if gain > best_gain:
                        best_gain, best_feat, best_val = gain, feat, v
            if best_feat is None:
                return sum(y) / n_s
            l_idx = [i for i, row in enumerate(X) if row[best_feat] <= best_val]
            r_idx = [i for i, row in enumerate(X) if row[best_feat] > best_val]
            left = self.fit([X[i] for i in l_idx], [y[i] for i in l_idx], max_depth, min_samples_split, depth + 1)
            right = self.fit([X[i] for i in r_idx], [y[i] for i in r_idx], max_depth, min_samples_split, depth + 1)
            return (best_feat, best_val, left, right)

        def predict_one(self, node, row):
            if not isinstance(node, tuple):
                return node
            feat, val, left, right = node
            if row[feat] <= val:
                return self.predict_one(left, row)
            return self.predict_one(right, row)

    for fold_configs in folds:
        train_idx = [i for i, g in enumerate(groups) if g not in fold_configs]
        val_idx = [i for i, g in enumerate(groups) if g in fold_configs]

        X_train = [X_scaled[i] for i in train_idx]
        y_train = [y_reg[i] for i in train_idx]
        X_val = [X_scaled[i] for i in val_idx]

        # 1. RF Regressor
        trees = []
        n_tr = len(X_train)
        st = SimpleTree()
        for t_i in range(5):
            boot_idx = [random.randint(0, n_tr - 1) for _ in range(n_tr)]
            X_b = [X_train[bi] for bi in boot_idx]
            y_b = [y_train[bi] for bi in boot_idx]
            root = st.fit(X_b, y_b)
            trees.append(root)

        for vi in val_idx:
            row = X_scaled[vi]
            pred = sum(st.predict_one(root, row) for root in trees) / len(trees)
            rf_oof_preds[vi] = pred

        # 2. Q95 Quantile Regressor
        dim = len(X_train[0])
        weights = [0.0] * dim
        weights[-1] = 10.0
        lr = 0.01
        quantile = 0.95
        for epoch in range(300):
            for i in range(len(X_train)):
                pred = sum(w*x for w, x in zip(weights, X_train[i]))
                err = y_train[i] - pred
                subgrad = -quantile if err > 0 else (1.0 - quantile)
                for j in range(dim):
                    weights[j] -= lr * subgrad * X_train[i][j]

        for vi in val_idx:
            q95_oof_preds[vi] = sum(w*x for w, x in zip(weights, X_scaled[vi]))

    return rf_oof_preds, q95_oof_preds

def run_experiment():
    dataset_csv = os.path.join(PHASE3B_DIR, "results/dataset_predictive_signals.csv")
    if not os.path.exists(dataset_csv):
        print(f"Error: Dataset {dataset_csv} missing!")
        return

    dataset = []
    with open(dataset_csv, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            dataset.append(r)

    print(f"Loaded {len(dataset)} decision windows for Phase 3C policy evaluation.")

    rf_preds, q95_preds = train_rf_and_q95_models(dataset)

    # Initialize policy instances
    policies = [
        AlwaysRunPolicy(),
        AlwaysDeferPolicy(),
        HeuristicPolicy(cpu_threshold=50.0, iops_threshold=500.0),
        PredictiveQIRPolicy(qir_threshold=10.0),
        ConservativeQuantilePolicy(q95_threshold=10.0)
    ]

    all_decisions = []
    policy_metrics = {p.policy_id: [] for p in policies}

    for idx, r in enumerate(dataset):
        x_pred = {
            "frag_files": float(r["frag_files"]),
            "table_size_mb": float(r["table_size_mb"]),
            "avg_file_size_kb": float(r["avg_file_size_kb"]),
            "pre_cpu_util_pct": float(r["pre_cpu_util_pct"]),
            "pre_mem_used_pct": float(r["pre_mem_used_pct"]),
            "pre_disk_read_bytes_sec": float(r["pre_disk_read_bytes_sec"]),
            "pre_disk_write_bytes_sec": float(r["pre_disk_write_bytes_sec"]),
            "pre_disk_read_iops": float(r["pre_disk_read_iops"]),
            "pre_disk_write_iops": float(r["pre_disk_write_iops"]),
            "baseline_duration_ms": float(r["baseline_duration_ms"]),
            "workload_type": r["workload_type"],
            "scheduler_mode": r["scheduler_mode"],
            "query": r["query"]
        }

        actual_qir = float(r["qir_pct"])
        baseline_dur_sec = float(r["baseline_duration_ms"]) / 1000.0
        rf_pred_qir = rf_preds[idx]
        q95_pred_qir = q95_preds[idx]

        for p in policies:
            if p.policy_id == "policy_4_predictive_qir":
                decision = p.decide(x_pred, rf_pred_qir)
            elif p.policy_id == "policy_5_conservative_quantile":
                decision = p.decide(x_pred, q95_pred_qir)
            else:
                decision = p.decide(x_pred)

            if decision == "RUN":
                obs_qir = actual_qir
                maint_executed = 1
                maint_delay_sec = 0.0
                maint_starved = 0
                sla_violation = 1 if actual_qir > 10.0 else 0
            else: # DEFER
                obs_qir = 0.0
                maint_executed = 0
                maint_delay_sec = baseline_dur_sec
                maint_starved = 1
                sla_violation = 0

            dec_record = {
                "window_id": idx + 1,
                "config_id": r["config_id"],
                "repetition": r["repetition"],
                "query": r["query"],
                "policy_id": p.policy_id,
                "policy_name": p.name,
                "decision": decision,
                "rf_predicted_qir": rf_pred_qir,
                "q95_predicted_qir": q95_pred_qir,
                "actual_concurrent_qir": actual_qir,
                "observed_effective_qir": obs_qir,
                "maintenance_executed": maint_executed,
                "maintenance_delay_sec": maint_delay_sec,
                "maintenance_starved": maint_starved,
                "sla_violation": sla_violation
            }

            all_decisions.append(dec_record)
            policy_metrics[p.policy_id].append(dec_record)

    # Write policy_decisions.csv
    dec_csv = os.path.join(RESULTS_DIR, "policy_decisions.csv")
    fieldnames = list(all_decisions[0].keys())
    with open(dec_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_decisions)

    # Calculate summary metrics per policy
    summary_rows = []
    n_windows = len(dataset)

    print("\n=========================================")
    print("Phase 3C Policy Evaluation Performance Summary")
    print("=========================================")

    for p in policies:
        recs = policy_metrics[p.policy_id]
        runs = sum(1 for r in recs if r["decision"] == "RUN")
        defers = sum(1 for r in recs if r["decision"] == "DEFER")
        run_pct = (runs / n_windows) * 100.0
        defer_pct = (defers / n_windows) * 100.0

        qirs = [r["observed_effective_qir"] for r in recs]
        mean_qir = sum(qirs) / len(qirs)
        sorted_qirs = sorted(qirs)
        med_qir = sorted_qirs[len(sorted_qirs)//2]
        p95_idx = int(0.95 * len(sorted_qirs))
        p95_qir = sorted_qirs[min(p95_idx, len(sorted_qirs)-1)]
        max_qir = max(qirs)

        sla_violations = sum(r["sla_violation"] for r in recs)
        sla_rate = (sla_violations / n_windows) * 100.0
        maint_completion_rate = (runs / n_windows) * 100.0
        tot_delay = sum(r["maintenance_delay_sec"] for r in recs)
        avg_delay = tot_delay / n_windows
        starvation_events = sum(r["maintenance_starved"] for r in recs)

        s_row = {
            "policy_id": p.policy_id,
            "policy_name": p.name,
            "total_windows": n_windows,
            "run_decisions": runs,
            "defer_decisions": defers,
            "run_pct": f"{run_pct:.1f}%",
            "defer_pct": f"{defer_pct:.1f}%",
            "mean_qir_pct": f"{mean_qir:.2f}%",
            "median_qir_pct": f"{med_qir:.2f}%",
            "p95_qir_pct": f"{p95_qir:.2f}%",
            "max_qir_pct": f"{max_qir:.2f}%",
            "sla_violation_rate": f"{sla_rate:.1f}%",
            "maintenance_completion_rate": f"{maint_completion_rate:.1f}%",
            "avg_deferral_delay_sec": f"{avg_delay:.2f}s",
            "starvation_events": starvation_events
        }
        summary_rows.append(s_row)
        print(f"{p.name}: Mean QIR = {mean_qir:.2f}%, P95 = {p95_qir:.2f}%, SLA Violations = {sla_rate:.1f}%, Maintenance Completion = {maint_completion_rate:.1f}%")

    res_csv = os.path.join(RESULTS_DIR, "policy_experiment_results.csv")
    with open(res_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nPolicy decisions saved to: {dec_csv}")
    print(f"Policy experimental results saved to: {res_csv}")

if __name__ == "__main__":
    run_experiment()
