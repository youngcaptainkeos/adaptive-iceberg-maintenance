import pandas as pd
import numpy as np
import os
import argparse
import matplotlib.pyplot as plt
import seaborn as sns

def build_temporal_windows(telemetry_path, queries_path, output_csv, output_svg):
    print("Loading datasets...")
    tel_df = pd.read_csv(telemetry_path)
    q_df = pd.read_csv(queries_path)
    
    # 1. Prepare Telemetry (1Hz)
    tel_df['timestamp'] = tel_df['timestamp'].astype(float)
    tel_df['timestamp'] = np.round(tel_df['timestamp']).astype(int) # align to exact second
    tel_df = tel_df.groupby('timestamp').mean().reset_index() # in case of duplicates
    tel_df = tel_df.sort_values('timestamp')
    
    # 2. Extract targets from Queries
    # We want to know for each second t, what is the average duration of queries that START in [t, t+300]
    q_df['query_start_time'] = np.round(q_df['query_start_time'].astype(float)).astype(int)
    
    print("Computing Rolling Features (k=60s)...")
    # Features to compute rolling stats on
    feat_cols = ['cpu_utilization_pct', 'memory_used_pct', 'disk_read_iops', 'disk_write_iops']
    
    # We will iterate through the telemetry timeline to build the dataset
    dataset = []
    
    # Convert queries to a fast lookup
    # Group by start time to get mean duration for queries starting at that exact second
    q_grouped = q_df.groupby('query_start_time')['query_duration_ms'].mean().to_dict()
    
    min_t = tel_df['timestamp'].min()
    max_t = tel_df['timestamp'].max()
    
    tel_indexed = tel_df.set_index('timestamp')
    
    # Pre-compute rolling means on telemetry
    for col in feat_cols:
        tel_indexed[f'{col}_mean_60s'] = tel_indexed[col].rolling(window=60, min_periods=10).mean()
        tel_indexed[f'{col}_std_60s'] = tel_indexed[col].rolling(window=60, min_periods=10).std()
        
    tel_indexed = tel_indexed.reset_index()
    
    print("Computing Forward Targets (h=300s) and aligning...")
    
    # Calculate target using a moving window over queries
    # To do this efficiently, we can create a time series of query durations for every second
    target_ts = pd.Series(index=range(min_t, max_t + 1), dtype=float).fillna(0)
    for t_val, dur in q_grouped.items():
        if min_t <= t_val <= max_t:
            target_ts[t_val] = dur
            
    # Forward rolling mean of 300 seconds
    # To do forward rolling, we reverse, do normal rolling, then reverse back
    target_ts_reversed = target_ts[::-1]
    target_rolling_rev = target_ts_reversed.rolling(window=300, min_periods=1).mean()
    target_rolling = target_rolling_rev[::-1]
    
    # Align to telemetry
    tel_indexed['target_avg_query_duration_300s'] = tel_indexed['timestamp'].map(target_rolling)
    
    # Drop NaNs (due to min_periods in rolling, and the end of the dataset)
    # Actually, we shouldn't use the last 300 seconds as training data because the target is truncated
    tel_indexed = tel_indexed[tel_indexed['timestamp'] <= (max_t - 300)]
    tel_indexed = tel_indexed.dropna()
    
    print(f"Total temporal windows generated: {len(tel_indexed)}")
    
    # 3. Chronological Split (70 / 15 / 15)
    n = len(tel_indexed)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)
    
    tel_indexed['split'] = 'test'
    tel_indexed.iloc[:train_end, tel_indexed.columns.get_loc('split')] = 'train'
    tel_indexed.iloc[train_end:val_end, tel_indexed.columns.get_loc('split')] = 'val'
    
    print(f"Split sizes -> Train: {train_end}, Val: {val_end-train_end}, Test: {n-val_end}")
    
    tel_indexed.to_csv(output_csv, index=False)
    print(f"Saved temporal windows to {output_csv}")
    
    # 4. Generate SVG Distribution overlay (Train vs Test)
    print("Generating rolling_feature_distributions.svg...")
    plt.figure(figsize=(15, 5))
    
    plot_feats = ['cpu_utilization_pct_mean_60s', 'disk_read_iops_mean_60s', 'target_avg_query_duration_300s']
    titles = ['CPU Mean (60s)', 'Disk Read IOPS Mean (60s)', 'Target Query Duration (300s)']
    
    for i, (feat, title) in enumerate(zip(plot_feats, titles)):
        plt.subplot(1, 3, i+1)
        sns.kdeplot(data=tel_indexed[tel_indexed['split'] == 'train'], x=feat, label='Train (First 70%)', fill=True, alpha=0.5)
        sns.kdeplot(data=tel_indexed[tel_indexed['split'] == 'test'], x=feat, label='Test (Last 15%)', fill=True, alpha=0.5)
        plt.title(title)
        if i == 0:
            plt.legend()
            
    plt.tight_layout()
    plt.savefig(output_svg, format='svg')
    plt.close()
    print(f"Saved {output_svg}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model/results/physical_telemetry.csv")
    parser.add_argument("--queries", type=str, default="/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model/results/physical_queries.csv")
    args = parser.parse_args()
    
    base_dir = os.path.dirname(args.input)
    out_csv = os.path.join(base_dir, "temporal_windows.csv")
    out_svg = os.path.join(base_dir, "rolling_feature_distributions.svg")
    
    build_temporal_windows(args.input, args.queries, out_csv, out_svg)
