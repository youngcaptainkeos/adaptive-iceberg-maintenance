#!/usr/bin/env python3
"""
audit1_policy_execution.py
--------------------------
Phase 3F Scientific Audit 1 — Policy Execution vs Counterfactual Evaluation.

Explicitly inspects and classifies all reported policy results across Phase 3A-3F into:
1. Physically Executed Online Policy Evaluation
2. Offline Counterfactual Policy Evaluation
3. Hybrid / Mixed Evaluation

Outputs:
- audit/policy_execution_audit.csv
- audit/plots/audit1_policy_execution_classification.svg
"""

import os
import sys
import csv

import os
WORKSPACE_DIR = os.environ.get("REPO_DIR", "/media/shashank/Data1/PDocuments/Capstone/implementation")
PHASE3F_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3f-scheduler-validation")
AUDIT_DIR = os.path.join(PHASE3F_DIR, "audit")
PLOTS_DIR = os.path.join(AUDIT_DIR, "plots")

os.makedirs(AUDIT_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)

def generate_svg_chart(counts, output_path):
    svg = f"""<svg width="600" height="350" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="300" y="30" font-family="DejaVu Sans, Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#1a1a1a">Audit 1: Classification of Policy Evaluations in Research Pipeline</text>
  
  <!-- Y-Axis Lines -->
  <line x1="80" y1="260" x2="540" y2="260" stroke="#cccccc" stroke-width="1"/>
  <line x1="80" y1="210" x2="540" y2="210" stroke="#eeeeee" stroke-width="1"/>
  <line x1="80" y1="160" x2="540" y2="160" stroke="#eeeeee" stroke-width="1"/>
  <line x1="80" y1="110" x2="540" y2="110" stroke="#eeeeee" stroke-width="1"/>
  <line x1="80" y1="60" x2="540" y2="60" stroke="#eeeeee" stroke-width="1"/>

  <!-- Y-Axis Labels -->
  <text x="70" y="265" font-family="DejaVu Sans, Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">0</text>
  <text x="70" y="215" font-family="DejaVu Sans, Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">1</text>
  <text x="70" y="165" font-family="DejaVu Sans, Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">2</text>
  <text x="70" y="115" font-family="DejaVu Sans, Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">3</text>
  <text x="70" y="65" font-family="DejaVu Sans, Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">4</text>

  <!-- Bars -->
  <!-- Physical (count = 3) -> height = 3 * 50 = 150 -> y = 260 - 150 = 110 -->
  <rect x="140" y="{260 - counts['Physically Executed Online'] * 50}" width="120" height="{counts['Physically Executed Online'] * 50}" fill="#2b5c8f" rx="4"/>
  <text x="200" y="{260 - counts['Physically Executed Online'] * 50 - 10}" font-family="DejaVu Sans, Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#2b5c8f">{counts['Physically Executed Online']}</text>
  <text x="200" y="285" font-family="DejaVu Sans, Arial, sans-serif" font-size="13" font-weight="bold" text-anchor="middle" fill="#333333">Physically Executed Online</text>
  <text x="200" y="305" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" text-anchor="middle" fill="#666666">(308 physical trials)</text>

  <!-- Counterfactual (count = 4) -> height = 4 * 50 = 200 -> y = 260 - 200 = 60 -->
  <rect x="340" y="{260 - counts['Offline Counterfactual'] * 50}" width="120" height="{counts['Offline Counterfactual'] * 50}" fill="#d95f02" rx="4"/>
  <text x="400" y="{260 - counts['Offline Counterfactual'] * 50 - 10}" font-family="DejaVu Sans, Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#d95f02">{counts['Offline Counterfactual']}</text>
  <text x="400" y="285" font-family="DejaVu Sans, Arial, sans-serif" font-size="13" font-weight="bold" text-anchor="middle" fill="#333333">Offline Counterfactual</text>
  <text x="400" y="305" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" text-anchor="middle" fill="#666666">(Dataset Filtering)</text>

  <!-- Axis Line -->
  <line x1="80" y1="260" x2="80" y2="50" stroke="#cccccc" stroke-width="1"/>
</svg>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated SVG chart: {output_path}")

def main():
    print("Running Audit 1: Policy Execution vs Counterfactual Evaluation...")

    evaluations = [
        {
            "policy_name": "Phase 3A Concurrent Compaction Baseline",
            "dataset_domain": "In-Distribution (50, 200, 500 files)",
            "evaluation_type": "Physically Executed Online Policy Evaluation",
            "physically_executed": "TRUE",
            "uses_observed_ground_truth_counterfactually": "FALSE",
            "scientific_claim_allowed": "Direct empirical measurement of query interference (+10.38% QIR)",
            "claim_limitation": "Covers immediate/greedy compaction scheduling only."
        },
        {
            "policy_name": "Phase 3B Random Forest Interference Regressor",
            "dataset_domain": "In-Distribution (50, 200, 500 files)",
            "evaluation_type": "Physically Executed Online Dataset / Offline Model Eval",
            "physically_executed": "TRUE (Dataset)",
            "uses_observed_ground_truth_counterfactually": "FALSE",
            "scientific_claim_allowed": "Predictive accuracy on pre-decision signals (MAE = 6.55% QIR)",
            "claim_limitation": "Evaluates prediction error on static dataset; does not run dynamic feedback control loop."
        },
        {
            "policy_name": "Phase 3C Policy Baselines (Heuristic, Threshold)",
            "dataset_domain": "In-Distribution (50, 200, 500 files)",
            "evaluation_type": "Offline Counterfactual Policy Evaluation",
            "physically_executed": "FALSE",
            "uses_observed_ground_truth_counterfactually": "TRUE",
            "scientific_claim_allowed": "Would have filtered 78% of observed SLA-violating trials under offline counterfactual evaluation",
            "claim_limitation": "Assumes system state and query sequence remain identical when compaction is deferred."
        },
        {
            "policy_name": "Phase 3D Track 1 Conformal Upper Prediction Bound",
            "dataset_domain": "In-Distribution LOCO-CV (50, 200, 500 files)",
            "evaluation_type": "Offline Counterfactual Policy Evaluation",
            "physically_executed": "FALSE",
            "uses_observed_ground_truth_counterfactually": "TRUE",
            "scientific_claim_allowed": "Achieved 91.07% empirical coverage and counterfactually prevented 100% of SLA violations",
            "claim_limitation": "Static dataset evaluation; ignores temporal accumulation of deferred compaction jobs."
        },
        {
            "policy_name": "Phase 3D Track 2 Zero-Shot OOD Experiment",
            "dataset_domain": "Interpolation Domain (100, 350 files)",
            "evaluation_type": "Physically Executed Online Policy Evaluation",
            "physically_executed": "TRUE",
            "uses_observed_ground_truth_counterfactually": "FALSE",
            "scientific_claim_allowed": "Verified physical generalizability on novel fragmentation levels (80 physical trials)",
            "claim_limitation": "Evaluated physical execution under fixed concurrent compaction trigger."
        },
        {
            "policy_name": "Phase 3E Adaptive Conformal Scheduler",
            "dataset_domain": "Combined ID + OOD (50 to 500 files)",
            "evaluation_type": "Offline Counterfactual Policy Evaluation",
            "physically_executed": "FALSE",
            "uses_observed_ground_truth_counterfactually": "TRUE",
            "scientific_claim_allowed": "Under offline counterfactual simulation, risk-urgency trade-off filtered 100% of SLA-violating trials",
            "claim_limitation": "Counterfactual model assumption; deferral cost approximated via synthetic delay model."
        },
        {
            "policy_name": "Phase 3F Step 1 Zero-Shot Extrapolation Experiment",
            "dataset_domain": "Extrapolation Domain (20, 750 files)",
            "evaluation_type": "Physically Executed Online Policy Evaluation",
            "physically_executed": "TRUE",
            "uses_observed_ground_truth_counterfactually": "FALSE",
            "scientific_claim_allowed": "Empirically measured physical query interference under extreme extrapolation (80 physical trials)",
            "claim_limitation": "Measures physical execution of queries under concurrent compaction; model evaluation is zero-shot prediction."
        },
        {
            "policy_name": "Phase 3F Step 2-6 Policy Audit & Urgency Scheduler",
            "dataset_domain": "Unified Benchmark Suite (20 to 750 files, N=328)",
            "evaluation_type": "Offline Counterfactual Policy Evaluation",
            "physically_executed": "FALSE",
            "uses_observed_ground_truth_counterfactually": "TRUE",
            "scientific_claim_allowed": "Under offline counterfactual evaluation on 328 physical trials, joint risk-urgency policy would have filtered 100% of SLA violations",
            "claim_limitation": "Offline counterfactual filtering model; does not execute dynamic online adaptive feedback loop."
        }
    ]

    out_csv = os.path.join(AUDIT_DIR, "policy_execution_audit.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(evaluations[0].keys()))
        writer.writeheader()
        writer.writerows(evaluations)
    print(f"Audit 1 CSV saved to: {out_csv}")

    types = [e["evaluation_type"] for e in evaluations]
    counts = {
        "Physically Executed Online": sum(1 for t in types if "Physically Executed" in t),
        "Offline Counterfactual": sum(1 for t in types if "Offline Counterfactual" in t)
    }

    svg_path = os.path.join(PLOTS_DIR, "audit1_policy_execution_classification.svg")
    generate_svg_chart(counts, svg_path)

if __name__ == "__main__":
    main()
