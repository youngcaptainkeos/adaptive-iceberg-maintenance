#!/usr/bin/env python3
import os
import shutil
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams.update({
    'font.size': 11,
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'figure.titlesize': 16
})

OUT_DIR_ROOT = "figures"
OUT_DIR_RUN = "results/runs/run_002/figures"
os.makedirs(OUT_DIR_ROOT, exist_ok=True)
os.makedirs(OUT_DIR_RUN, exist_ok=True)

df_a = pd.read_csv("results/runs/run_002/eval/run_a_baseline.csv")
df_b = pd.read_csv("results/runs/run_002/eval/run_b_costbenefit.csv")

# Filter out initial tick 0 with 0 latency for clean statistical plotting
df_a_clean = df_a[df_a['elapsed_s'] > 0].copy()
df_b_clean = df_b[df_b['elapsed_s'] > 0].copy()

# -------------------------------------------------------------
# 1. LATENCY TIMELINE WITH COMPACTIONS & INTENSITY
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), sharex=True, gridspec_kw={'height_ratios': [2.5, 1]})

# Baseline
ax1.plot(df_a['elapsed_s'] / 3600.0, df_a['p95_query_latency_ms'] / 1000.0,
         color='#d95f02', alpha=0.75, linewidth=1.8, label='SOTA Baseline Policy')
sota_runs = df_a[df_a['decision'] == 'RUN']
ax1.scatter(sota_runs['elapsed_s'] / 3600.0, sota_runs['p95_query_latency_ms'] / 1000.0,
            color='#d95f02', marker='X', s=120, edgecolors='black', zorder=5, label=f'Baseline Compaction (n={len(sota_runs)})')

# Cost-Benefit
ax1.plot(df_b['elapsed_s'] / 3600.0, df_b['p95_query_latency_ms'] / 1000.0,
         color='#1f78b4', alpha=0.85, linewidth=1.8, label='Conformal Cost-Benefit Agent (Ours)')
cb_runs = df_b[df_b['decision'] == 'RUN']
ax1.scatter(cb_runs['elapsed_s'] / 3600.0, cb_runs['p95_query_latency_ms'] / 1000.0,
            color='#33a02c', marker='o', s=35, alpha=0.7, edgecolors='none', zorder=4, label=f'Agent Compaction (n={len(cb_runs)})')

ax1.set_ylabel('P95 Latency (seconds)')
ax1.set_title('(a) P95 Query Latency & Compaction Scheduling Over 8-Hour Production Horizon', fontweight='bold')
ax1.legend(loc='upper right', frameon=True, framealpha=0.9)
ax1.set_ylim(0, 100)

# Workload trace intensity
ax2.plot(df_a['elapsed_s'] / 3600.0, df_a['intensity'], color='#636363', linewidth=1.5, label='Trace Workload Intensity')
ax2.axhspan(0.0, 0.3, color='#e0f3db', alpha=0.5, label='LOW Intensity (<0.3)')
ax2.axhspan(0.3, 0.7, color='#fff7bc', alpha=0.5, label='HIGH Intensity (0.3-0.7)')
ax2.axhspan(0.7, 1.0, color='#fee391', alpha=0.5, label='BURST Intensity (>0.7)')
ax2.set_xlabel('Elapsed Time (Hours)')
ax2.set_ylabel('Intensity (0-1)')
ax2.set_ylim(0, 1.05)
ax2.set_title('(b) Dynamic Workload Trace Intensity (Google Cluster Trace)', fontweight='bold', fontsize=12)
ax2.legend(loc='upper right', ncol=4, frameon=True, framealpha=0.9, fontsize=9)

plt.tight_layout()
p1 = os.path.join(OUT_DIR_ROOT, "run_002_latency_timeline.png")
plt.savefig(p1, dpi=300)
shutil.copy(p1, os.path.join(OUT_DIR_RUN, "run_002_latency_timeline.png"))
plt.close()
print("Saved 1: latency timeline")

# -------------------------------------------------------------
# 2. FRAGMENTATION TRAJECTORY (DATA FILE COUNT OVER TIME)
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(14, 5.5))

ax.plot(df_a['elapsed_s'] / 3600.0, df_a['frag_file_count'],
        color='#d95f02', linewidth=2.4, label='SOTA Baseline (Compacts 3x, files accumulate unbounded)')
