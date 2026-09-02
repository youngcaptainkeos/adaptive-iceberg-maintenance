#!/usr/bin/env python3
"""
plot_pareto_frontiers.py
------------------------
Generates publication-quality visual plots for In-Distribution and Out-Of-Distribution
Policy Pareto Frontiers (Maintenance Completion Rate vs SLA Protection Rate) using PIL.

Outputs:
- analysis/plots/policy_pareto_frontier.png
- analysis/plots/ood_policy_pareto_frontier.png
"""

import os
import sys
import csv
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3D_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3d-validation-generalization")
RESULTS_DIR = os.path.join(PHASE3D_DIR, "results")
PLOTS_DIR = os.path.join(PHASE3D_DIR, "analysis/plots")

os.makedirs(PLOTS_DIR, exist_ok=True)

def load_csv(path: str) -> List[Dict[str, Any]]:
    rows = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append(r)
    return rows

def generate_pil_pareto_plot(csv_path: str, output_png: str, title_text: str):
    data = load_csv(csv_path)
    if not data:
        print(f"Error: No data found at {csv_path}")
        return

    width, height = 1200, 800
    bg_color = (255, 255, 255)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_legend = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except Exception:
        font_title = font_label = font_small = font_legend = ImageFont.load_default()

    # Define chart margins
    margin_left = 120
    margin_right = 320
    margin_top = 100
    margin_bottom = 100

    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    # Title
    draw.text((margin_left, 35), title_text, fill=(30, 30, 30), font=font_title)

    # Subtitle / Axis Info
    draw.text((margin_left, 68), "X-Axis: Maintenance Completion Rate (%)  |  Y-Axis: SLA Protection Rate (%) [100% - SLA Violation Rate]", fill=(80, 80, 80), font=font_small)

    # Draw grid lines & axes (X: 0 to 100, Y: 60 to 100)
    x_min, x_max = 0.0, 100.0
    y_min, y_max = 60.0, 100.0

    # Grid background box
    draw.rectangle([margin_left, margin_top, margin_left + plot_w, margin_top + plot_h], outline=(200, 200, 200), fill=(250, 252, 255), width=2)

    # Y-axis ticks & grid lines (60% to 100% in steps of 5%)
    for y_val in range(60, 105, 5):
        y_pos = margin_top + plot_h - int(((y_val - y_min) / (y_max - y_min)) * plot_h)
        draw.line([(margin_left, y_pos), (margin_left + plot_w, y_pos)], fill=(225, 230, 240), width=1)
        draw.text((margin_left - 50, y_pos - 8), f"{y_val}%", fill=(70, 70, 70), font=font_small)

    # X-axis ticks & grid lines (0% to 100% in steps of 10%)
    for x_val in range(0, 110, 10):
        x_pos = margin_left + int(((x_val - x_min) / (x_max - x_min)) * plot_w)
        draw.line([(x_pos, margin_top), (x_pos, margin_top + plot_h)], fill=(225, 230, 240), width=1)
        draw.text((x_pos - 15, margin_top + plot_h + 12), f"{x_val}%", fill=(70, 70, 70), font=font_small)

    # Axis Labels
    draw.text((margin_left + plot_w // 2 - 120, margin_top + plot_h + 45), "Maintenance Completion Rate (%)", fill=(30, 30, 30), font=font_label)
    
    # Policy Colors
    policy_colors = {
        "Policy 1: Always Run": (217, 83, 79),
        "Policy 2: Always Defer": (108, 117, 125),
        "Policy 3: Explicit Resource Heuristic": (240, 173, 78),
        "Policy 4: Predictive Mean-QIR Policy": (2, 117, 216),
        "Policy 5: Raw Quantile Conservative Policy": (91, 192, 222),
        "Policy 6: Split-Conformal Upper Bound Policy": (92, 184, 92),
        "Policy 7: Random Policy (P=0.5)": (170, 102, 204)
    }

    pareto_points = []
    all_points = []

    for r in data:
        name = r["policy_name"]
        comp = float(r["maintenance_completion_rate_pct"])
        prot = float(r["sla_protection_rate_pct"])
        is_pareto = str(r.get("is_pareto_optimal", "False")).lower() == "true"

        px = margin_left + int(((comp - x_min) / (x_max - x_min)) * plot_w)
        py = margin_top + plot_h - int(((prot - y_min) / (y_max - y_min)) * plot_h)

        color = policy_colors.get(name, (50, 50, 50))
        all_points.append((comp, prot, px, py, name, color, is_pareto))
        if is_pareto:
            pareto_points.append((comp, prot, px, py, name))

    # Sort pareto points by completion rate to draw frontier curve
    pareto_points.sort(key=lambda p: p[0])

    if len(pareto_points) > 1:
        for k in range(len(pareto_points) - 1):
            x1, y1 = pareto_points[k][2], pareto_points[k][3]
            x2, y2 = pareto_points[k+1][2], pareto_points[k+1][3]
            draw.line([(x1, y1), (x2, y2)], fill=(40, 40, 40), width=3)

    # Draw Points & Annotations
    for comp, prot, px, py, name, color, is_pareto in all_points:
        radius = 9 if is_pareto else 6
        if is_pareto:
            draw.ellipse([px - radius, py - radius, px + radius, py + radius], fill=color, outline=(0, 0, 0), width=2)
        else:
            # Draw 'X' for non-pareto dominated point
            draw.line([px - radius, py - radius, px + radius, py + radius], fill=color, width=3)
            draw.line([px - radius, py + radius, px + radius, py - radius], fill=color, width=3)

        # Label annotation
        short_id = name.split(":")[0]
        offset_y = -22 if prot > 95 else 10
        offset_x = 10 if comp < 90 else -40
        draw.text((px + offset_x, py + offset_y), short_id, fill=(20, 20, 20), font=font_label)

    # Draw Legend Box on the Right Margin
    legend_left = margin_left + plot_w + 30
    legend_top = margin_top
    draw.rectangle([legend_left, legend_top, legend_left + 270, legend_top + 320], outline=(180, 180, 180), fill=(255, 255, 255), width=1)
    draw.text((legend_left + 15, legend_top + 12), "Scheduling Policies", fill=(20, 20, 20), font=font_label)

    curr_leg_y = legend_top + 42
    for p_name, color in policy_colors.items():
        is_p = any(pt[4] == p_name for pt in pareto_points)
        draw.rectangle([legend_left + 15, curr_leg_y + 2, legend_left + 27, curr_leg_y + 14], fill=color, outline=(0,0,0))
        label_txt = p_name.split(":")[0] + ": " + p_name.split(":")[1].strip()
        if len(label_txt) > 28:
            label_txt = label_txt[:26] + "..."
        draw.text((legend_left + 35, curr_leg_y), label_txt, fill=(30, 30, 30), font=font_legend)
        if is_p:
            draw.text((legend_left + 235, curr_leg_y), "★", fill=(220, 160, 0), font=font_legend)
        curr_leg_y += 28

    # Legend Key
    draw.text((legend_left + 15, curr_leg_y + 15), "★ Pareto Optimal Policy", fill=(180, 130, 0), font=font_legend)
    draw.line([(legend_left + 15, curr_leg_y + 40), (legend_left + 50, curr_leg_y + 40)], fill=(40, 40, 40), width=3)
    draw.text((legend_left + 55, curr_leg_y + 32), "Pareto Frontier Line", fill=(50, 50, 50), font=font_legend)

    img.save(output_png, "PNG")
    print(f"Saved Pareto frontier plot image to {output_png}")

def main():
    ind_csv = os.path.join(RESULTS_DIR, "policy_pareto_results.csv")
    ood_csv = os.path.join(RESULTS_DIR, "ood_policy_tradeoff_results.csv")

    ind_png = os.path.join(PLOTS_DIR, "policy_pareto_frontier.png")
    ood_png = os.path.join(PLOTS_DIR, "ood_policy_pareto_frontier.png")

    generate_pil_pareto_plot(ind_csv, ind_png, "In-Distribution Policy Pareto Frontier (Phase 3B Dataset)")
    generate_pil_pareto_plot(ood_csv, ood_png, "Out-of-Distribution Policy Pareto Frontier (Phase 3D Track 2 Dataset)")

if __name__ == "__main__":
    main()
