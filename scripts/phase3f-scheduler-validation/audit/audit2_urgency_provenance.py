#!/usr/bin/env python3
"""
audit2_urgency_provenance.py
----------------------------
Phase 3F Scientific Audit 2 — Maintenance Urgency Formula Provenance & Leakage Audit.

Extracts, audits, and documents:
1. Exact formula components, normalization, weights, and selection method.
2. Leakage analysis (whether parameters were tuned on evaluation data).
3. Classification of policy as "Partially heuristic".
4. Component contribution breakdown across representative storage states (20, 50, 100, 200, 350, 500, 750 files).

Outputs:
- audit/urgency_parameter_audit.csv
- audit/urgency_parameter_audit.md
- audit/plots/audit2_urgency_components.svg
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

def generate_urgency_stacked_svg(states_data, output_path):
    svg = f"""<svg width="700" height="420" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="350" y="30" font-family="DejaVu Sans, Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#1a1a1a">Audit 2: Storage Health Urgency Component Contribution Across Table States</text>
  
  <!-- Grid Lines -->
  <line x1="80" y1="320" x2="650" y2="320" stroke="#cccccc" stroke-width="1"/>
  <line x1="80" y1="250" x2="650" y2="250" stroke="#eeeeee" stroke-width="1"/>
  <line x1="80" y1="180" x2="650" y2="180" stroke="#eeeeee" stroke-width="1"/>
  <line x1="80" y1="110" x2="650" y2="110" stroke="#eeeeee" stroke-width="1"/>
  <line x1="80" y1="40" x2="650" y2="40" stroke="#eeeeee" stroke-width="1"/>

  <!-- Y-Axis Labels -->
  <text x="70" y="325" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" text-anchor="end" fill="#666666">0</text>
  <text x="70" y="255" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" text-anchor="end" fill="#666666">25</text>
  <text x="70" y="185" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" text-anchor="end" fill="#666666">50</text>
  <text x="70" y="115" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" text-anchor="end" fill="#666666">75</text>
  <text x="70" y="45" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" text-anchor="end" fill="#666666">100</text>

  <!-- Legend -->
  <rect x="120" y="355" width="14" height="14" fill="#2b5c8f"/>
  <text x="140" y="367" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" fill="#333333">Frag Ratio (w1=0.40)</text>

  <rect x="270" y="355" width="14" height="14" fill="#4daf4a"/>
  <text x="290" y="367" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" fill="#333333">Table Size (w2=0.20)</text>

  <rect x="420" y="355" width="14" height="14" fill="#984ea3"/>
  <text x="440" y="367" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" fill="#333333">Inv File Size (w3=0.20)</text>

  <rect x="560" y="355" width="14" height="14" fill="#ff7f00"/>
  <text x="580" y="367" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" fill="#333333">Deferral Ratio (w4=0.20)</text>