ax.plot(df_b['elapsed_s'] / 3600.0, df_b['frag_file_count'],
        color='#1f78b4', linewidth=2.4, label='Conformal Cost-Benefit Agent (Continuous sawtooth compaction, files stay ~33-36)')

ax.axhline(33, color='gray', linestyle=':', alpha=0.7, label='Optimal Compacted State (33 files)')

# Annotations
ax.annotate('Baseline: unmanaged growth (up to 77 files)', xy=(7.5, 75), xytext=(5.2, 110),
            arrowprops=dict(facecolor='#d95f02', shrink=0.08, width=1.5, headwidth=8),
            fontweight='bold', color='#d95f02')

ax.annotate('Cost-Benefit: bounded between 33-36 files\n(57% fewer files at horizon end)', xy=(7.0, 34), xytext=(3.5, 70),
            arrowprops=dict(facecolor='#1f78b4', shrink=0.08, width=1.5, headwidth=8),
            fontweight='bold', color='#1f78b4')

ax.set_xlabel('Elapsed Time (Hours)')
ax.set_ylabel('Fragmented Data File Count')
ax.set_title('Table Health & Fragmentation Trajectory Under Production Ingestion', fontweight='bold')
ax.legend(loc='upper right', frameon=True, framealpha=0.9)
ax.set_ylim(20, 200)

plt.tight_layout()
p2 = os.path.join(OUT_DIR_ROOT, "run_002_fragmentation_trend.png")
plt.savefig(p2, dpi=300)
shutil.copy(p2, os.path.join(OUT_DIR_RUN, "run_002_fragmentation_trend.png"))
plt.close()
print("Saved 2: fragmentation trend")

# -------------------------------------------------------------
# 3. EMPIRICAL CDF OF P95 QUERY LATENCIES
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6))

lat_a = np.sort(df_a_clean['p95_query_latency_ms'] / 1000.0)
cdf_a = np.arange(1, len(lat_a) + 1) / len(lat_a)

lat_b = np.sort(df_b_clean['p95_query_latency_ms'] / 1000.0)
cdf_b = np.arange(1, len(lat_b) + 1) / len(lat_b)

ax.plot(lat_a, cdf_a, color='#d95f02', linewidth=2.5, label=f'SOTA Baseline (Mean: {lat_a.mean():.1f}s, Max: {lat_a.max():.1f}s)')
ax.plot(lat_b, cdf_b, color='#1f78b4', linewidth=2.5, label=f'Cost-Benefit Agent (Mean: {lat_b.mean():.1f}s, Max: {lat_b.max():.1f}s)')

ax.axvline(lat_a.mean(), color='#d95f02', linestyle='--', alpha=0.6)
ax.axvline(lat_b.mean(), color='#1f78b4', linestyle='--', alpha=0.6)

ax.set_xlabel('P95 Query Latency (seconds)')
ax.set_ylabel('Cumulative Probability P(Latency ≤ X)')
ax.set_title('Empirical Cumulative Distribution Function (ECDF) of Query Latency', fontweight='bold')
ax.legend(loc='lower right', frameon=True, framealpha=0.9)
ax.set_xlim(0, 100)
ax.set_ylim(0, 1.02)

plt.tight_layout()
p3 = os.path.join(OUT_DIR_ROOT, "run_002_cdf_latency.png")
plt.savefig(p3, dpi=300)
shutil.copy(p3, os.path.join(OUT_DIR_RUN, "run_002_cdf_latency.png"))
plt.close()
print("Saved 3: cdf latency")

# -------------------------------------------------------------
# 4. REGIME-BY-REGIME COMPARISON BAR CHART
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

regimes = ['LOW', 'HIGH', 'BURST']
x = np.arange(len(regimes))
width = 0.35

# Latency by regime
lat_means_a = []
lat_means_b = []
for reg in regimes:
    sub_a = df_a_clean[df_a_clean['regime'] == reg]
    sub_b = df_b_clean[df_b_clean['regime'] == reg]
    lat_means_a.append(sub_a['p95_query_latency_ms'].mean() / 1000.0)
    lat_means_b.append(sub_b['p95_query_latency_ms'].mean() / 1000.0)

b1 = ax1.bar(x - width/2, lat_means_a, width, label='SOTA Baseline', color='#d95f02', edgecolor='black', linewidth=1)
b2 = ax1.bar(x + width/2, lat_means_b, width, label='Cost-Benefit Agent', color='#1f78b4', edgecolor='black', linewidth=1)

