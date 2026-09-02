#!/usr/bin/env python3
"""
starvation_protection.py
------------------------
Phase 3E Part 4 — Bounded Starvation Protection Analysis.

Evaluates the impact of introducing MAX_DEFERRALS in {1, 2, 3, 5} on maintenance completion rates,
SLA violation rates, and maximum consecutive deferral streaks.

Output:
- results/starvation_protection_results.csv
"""

import os
import sys
import csv
import math
from typing import Dict, Any, List

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
PHASE3D_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3d-validation-generalization")
PHASE3E_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3e-adaptive-scheduler")

RESULTS_DIR = os.path.join(PHASE3E_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

sys.path.insert(0, PHASE3E_DIR)
from policies.adaptive_policies import make_policy_decision
from policies.threshold_sweep import load_in_distribution_dataset, load_ood_dataset

def run_starvation_protection_evaluation():
    print("================================================================")
    print("Phase 3E — Part 4: Bounded Starvation Protection Evaluation")
    print("================================================================")

    ind_dataset = load_in_distribution_dataset()
    ood_dataset = load_ood_dataset()

    max_deferral_bounds = [0, 1, 2, 3, 5] # 0 = no override
    sla_threshold = 10.0

    policies = [
        "Policy B: Always Defer",
        "Policy C: Resource Heuristic",
        "Policy D: Point Prediction Policy",
        "Policy E: Raw Quantile Policy",
        "Policy F: Adaptive Conformal Risk Policy" # alpha = 0.05
    ]

    results = []

    for scope_name, dataset in [("In-Distribution", ind_dataset), ("Out-Of-Distribution", ood_dataset)]:
        if not dataset:
            continue
        total = len(dataset)

        for pol_name in policies:
            for max_def in max_deferral_bounds:
                allowed_count = 0
                deferred_count = 0
                forced_count = 0
                observed_qirs = []
                sla_violations = 0

                curr_streak = 0
                max_streak = 0
                deferral_streaks = []
                starvation_events = 0

                for row in dataset:
                    act_qir = float(row["qir_pct"])
                    feat_dict = {
                        "pre_cpu_util_pct": float(row.get("pre_cpu_util_pct", 30.0)),
                        "pre_disk_write_bytes_sec": float(row.get("pre_disk_write_bytes_sec", 0.0))
                    }
                    pred_rf = float(row.get("pred_rf_qir", act_qir))
                    pred_q95 = float(row.get("pred_q95_qir", act_qir + 5.0))
                    pred_conf = float(row.get("pred_conf_ub", act_qir + 8.5))

                    dec_type = "Policy F: Adaptive Conformal Risk Policy" if pol_name == "Policy F: Adaptive Conformal Risk Policy" else pol_name
                    decision, is_forced = make_policy_decision(
                        policy_type=dec_type,
                        feature_dict=feat_dict,
                        pred_rf_qir=pred_rf,
                        pred_q95_qir=pred_q95,
                        pred_conf_ub=pred_conf,
                        sla_threshold=sla_threshold,
                        risk_budget=0.05,
                        max_deferrals=max_def,
                        consecutive_deferrals=curr_streak
                    )

                    if decision == "RUN":
                        allowed_count += 1
                        if is_forced:
                            forced_count += 1
                        observed_qirs.append(act_qir)
                        if act_qir > sla_threshold:
                            sla_violations += 1
                        if curr_streak > 0:
                            deferral_streaks.append(curr_streak)
                            if curr_streak >= 3:
                                starvation_events += 1
                            curr_streak = 0
                    else:
                        deferred_count += 1
                        observed_qirs.append(0.0)
                        curr_streak += 1
                        if curr_streak > max_streak:
                            max_streak = curr_streak

                if curr_streak > 0:
                    deferral_streaks.append(curr_streak)
                    if curr_streak >= 3:
                        starvation_events += 1

                comp_rate = (allowed_count / total) * 100.0
                def_rate = (deferred_count / total) * 100.0
                forced_rate = (forced_count / total) * 100.0
                mean_qir = sum(observed_qirs) / total
                sorted_qirs = sorted(observed_qirs)
                med_qir = sorted_qirs[total // 2]
                p95_qir = sorted_qirs[min(total - 1, int(total * 0.95))]
                max_qir = sorted_qirs[-1]
                sla_viol_rate = (sla_violations / total) * 100.0
                mean_streak = sum(deferral_streaks) / len(deferral_streaks) if deferral_streaks else 0.0

                results.append({
                    "dataset_scope": scope_name,
                    "policy_name": pol_name,
                    "max_deferrals_bound": max_def,
                    "total_observations": total,
                    "maintenance_completion_rate_pct": round(comp_rate, 2),
                    "forced_runs_pct": round(forced_rate, 2),
                    "maintenance_deferral_rate_pct": round(def_rate, 2),
                    "mean_qir_pct": round(mean_qir, 2),
                    "median_qir_pct": round(med_qir, 2),
                    "p95_qir_pct": round(p95_qir, 2),
                    "max_qir_pct": round(max_qir, 2),
                    "sla_violation_rate_pct": round(sla_viol_rate, 2),
                    "sla_protection_rate_pct": round(100.0 - sla_viol_rate, 2),
                    "max_consecutive_deferrals": max_streak,
                    "mean_deferral_streak": round(mean_streak, 2),
                    "number_of_starvation_events": starvation_events
                })

    out_csv = os.path.join(RESULTS_DIR, "starvation_protection_results.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved starvation protection evaluation to {out_csv}")

    # Print summary table
    print("\n--- Bounded Starvation Protection Summary (MAX_DEFERRALS in {0, 2, 3}) ---")
    print(f"{'Scope':<18} | {'Policy':<36} | {'MAX_DEF':<8} | {'Completion %':<12} | {'Forced %':<10} | {'SLA Viol %':<10} | {'Starvation'}")
    print("-" * 115)
    for r in results:
        if r["max_deferrals_bound"] in [0, 2, 3]:
            print(f"{r['dataset_scope']:<18} | {r['policy_name']:<36} | {r['max_deferrals_bound']:<8} | {r['maintenance_completion_rate_pct']:<12}% | {r['forced_runs_pct']:<10}% | {r['sla_violation_rate_pct']:<10}% | {r['number_of_starvation_events']}")

if __name__ == "__main__":
    run_starvation_protection_evaluation()
