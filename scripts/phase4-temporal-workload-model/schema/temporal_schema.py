import os
import csv
import textwrap

def design_schema():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    
    # Define Schema
    schema = [
        {"column": "timestamp", "category": "CLOCK", "type": "float", "description": "Global synchronized clock epoch (seconds)"},
        
        # TABLE STATE
        {"column": "num_files", "category": "TABLE STATE", "type": "int", "description": "Total data files in Iceberg table"},
        {"column": "avg_file_size_mb", "category": "TABLE STATE", "type": "float", "description": "Average size of data files"},
        {"column": "total_table_size_mb", "category": "TABLE STATE", "type": "float", "description": "Total size of table"},
        {"column": "fragmentation_level", "category": "TABLE STATE", "type": "float", "description": "Ratio of small files to total files"},
        {"column": "files_created_since_prev", "category": "TABLE STATE", "type": "int", "description": "Files added in last dt"},
        {"column": "maintenance_debt", "category": "TABLE STATE", "type": "float", "description": "Estimated compaction work required"},
        {"column": "time_since_last_compaction_s", "category": "TABLE STATE", "type": "float", "description": "Seconds since last compaction ended"},
        
        # WORKLOAD STATE
        {"column": "query_arrival_rate_hz", "category": "WORKLOAD STATE", "type": "float", "description": "Arrivals per second in dt"},
        {"column": "queries_started", "category": "WORKLOAD STATE", "type": "int", "description": "Queries launched in dt"},
        {"column": "queries_completed", "category": "WORKLOAD STATE", "type": "int", "description": "Queries finished in dt"},
        {"column": "active_queries", "category": "WORKLOAD STATE", "type": "int", "description": "Queries running at end of dt"},
        {"column": "queued_queries", "category": "WORKLOAD STATE", "type": "int", "description": "Queries waiting for admission"},
        {"column": "read_queries", "category": "WORKLOAD STATE", "type": "int", "description": "Number of read queries active"},
        {"column": "write_update_queries", "category": "WORKLOAD STATE", "type": "int", "description": "Number of update queries active"},
        {"column": "workload_intensity", "category": "WORKLOAD STATE", "type": "float", "description": "Normalized intensity metric (0.0 - 1.0)"},
        
        # SYSTEM STATE
        {"column": "cpu_utilization_pct", "category": "SYSTEM STATE", "type": "float", "description": "Global CPU utilization"},
        {"column": "memory_utilization_pct", "category": "SYSTEM STATE", "type": "float", "description": "Global RAM utilization"},
        {"column": "active_spark_tasks", "category": "SYSTEM STATE", "type": "int", "description": "Spark tasks actively computing"},
        {"column": "queued_spark_tasks", "category": "SYSTEM STATE", "type": "int", "description": "Spark tasks pending resources"},
        
        # MAINTENANCE STATE
        {"column": "compaction_active", "category": "MAINTENANCE STATE", "type": "int", "description": "Boolean: 1 if compaction is running, else 0"},
        {"column": "compaction_elapsed_time_s", "category": "MAINTENANCE STATE", "type": "float", "description": "Time since current compaction started"},
        {"column": "files_being_compacted", "category": "MAINTENANCE STATE", "type": "int", "description": "Number of files targeted by active compaction"},
        
        # TEMPORAL FEATURES (Engineered via lookback k)
        {"column": "rolling_query_rate_k", "category": "TEMPORAL FEATURES", "type": "float", "description": "Average query arrival over lookback k"},
        {"column": "workload_acceleration_k", "category": "TEMPORAL FEATURES", "type": "float", "description": "Derivative of query rate over k"},
        {"column": "recent_fragmentation_growth_k", "category": "TEMPORAL FEATURES", "type": "float", "description": "Growth rate of small files over k"},
        
        # TARGET VARIABLES (Future horizons h)
        {"column": "target_y1_future_qir_h", "category": "TARGETS", "type": "float", "description": "Avg Query Interference Ratio over horizon h"},
        {"column": "target_y5_interference_cost", "category": "TARGETS", "type": "float", "description": "Total latency penalty over horizon h"}
    ]
    
    csv_path = os.path.join(base_dir, "results/temporal_schema.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["column", "category", "type", "description"])
        writer.writeheader()
        writer.writerows(schema)
        
    md_path = os.path.join(base_dir, "reports/temporal_target_design.md")
    with open(md_path, 'w') as f:
        f.write("# Phase 4 Temporal Target & Schema Design\n\n")
        
        f.write("## 1. Temporal Resolution ($\\Delta t$)\n")
        f.write("We have evaluated 1s, 5s, 10s, 30s, and 60s resolutions. \n")
        f.write("**Selection**: **$\\Delta t = 5$ seconds**\n")
        f.write("**Justification**: Query and task lifespans in Spark often range from 2 to 15 seconds. A 1-second resolution introduces excessive noise from the OS polling jitter and Spark REST API latency. Resolutions >= 10 seconds risk 'missing' the start and end of micro-queries within a single window, severely blurring the temporal sequence. 5 seconds provides a crisp, responsive signal without the high-frequency jitter.\n\n")
        
        f.write("## 2. Forecasting Target Evaluation\n")
        f.write("The fundamental question is: *'When should Iceberg compaction be performed?'*\n")
        f.write("We evaluate the following candidate targets ($Y_{t+h}$):\n\n")
        
        f.write("### Target Y1: Future QIR / Interference over horizon $h$\n")
        f.write("- **Pros**: Direct measure of the penalty if compaction is executed. QIR isolates interference from natural workload fluctuations.\n")
        f.write("- **Cons**: Requires knowing the baseline uncontended runtime to calculate QIR.\n")
        
        f.write("### Target Y2: Probability future QIR exceeds SLA threshold\n")
        f.write("- **Pros**: Formulates as a standard binary classification problem.\n")
        f.write("- **Cons**: Destroys the magnitude of the violation. A 105% SLA violation is treated identically to a 400% SLA violation, limiting policy utility.\n")
        
        f.write("### Target Y3: Future Workload Intensity\n")
        f.write("- **Pros**: Easy to forecast from pure arrival traces.\n")
        f.write("- **Cons**: Forecasting workload intensity does not directly answer 'what is the compaction cost?'. High intensity does not automatically mean high interference if the queries are fully disjoint from the compaction dataset.\n")
        
        f.write("### Target Y4: Whether the next window is 'safe' for compaction\n")
        f.write("- **Pros**: Direct policy action.\n")
        f.write("- **Cons**: Circular definition. 'Safe' depends on a heuristic threshold, forcing the ML model to learn the heuristic rather than the physical reality.\n")
        
        f.write("### Target Y5: Future Compaction Interference Cost\n")
        f.write("- **Pros**: Quantifies total system degradation mathematically.\n")
        f.write("- **Cons**: Can be noisy if task variance is high.\n\n")
        
        f.write("## 3. Scientific Target Selection\n")
        f.write("**Selection**: **Target Y1 (Future QIR over horizon $h$)**.\n")
        f.write("**Justification**: To decide *when* to compact, the agent must weigh the *reward* (reduced future fragmentation) against the *cost* (immediate interference penalty). Y1 directly models the cost. By predicting the continuous QIR degradation over horizon $h$, a downstream policy can mathematically optimize the exact trade-off threshold.\n")
        
    print(f"Schema written to {csv_path}, Design doc written to {md_path}")

    # Generate Visualization: A simple feature category distribution pie chart SVG
    svg_path = os.path.join(base_dir, "results/temporal_schema_distribution.svg")
    
    categories = {}
    for row in schema:
        categories[row['category']] = categories.get(row['category'], 0) + 1
        
    width = 600
    height = 300
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.text { font-family: Arial; font-size: 14px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 18px; font-weight: bold; }\n')
        f.write('</style>\n')
        f.write(f'<text x="20" y="30" class="title">Schema Feature Categories</text>\n')
        
        y_offset = 60
        for i, (cat, count) in enumerate(categories.items()):
            color = colors[i % len(colors)]
            f.write(f'<rect x="20" y="{y_offset}" width="{count*20}" height="25" fill="{color}"/>\n')
            f.write(f'<text x="{30 + count*20}" y="{y_offset + 17}" class="text">{cat} ({count} features)</text>\n')
            y_offset += 40
            
        f.write('</svg>\n')
    print(f"SVG written to {svg_path}")

if __name__ == "__main__":
    design_schema()