ax1.set_ylabel('Mean Latency (seconds)')
ax1.set_title('(a) Query Latency Across Workload Regimes', fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(regimes)
ax1.legend(loc='upper right')
ax1.set_ylim(0, 55)

for bar in b1:
    h = bar.get_height()
    ax1.annotate(f'{h:.1f}s', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 4),
                 textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold')
for bar in b2:
    h = bar.get_height()
    ax1.annotate(f'{h:.1f}s', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 4),
                 textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold')

# Compaction frequency by regime
comp_rate_a = []
comp_rate_b = []
for reg in regimes:
    sub_a = df_a[df_a['regime'] == reg]
    sub_b = df_b[df_b['regime'] == reg]
    comp_rate_a.append((sub_a['decision'] == 'RUN').mean() * 100.0)
    comp_rate_b.append((sub_b['decision'] == 'RUN').mean() * 100.0)

b3 = ax2.bar(x - width/2, comp_rate_a, width, label='SOTA Baseline', color='#d95f02', edgecolor='black', linewidth=1)
b4 = ax2.bar(x + width/2, comp_rate_b, width, label='Cost-Benefit Agent', color='#1f78b4', edgecolor='black', linewidth=1)

ax2.set_ylabel('Compaction Action Rate (%)')
ax2.set_title('(b) Proactive Maintenance Rate by Regime', fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(regimes)
ax2.legend(loc='upper left')
ax2.set_ylim(0, 95)

for bar in b3:
    h = bar.get_height()
    ax2.annotate(f'{h:.1f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 4),
                 textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold')
for bar in b4:
    h = bar.get_height()
    ax2.annotate(f'{h:.1f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 4),
                 textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
p4 = os.path.join(OUT_DIR_ROOT, "run_002_regime_breakdown.png")
plt.savefig(p4, dpi=300)
shutil.copy(p4, os.path.join(OUT_DIR_RUN, "run_002_regime_breakdown.png"))
plt.close()
print("Saved 4: regime breakdown")

# -------------------------------------------------------------
# 5. MODEL FEATURE IMPORTANCES
# -------------------------------------------------------------
features_a = [
    ('cpu_util_avg_1min', 0.3103),
    ('cpu_util_avg_5min', 0.2829),
    ('cpu_trend', 0.1915),
    ('intensity', 0.1051),
    ('mem_used_pct', 0.0688),
    ('avg_file_size_kb', 0.0359),
    ('table_size_mb', 0.0055),
    ('frag_file_count', 0.0001)
]

features_b = [
    ('cpu_util_avg_1min', 0.2706),
    ('cpu_trend', 0.2462),
    ('intensity', 0.1712),
    ('cpu_util_avg_5min', 0.1173),
    ('mem_used_pct', 0.1156),
    ('avg_file_size_kb', 0.0581),
    ('frag_file_count', 0.0148),
    ('table_size_mb', 0.0062)
]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

names_a = [f[0] for f in reversed(features_a)]
vals_a = [f[1] * 100 for f in reversed(features_a)]
ax1.barh(names_a, vals_a, color='#2b8cbe', edgecolor='black', linewidth=1)
ax1.set_xlabel('Feature Importance (%)')
ax1.set_title('Model A: Active Compaction Regime\n(What drives query latency during rewrite?)', fontweight='bold')
ax1.set_xlim(0, 38)
for i, v in enumerate(vals_a):
    ax1.text(v + 0.8, i, f'{v:.1f}%', va='center', fontweight='bold', fontsize=10)

names_b = [f[0] for f in reversed(features_b)]
vals_b = [f[1] * 100 for f in reversed(features_b)]
ax2.barh(names_b, vals_b, color='#7bccc4', edgecolor='black', linewidth=1)
ax2.set_xlabel('Feature Importance (%)')
ax2.set_title('Model B: Baseline Operation Regime\n(What drives query latency normally?)', fontweight='bold')
ax2.set_xlim(0, 38)
for i, v in enumerate(vals_b):
    ax2.text(v + 0.8, i, f'{v:.1f}%', va='center', fontweight='bold', fontsize=10)

plt.tight_layout()
p5 = os.path.join(OUT_DIR_ROOT, "run_002_model_features.png")
plt.savefig(p5, dpi=300)
shutil.copy(p5, os.path.join(OUT_DIR_RUN, "run_002_model_features.png"))
plt.close()
print("Saved 5: model features")

