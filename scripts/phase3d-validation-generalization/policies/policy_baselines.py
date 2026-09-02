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

def run_policy_baselines():
    dataset_csv = os.path.join(PHASE3B_DIR, "results/dataset_predictive_signals.csv")
    preds_csv = os.path.join(RESULTS_DIR, "loco_fold_predictions.csv")
    calib_csv = os.path.join(RESULTS_DIR, "quantile_calibration_results.csv")

    if not os.path.exists(dataset_csv) or not os.path.exists(preds_csv):
        print("Error: Required dataset/predictions files missing!", file=sys.stderr)
        sys.exit(1)

    dataset = []
    with open(dataset_csv, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            dataset.append(r)

    loco_preds = []
    with open(preds_csv, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            loco_preds.append(r)

    calib_adj = {}
    if os.path.exists(calib_csv):
        with open(calib_csv, "r") as f:
            reader = csv.DictReader(f)
            for r in reader:
                calib_adj[r["held_out_config_id"]] = float(r["conformal_adjustment_q"])

    # Organize predictions by sample
    rf_preds_by_row = {}
    q95_preds_by_row = {}
    for r in loco_preds:
        cfg = r["held_out_config_id"]
        s_idx = int(r["sample_idx"])
        key = (cfg, s_idx)
        if r["model"] == "Random Forest Regressor":
            rf_preds_by_row[key] = float(r["predicted_qir"])
        elif r["model"] == "Quantile Regressor (q=0.95)":
            q95_preds_by_row[key] = float(r["predicted_qir"])

    # Define 7 Policies
    policies = [
        "Always Run (Baseline)",
        "Always Defer",
        "Random Policy (P=0.5, Seed=42)",
        "Explicit Simple Resource Heuristic",
        "Predictive Mean-QIR Policy (RF)",
        "Conservative Quantile Policy (Raw q=0.95)",
        "Conformal Upper-Bound Policy (Conformal q=0.95)"
    ]

    # Fixed seed for Random policy
    rng = random.Random(42)
    random_decisions = [rng.choice(["RUN", "DEFER"]) for _ in range(len(dataset))]

    policy_eval_results = []

    for pol in policies:
        allowed_count = 0
        deferred_count = 0
        observed_qirs = []
        sla_violations = 0
        consecutive_deferrals = 0
        max_consecutive_deferral = 0
        deferral_streaks = []
        curr_streak = 0
        starvation_events = 0 # streaks >= 3

        for i, row in enumerate(dataset):
            cfg = row["config_id"]
            # Find sample index within config
            cfg_rows = [r for r in dataset if r["config_id"] == cfg]
            s_idx = cfg_rows.index(row) + 1
            key = (cfg, s_idx)

            act_qir = float(row["qir_pct"])
            cpu_val = float(row["pre_cpu_util_pct"])
            disk_write = float(row["pre_disk_write_bytes_sec"])

            decision = "RUN"

            if pol == "Always Run (Baseline)":
                decision = "RUN"
            elif pol == "Always Defer":
                decision = "DEFER"
            elif pol == "Random Policy (P=0.5, Seed=42)":
                decision = random_decisions[i]
            elif pol == "Explicit Simple Resource Heuristic":
                # DEFER if CPU > 45% or Write Bytes/sec > 3.0e7
                if cpu_val > 45.0 or disk_write > 3.0e7:
                    decision = "DEFER"
                else:
                    decision = "RUN"
            elif pol == "Predictive Mean-QIR Policy (RF)":
                pred_rf = rf_preds_by_row.get(key, 0.0)
                if pred_rf > 10.0:
                    decision = "DEFER"
                else:
                    decision = "RUN"
            elif pol == "Conservative Quantile Policy (Raw q=0.95)":
                pred_q95 = q95_preds_by_row.get(key, 0.0)
                if pred_q95 > 10.0:
                    decision = "DEFER"
                else:
                    decision = "RUN"
            elif pol == "Conformal Upper-Bound Policy (Conformal q=0.95)":
                pred_q95 = q95_preds_by_row.get(key, 0.0)
                adj = calib_adj.get(cfg, 0.0)
                conf_pred = pred_q95 + adj
                if conf_pred > 10.0:
                    decision = "DEFER"
                else:
                    decision = "RUN"

            if decision == "RUN":
                allowed_count += 1
                observed_qirs.append(act_qir)
                if act_qir > 10.0:
                    sla_violations += 1
                if curr_streak > 0:
                    deferral_streaks.append(curr_streak)
                    if curr_streak >= 3:
                        starvation_events += 1
                    curr_streak = 0
            else:
                deferred_count += 1
                observed_qirs.append(0.0) # Zero interference when deferred
                curr_streak += 1
                if curr_streak > max_consecutive_deferral:
                    max_consecutive_deferral = curr_streak

        if curr_streak > 0:
            deferral_streaks.append(curr_streak)
            if curr_streak >= 3:
                starvation_events += 1

        total = len(dataset)
        run_pct = (allowed_count / total) * 100.0
        defer_pct = (deferred_count / total) * 100.0
        mean_qir = sum(observed_qirs) / total
        sorted_qirs = sorted(observed_qirs)
        med_qir = sorted_qirs[total // 2]
        p95_qir = sorted_qirs[int(total * 0.95)]
        sla_pct = (sla_violations / total) * 100.0
        mean_streak = sum(deferral_streaks) / len(deferral_streaks) if deferral_streaks else 0.0

        policy_eval_results.append({
            "policy_name": pol,
            "maintenance_allowed_pct": f"{run_pct:.1f}%",
            "maintenance_deferred_pct": f"{defer_pct:.1f}%",
            "mean_qir_pct": f"{mean_qir:.2f}%",
            "median_qir_pct": f"{med_qir:.2f}%",
            "p95_qir_pct": f"{p95_qir:.2f}%",
            "sla_violation_rate_pct": f"{sla_pct:.1f}%",
            "max_consecutive_deferrals": max_consecutive_deferral,
            "mean_deferral_streak": f"{mean_streak:.2f}",
            "starvation_events": starvation_events
        })

    # Print summary
    print("=========================================")
    print("Policy Evaluation Across 7 Scheduling Policies")
    print("=========================================")
    for p in policy_eval_results:
        print(f"Policy: {p['policy_name']:<48} | Run: {p['maintenance_allowed_pct']:<6} | QIR: {p['mean_qir_pct']:<6} | P95: {p['p95_qir_pct']:<6} | SLA Viol: {p['sla_violation_rate_pct']:<6} | Starv: {p['starvation_events']}")

    # Write policy_baselines_summary.csv
    pol_csv = os.path.join(RESULTS_DIR, "policy_baselines_summary.csv")
    with open(pol_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(policy_eval_results[0].keys()))
        writer.writeheader()
        writer.writerows(policy_eval_results)

    print(f"\nPolicy evaluation written to {pol_csv}")

if __name__ == "__main__":
    run_policy_baselines()
