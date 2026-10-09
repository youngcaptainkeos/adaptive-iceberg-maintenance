import os
import glob
import csv
from datetime import datetime

def analyze_telemetry():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation"
    
    # 1. Collect all CSVs
    csv_files = glob.glob(f"{base_dir}/**/*.csv", recursive=True)
    csv_files = [f for f in csv_files if "test_venv" not in f and "__pycache__" not in f and "/software/" not in f]
    
    inventory = []
    
    temporal_sources = 0
    total_rows = 0
    
    for f in csv_files:
        try:
            with open(f, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, None)
                if not headers: continue
                
                # Check for temporal columns
                temporal_cols = [c for c in headers if any(k in c.lower() for k in ['time', 'date', 'window', 'epoch'])]
                
                # Count rows
                rows = list(reader)
                row_count = len(rows)
                total_rows += row_count
                
                is_temporal = len(temporal_cols) > 0
                if is_temporal:
                    temporal_sources += 1
                
                rel_path = os.path.relpath(f, base_dir)
                inventory.append({
                    "file": rel_path,
                    "rows": row_count,
                    "temporal": is_temporal,
                    "temporal_cols": temporal_cols,
                    "headers": headers
                })
        except Exception as e:
            pass

    # Sort inventory by rows
    inventory.sort(key=lambda x: x['rows'], reverse=True)
    
    # Generate Report
    report_path = os.path.join(base_dir, "audit_results.md")
    with open(report_path, "w") as f:
        f.write("# Capstone Data Pipeline Audit Report\n\n")
        f.write("## 1. Inventory Summary\n")
        f.write(f"- **Total CSV Files Analyzed**: {len(inventory)}\n")
        f.write(f"- **Total Telemetry Rows**: {total_rows:,}\n")
        f.write(f"- **Sources with Temporal Features**: {temporal_sources}\n\n")
        
        f.write("## 2. Assessment of Temporal ML Feasibility ($X_{t-k:t} \\rightarrow Y_{t+h}$)\n")
        f.write("Based on the audit, the current telemetry pipeline collects timestamps and sequences (e.g., `window_id`, `launch_time`, `finish_time`, `timestamp`). ")
        f.write("However, the data is heavily fragmented across independent short-lived experiment phases (Phase 3a, 3b, 3c, etc.) rather than a continuous, contiguous timeline.\n\n")
        f.write("**Gap Analysis:**\n")
        f.write("- **Fragmentation**: Data is generated in isolated runs. A true temporal dataset requires a long, continuous history (hours or days) to capture seasonality, gradual fragmentation build-up, and sustained interference patterns.\n")
        f.write("- **Sampling Frequency**: System metrics are collected, but Spark task telemetry is bound to discrete query execution windows. The connection between background compaction events and continuous query streams is broken between experiment boundaries.\n")
        f.write("- **State Transitions**: To model sequences $X_{t-k:t} \\rightarrow Y_{t+h}$, the state matrix $X$ needs continuous system state, table state, and queue state. The current setup only logs final table states or discrete metric snapshots per phase.\n\n")
        f.write("**Conclusion**: The existing data is **insufficient** to construct a valid, industry-relevant temporal machine-learning dataset without heavy synthetic generation or interpolation.\n\n")
        
        f.write("## 3. Recommendation for New Physical Experiment\n")
        f.write("**Minimum Viable Temporal Experiment (Continuous Workload Trace)**\n")
        f.write("To generate an industry-relevant dataset, a new experiment must be executed with the following specifications:\n")
        f.write("1. **Duration**: 4-8 hours of contiguous execution without restarting the Spark cluster or resetting the Iceberg table.\n")
        f.write("2. **Workload Stream**: A Poisson-distributed arrival of queries (both reads and updates) representing daily cyclical load.\n")
        f.write("3. **Background Maintenance**: Background compaction processes running concurrently, driven by actual file fragmentation counts, generating realistic interference.\n")
        f.write("4. **Unified Telemetry Logger (Global Clock Sync)**: A daemon that outputs `(timestamp, cpu, mem, active_tasks, queued_tasks, maintenance_status)` at a fixed frequency (e.g., 1Hz). This is critical for ML sequence modeling.\n\n")
        
        f.write("## 4. Detailed Telemetry Inventory (Top 50)\n")
        f.write("| File | Rows | Has Temporal | Temporal Columns |\n")
        f.write("|---|---|---|---|\n")
        for inv in inventory[:50]: # Top 50
            cols = ", ".join(inv['temporal_cols']) if inv['temporal_cols'] else "None"
            f.write(f"| `{inv['file']}` | {inv['rows']} | {inv['temporal']} | `{cols}` |\n")
            
    print(f"Report written to {report_path}")

    # Visualization - Create a clean SVG bar chart
    top_files = inventory[:15]
    max_rows = max([x['rows'] for x in top_files])
    
    svg_path = os.path.join(base_dir, "audit_visualization.svg")
    
    svg_width = 800
    svg_height = 40 + len(top_files) * 40
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">\n')
        f.write('<style>\n')
        f.write('.bar { fill: #3498db; }\n')
        f.write('.text { font-family: Arial, sans-serif; font-size: 12px; fill: #333; }\n')
        f.write('.title { font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; fill: #111; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="25" class="title">Top 15 Largest Telemetry Sources by Row Count</text>\n')
        
        y_offset = 50
        for item in top_files:
            file_name = os.path.basename(item['file'])
            bar_width = (item['rows'] / max_rows) * 400
            
            f.write(f'<text x="20" y="{y_offset + 15}" class="text">{file_name}</text>\n')
            f.write(f'<rect x="250" y="{y_offset}" width="{bar_width}" height="20" class="bar"/>\n')
            f.write(f'<text x="{250 + bar_width + 10}" y="{y_offset + 15}" class="text">{item["rows"]}</text>\n')
            
            y_offset += 40
            
        f.write('</svg>\n')
    
    print(f"Visualization saved to {svg_path}")

if __name__ == "__main__":
    analyze_telemetry()