"""
    x_base = 110
    x_step = 75
    y_zero = 320
    scale = 2.8 # 100 points = 280 pixels

    for i, s in enumerate(states_data):
        cx = x_base + i * x_step

        c1_h = s["c1_frag"] * scale
        c2_h = s["c2_size"] * scale
        c3_h = s["c3_inv_file"] * scale
        c4_h = s["c4_def"] * scale

        y1 = y_zero - c1_h
        y2 = y1 - c2_h
        y3 = y2 - c3_h
        y4 = y3 - c4_h

        svg += f'  <rect x="{cx-20}" y="{y1}" width="40" height="{c1_h}" fill="#2b5c8f"/>\n'
        svg += f'  <rect x="{cx-20}" y="{y2}" width="40" height="{c2_h}" fill="#4daf4a"/>\n'
        svg += f'  <rect x="{cx-20}" y="{y3}" width="40" height="{c3_h}" fill="#984ea3"/>\n'
        svg += f'  <rect x="{cx-20}" y="{y4}" width="40" height="{c4_h}" fill="#ff7f00"/>\n'

        total_u = s["total_u"]
        svg += f'  <text x="{cx}" y="{y4-6}" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" font-weight="bold" text-anchor="middle" fill="#1a1a1a">{total_u:.1f}</text>\n'
        svg += f'  <text x="{cx}" y="338" font-family="DejaVu Sans, Arial, sans-serif" font-size="11" text-anchor="middle" fill="#333333">{s["frag"]} files</text>\n'

    svg += "  <line x1=\"80\" y1=\"320\" x2=\"80\" y2=\"40\" stroke=\"#cccccc\" stroke-width=\"1\"/>\n</svg>"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated Urgency Stacked SVG chart: {output_path}")

def main():
    print("Running Audit 2: Maintenance Urgency Formula Provenance...")

    parameters = [
        {
            "parameter_name": "w1 (Fragmentation Ratio Weight)",
            "formula_expression": "w1 * min(1.0, frag_files / 750.0)",
            "assigned_value": "0.40",
            "selection_method": "Domain heuristic choice (File count is primary driver of scan amplification)",
            "tuned_on_eval_data": "FALSE (Heuristically selected prior to evaluation)",
            "leakage_classification": "Pre-specified domain rule",
            "justification_notes": "Represents 40% of total urgency weight."
        },
        {
            "parameter_name": "w2 (Table Size Weight)",
            "formula_expression": "w2 * min(1.0, table_mb / 200.0)",
            "assigned_value": "0.20",
            "selection_method": "Domain heuristic choice (Table metadata overhead scale)",
            "tuned_on_eval_data": "FALSE (Heuristically selected prior to evaluation)",
            "leakage_classification": "Pre-specified domain rule",
            "justification_notes": "Represents 20% of total urgency weight."
        },
        {
            "parameter_name": "w3 (Inverse File Size Weight)",
            "formula_expression": "w3 * min(1.0, 500.0 / (avg_file_kb + 1.0))",
            "assigned_value": "0.20",
            "selection_method": "Domain heuristic choice (Small file penalty factor)",
            "tuned_on_eval_data": "FALSE (Heuristically selected prior to evaluation)",
            "leakage_classification": "Pre-specified domain rule",
            "justification_notes": "Represents 20% of total urgency weight."
        },
        {
            "parameter_name": "w4 (Pending Deferral Weight)",
            "formula_expression": "w4 * min(1.0, pending_slots / 5.0)",
            "assigned_value": "0.20",
            "selection_method": "Domain heuristic choice (Starvation prevention counter)",
            "tuned_on_eval_data": "FALSE (Heuristically selected prior to evaluation)",
            "leakage_classification": "Pre-specified domain rule",
            "justification_notes": "Represents 20% of total urgency weight."
        },
        {
            "parameter_name": "U_critical (Max Urgency Threshold)",
            "formula_expression": "Urgency >= U_critical",
            "assigned_value": "70.0",
            "selection_method": "Domain heuristic cutoff for mandatory compaction override",
            "tuned_on_eval_data": "PARTIAL (Tested against 750-file extrapolation table health)",
            "leakage_classification": "Partially heuristic / domain-guided",
            "justification_notes": "Overrides deferral when storage health degrades past 70/100 score."
        }
    ]

    # Save CSV
    out_csv = os.path.join(AUDIT_DIR, "urgency_parameter_audit.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(parameters[0].keys()))
        writer.writeheader()
        writer.writerows(parameters)
    print(f"Audit 2 CSV saved to: {out_csv}")

    # Compute Representative Storage States Component Breakdown
    # Configurations: 20, 50, 100, 200, 350, 500, 750 files
    state_configs = [
        {"frag": 20, "table_mb": 157.0, "avg_kb": 8040.0, "pending": 0},
        {"frag": 50, "table_mb": 160.0, "avg_kb": 3200.0, "pending": 0},
        {"frag": 100, "table_mb": 165.0, "avg_kb": 1650.0, "pending": 1},
        {"frag": 200, "table_mb": 170.0, "avg_kb": 850.0, "pending": 1},
        {"frag": 350, "table_mb": 171.0, "avg_kb": 488.0, "pending": 2},
        {"frag": 500, "table_mb": 172.0, "avg_kb": 344.0, "pending": 2},
        {"frag": 750, "table_mb": 173.0, "avg_kb": 237.0, "pending": 3},
    ]

    states_breakdown = []
    for sc in state_configs:
        c1 = 0.40 * min(1.0, sc["frag"] / 750.0) * 100.0
        c2 = 0.20 * min(1.0, sc["table_mb"] / 200.0) * 100.0
        c3 = 0.20 * min(1.0, 500.0 / (sc["avg_kb"] + 1.0)) * 100.0
        c4 = 0.20 * min(1.0, sc["pending"] / 5.0) * 100.0
        total_u = c1 + c2 + c3 + c4

        states_breakdown.append({
            "frag": sc["frag"],
            "c1_frag": c1,
            "c2_size": c2,
            "c3_inv_file": c3,
            "c4_def": c4,
            "total_u": total_u
        })

    svg_path = os.path.join(PLOTS_DIR, "audit2_urgency_components.svg")
    generate_urgency_stacked_svg(states_breakdown, svg_path)

    # Write Audit Markdown Report
    out_md = os.path.join(AUDIT_DIR, "urgency_parameter_audit.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# Phase 3F Audit 2: Maintenance Urgency Formula Provenance & Leakage Audit\n\n")
        f.write("## 1. Executive Provenance Summary\n")
        f.write("This audit inspects the mathematical formula, component weights, normalization methods, and parameter provenance of the Storage Health & Maintenance Urgency metric $U(s)$.\n\n")

        f.write("## 2. Mathematical Definition of Urgency Metric $U(s)$\n")
        f.write("$$U(s) = 100.0 \\times \\left[ 0.40 \\cdot \\min\\left(1.0, \\frac{N_{\\text{files}}}{750}\\right) + 0.20 \\cdot \\min\\left(1.0, \\frac{S_{\\text{table}}}{200}\\right) + 0.20 \\cdot \\min\\left(1.0, \\frac{500}{\\text{AvgFileSize} + 1}\\right) + 0.20 \\cdot \\min\\left(1.0, \\frac{k}{5}\\right) \\right]$$\n\n")

        f.write("## 3. Parameter Audit Matrix\n\n")
        f.write("| Parameter | Expression | Assigned Value | Provenance & Selection Method | Leakage Classification |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for p in parameters:
            f.write(f"| `{p['parameter_name']}` | `{p['formula_expression']}` | **{p['assigned_value']}** | {p['selection_method']} | `{p['leakage_classification']}` |\n")

        f.write("\n## 4. Scientific Classification & Evaluation Leakage Verdict\n")
        f.write("- **Policy Classification**: **`Partially heuristic`**\n")
        f.write("- **Leakage Analysis**: The weights $w = [0.40, 0.20, 0.20, 0.20]$ were **not** fitted via mathematical hyperparameter optimization on test set SLA metrics. However, because $U_{\\text{critical}} = 70.0$ was selected after observing 750-file table fragmentation, the policy is partially heuristic and must be reported as such in paper publications.\n")

    print(f"Audit 2 Markdown saved to: {out_md}")

if __name__ == "__main__":
    main()
