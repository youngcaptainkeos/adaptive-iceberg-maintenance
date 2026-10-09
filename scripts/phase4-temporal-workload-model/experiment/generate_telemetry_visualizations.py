import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.patches as patches

import os
WORKSPACE_DIR = os.environ.get("REPO_DIR", "/media/shashank/Data1/PDocuments/Capstone/implementation")
PHASE4_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase4-temporal-workload-model")
RESULTS_DIR = os.path.join(PHASE4_DIR, "results")

# Setup seaborn
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.4)

def generate_visualizations():
    print("Loading datasets...")
    tel_path = os.path.join(RESULTS_DIR, "physical_telemetry.csv")
    q_path = os.path.join(RESULTS_DIR, "physical_queries.csv")
    
    if not os.path.exists(tel_path) or not os.path.exists(q_path):
        print("Error: Telemetry or Queries CSV not found. Make sure the experiment generated them.")
        return
        
    telemetry = pd.read_csv(tel_path)
    queries = pd.read_csv(q_path)
    
    if len(telemetry) == 0 or len(queries) == 0:
        print("Error: Datasets are empty.")
        return

    telemetry['timestamp'] = pd.to_numeric(telemetry['timestamp'])
    t0 = telemetry['timestamp'].min()
    
    telemetry['time_relative_min'] = (telemetry['timestamp'] - t0) / 60.0
    queries['time_relative_min'] = (queries['query_start_time'] - t0) / 60.0
    
    # Identify compaction regions
    telemetry['compaction_active'] = telemetry['compaction_active'].astype(bool)
    compaction_blocks = []
    in_compaction = False
    start_t = 0
    for _, row in telemetry.iterrows():
        if row['compaction_active'] and not in_compaction:
            start_t = row['time_relative_min']
            in_compaction = True
        elif not row['compaction_active'] and in_compaction:
            end_t = row['time_relative_min']
            compaction_blocks.append((start_t, end_t))
            in_compaction = False
    if in_compaction:
        compaction_blocks.append((start_t, telemetry['time_relative_min'].max()))
        
    print(f"Found {len(compaction_blocks)} compaction events.")

    # 1. Telemetry Timeline SVG
    print("Generating telemetry_timeline.svg...")
    fig, ax1 = plt.subplots(figsize=(15, 6))
    
    color = 'tab:red'
    ax1.set_xlabel('Time (Minutes)')
    ax1.set_ylabel('CPU Utilization (%)', color=color)
    ax1.plot(telemetry['time_relative_min'], telemetry['cpu_utilization_pct'], color=color, alpha=0.7, linewidth=1)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_ylim(0, 100)

    ax2 = ax1.twinx()  
    color = 'tab:blue'
    ax2.set_ylabel('Disk IOPS (Read+Write)', color=color)  
    total_iops = telemetry['disk_read_iops'] + telemetry['disk_write_iops']
    ax2.plot(telemetry['time_relative_min'], total_iops, color=color, alpha=0.5, linewidth=1)
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Shade compaction regions
    for (start, end) in compaction_blocks:
        ax1.axvspan(start, end, color='gray', alpha=0.3)
        
    # Custom legend for shaded region
    import matplotlib.lines as mlines
    comp_patch = patches.Patch(color='gray', alpha=0.3, label='Compaction Active')
    cpu_line = mlines.Line2D([], [], color='tab:red', label='CPU Util %')
    io_line = mlines.Line2D([], [], color='tab:blue', label='Total Disk IOPS')
    plt.legend(handles=[comp_patch, cpu_line, io_line], loc='upper right')

    plt.title('System Telemetry Timeline during Continuous Physical Workload')
    fig.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "telemetry_timeline.svg"), format='svg')
    plt.close()

    # 2. Query Latency Timeline SVG
    print("Generating query_latency_timeline.svg...")
    plt.figure(figsize=(15, 6))
    
    sns.scatterplot(data=queries, x='time_relative_min', y='query_duration_ms', hue='query_type', 
                    palette='viridis', alpha=0.6, s=50, edgecolor=None)
                    
    # Shade compaction regions again
    for (start, end) in compaction_blocks:
        plt.axvspan(start, end, color='gray', alpha=0.3, zorder=0)
        
    plt.yscale('log') # Use log scale because query latencies can spike hugely
    plt.xlabel('Time (Minutes)')
    plt.ylabel('Query Duration (ms) [Log Scale]')
    plt.title('Query Latency Timeline with Compaction Interference')
    
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "query_latency_timeline.svg"), format='svg')
    plt.close()

    # 3. Regime Distribution SVG
    print("Generating regime_distribution.svg...")
    plt.figure(figsize=(10, 6))
    
    regime_counts = queries['regime'].value_counts()
    
    # Bar chart of regime query counts
    sns.barplot(x=regime_counts.index, y=regime_counts.values, palette='Set2')
    plt.xlabel('NHPP Regime')
    plt.ylabel('Total Queries Executed')
    plt.title('Distribution of Physical Queries across NHPP Regimes')
    
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "regime_distribution.svg"), format='svg')
    plt.close()

    print("Successfully generated all SVGs.")

if __name__ == "__main__":
    generate_visualizations()
