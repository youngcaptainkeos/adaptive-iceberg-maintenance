#!/usr/bin/env python3
import os
import sys
import csv
from PIL import Image, ImageDraw, ImageFont

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3D_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3d-validation-generalization")
RESULTS_DIR = os.path.join(PHASE3D_DIR, "results")
PLOTS_DIR = os.path.join(PHASE3D_DIR, "analysis/plots")

os.makedirs(PLOTS_DIR, exist_ok=True)

def generate_coverage_plot():
    calib_csv = os.path.join(RESULTS_DIR, "quantile_calibration_results.csv")
    if not os.path.exists(calib_csv):
        print(f"Error: {calib_csv} missing!", file=sys.stderr)
        sys.exit(1)

    configs = []
    coverages = []
    with open(calib_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            configs.append(r["config_id"])
            coverages.append(float(r["raw_quantile_coverage_pct"]))

    n_bars = len(configs)
    
    # Image dimensions
    width = 1200
    height = 650
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_val = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
        font_legend = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        font_title = font_sub = font_label = font_val = font_legend = ImageFont.load_default()

    # Title & Subtitle
    draw.text((40, 25), "Raw Quantile Model (q=0.95) Empirical Coverage per LOCO Fold", fill=(30, 30, 30), font=font_title)
    draw.text((40, 58), "Target: 95.0% Nominal Upper Bound Coverage | Overall Empirical Mean: 91.07%", fill=(80, 80, 80), font=font_sub)

    # Plot area margins
    margin_left = 80
    margin_right = 40
    margin_top = 110
    margin_bottom = 180

    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    # Y-axis scale (0% to 110%)
    y_min = 0.0
    y_max = 110.0

    def get_y_pix(val):
        return margin_top + plot_h - int((val - y_min) / (y_max - y_min) * plot_h)

    # Draw gridlines & y-axis labels
    for y_val in range(0, 101, 20):
        y_pix = get_y_pix(y_val)
        draw.line([(margin_left, y_pix), (width - margin_right, y_pix)], fill=(230, 230, 230), width=1)
        draw.text((margin_left - 45, y_pix - 7), f"{y_val}%", fill=(100, 100, 100), font=font_label)

    # Draw Target 95% line (Red dashed)
    y_95 = get_y_pix(95.0)
    for dash_x in range(margin_left, width - margin_right, 12):
        draw.line([(dash_x, y_95), (min(dash_x + 6, width - margin_right), y_95)], fill=(220, 50, 50), width=2)
    draw.text((width - margin_right - 140, y_95 - 18), "Target (95.0%)", fill=(220, 50, 50), font=font_legend)

    # Draw Overall Mean 91.07% line (Blue dotted)
    y_overall = get_y_pix(91.07)
    for dash_x in range(margin_left, width - margin_right, 8):
        draw.line([(dash_x, y_overall), (min(dash_x + 3, width - margin_right), y_overall)], fill=(50, 100, 220), width=2)
    draw.text((margin_left + 10, y_overall - 18), "Overall Mean (91.07%)", fill=(50, 100, 220), font=font_legend)

    # Draw Bars
    bar_gap = 18
    total_gaps = (n_bars - 1) * bar_gap
    bar_w = int((plot_w - total_gaps) / n_bars)

    for i, (cfg, cov) in enumerate(zip(configs, coverages)):
        x_left = margin_left + i * (bar_w + bar_gap)
        x_right = x_left + bar_w
        y_top = get_y_pix(cov)
        y_bot = get_y_pix(0.0)

        # Color: Green if >= 95%, Orange if 80-94%, Red if < 80%
        if cov >= 95.0:
            fill_color = (46, 125, 50)     # Green
            border_color = (27, 94, 32)
        elif cov >= 80.0:
            fill_color = (239, 108, 0)    # Orange
            border_color = (230, 81, 0)
        else:
            fill_color = (198, 40, 40)     # Red
            border_color = (183, 28, 28)

        draw.rectangle([(x_left, y_top), (x_right, y_bot)], fill=fill_color, outline=border_color, width=1)

        # Value text above bar
        draw.text((x_left + (bar_w // 2) - 16, y_top - 18), f"{cov:.1f}%", fill=(30, 30, 30), font=font_val)

        # Rotate config label below bar (draw vertically/shortened)
        label_text = cfg.replace("frag", "f").replace("_single_stream_", "_s_").replace("_multi_stream_", "_m_")
        draw.text((x_left, y_bot + 10), label_text, fill=(50, 50, 50), font=font_label)

    # Legend at bottom
    leg_y = height - 45
    draw.rectangle([(margin_left, leg_y), (margin_left + 16, leg_y + 16)], fill=(46, 125, 50))
    draw.text((margin_left + 24, leg_y), "Pass (Coverage >= 95%)", fill=(50, 50, 50), font=font_legend)

    draw.rectangle([(margin_left + 220, leg_y), (margin_left + 236, leg_y + 16)], fill=(239, 108, 0))
    draw.text((margin_left + 244, leg_y), "Moderate Undercoverage (80% - 94%)", fill=(50, 50, 50), font=font_legend)

    draw.rectangle([(margin_left + 520, leg_y), (margin_left + 536, leg_y + 16)], fill=(198, 40, 40))
    draw.text((margin_left + 544, leg_y), "Severe Failure (< 80%)", fill=(50, 50, 50), font=font_legend)

    plot_path = os.path.join(PLOTS_DIR, "raw_quantile_coverage_by_config.png")
    img.save(plot_path)
    print(f"Saved raw quantile coverage plot to: {plot_path}")

if __name__ == "__main__":
    generate_coverage_plot()
