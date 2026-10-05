import os
import csv

def assign_roles():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    
    datasets = [
        {
            "phase": "Phase 2 Validation Layout Comparison",
            "file": "paired_state_differences.csv",
            "role": "Calibration",
            "justification": "Provides ground-truth baseline un-interfered query latencies needed to compute QIR for new physical runs. Unusable for temporal training due to discrete non-chronological execution."
        },
        {
            "phase": "Phase 3B Predictive Signals",
            "file": "phase3b_system_metrics.csv",
            "role": "Feature Engineering Validation",
            "justification": "Useful to test parsing and aggregation logic for OS system metrics (CPU/Mem), but unusable for temporal model training because the timeline is interrupted and lacks continuous workload variations."
        },
        {
            "phase": "Phase 3C Uncertainty Aware Scheduler",
            "file": "policy_decisions.csv",
            "role": "Unusable",
            "justification": "Decisions were made using a static lookback that inherently leaked future targets (simulated execution). Timestamps are logical windows, not physical clock ticks."
        },
        {
            "phase": "Phase 3D Validation Generalization",
            "file": "ood_system_metrics.csv",
            "role": "Validation (Independent)",
            "justification": "Can be used as a static out-of-distribution (OOD) test set to verify if the Phase 4 temporal model generalizes to the static 750-file state, but cannot be used for sequence training."
        },
        {
            "phase": "Phase 3-Concurrent Interference",
            "file": "task_telemetry.csv",
            "role": "Feature Engineering Validation",
            "justification": "Used strictly to validate that the new Unified Logger is calculating executor_cpu_time_ms correctly. Cannot be concatenated for temporal ML training."
        }
    ]
    
    csv_path = os.path.join(base_dir, "results/dataset_role_assignment.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["phase", "file", "role", "justification"])
        writer.writeheader()
        writer.writerows(datasets)
        
    print(f"Dataset roles written to {csv_path}")
    
    # Generate Visualization SVG
    svg_path = os.path.join(base_dir, "results/dataset_role_assignment.svg")
    width = 800
    height = 50 + len(datasets) * 60
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.text { font-family: Arial; font-size: 13px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 18px; font-weight: bold; }\n')
        f.write('.role { font-family: Arial; font-size: 12px; font-weight: bold; fill: #fff; }\n')
        f.write('.Calibration { fill: #36A2EB; }\n')
        f.write('.Feature { fill: #4BC0C0; }\n')
        f.write('.Unusable { fill: #FF6384; }\n')
        f.write('.Validation { fill: #9966FF; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="30" class="title">Dataset Role Assignment for Phase 4</text>\n')
        
        y = 60
        for d in datasets:
            f.write(f'<text x="20" y="{y+15}" class="text">{d["phase"]} ({d["file"]})</text>\n')
            
            # Draw role pill
            role_short = d['role'].split()[0] # e.g. Calibration, Feature, Unusable, Validation
            color_class = role_short
            if role_short not in ["Calibration", "Feature", "Unusable", "Validation"]: color_class = "Unusable"
            
            f.write(f'<rect x="400" y="{y}" width="150" height="22" rx="10" class="{color_class}"/>\n')
            f.write(f'<text x="410" y="{y+15}" class="role">{d["role"]}</text>\n')
            
            y += 50
            
        f.write('</svg>\n')
    print(f"SVG written to {svg_path}")


if __name__ == "__main__":
    assign_roles()
