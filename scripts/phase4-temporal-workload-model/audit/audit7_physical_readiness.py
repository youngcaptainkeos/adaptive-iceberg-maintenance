import os
import csv

def run_audit7():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    out_dir = os.path.join(base_dir, "results")
    
    readiness = [
        {"Phenomenon": "Persistent Iceberg State", "Status": "Ready", "Constraint": "None", "Can_Measure": "Yes"},
        {"Phenomenon": "Evolving Fragmentation", "Status": "Ready", "Constraint": "Depends on Workload Write Intensity", "Can_Measure": "Yes"},
        {"Phenomenon": "Continuous Query Arrivals", "Status": "Ready", "Constraint": "Managed by NHPP simulator", "Can_Measure": "Yes"},
        {"Phenomenon": "Workload Transitions", "Status": "Ready", "Constraint": "Regimes will cycle multiple times over 4-8h", "Can_Measure": "Yes"},
        {"Phenomenon": "Real Spark Telemetry", "Status": "Ready", "Constraint": "Needs robust REST API parsing in global daemon", "Can_Measure": "Yes"},
        {"Phenomenon": "Real Compaction Events", "Status": "Ready", "Constraint": "Requires programmatic trigger threshold", "Can_Measure": "Yes"},
        {"Phenomenon": "Overlap (Interference)", "Status": "Ready", "Constraint": "Requires queries to be queued/running during compaction", "Can_Measure": "Yes"},
        {"Phenomenon": "Unified Timestamps", "Status": "Ready", "Constraint": "Time.time() epoch in Python Daemon", "Can_Measure": "Yes"},
        {"Phenomenon": "Hardware Cache State", "Status": "Cannot Measure", "Constraint": "OS level caches (page cache) are unobservable directly", "Can_Measure": "No"},
        {"Phenomenon": "Network Latency Fluctuations", "Status": "Cannot Measure", "Constraint": "Not instrumented in daemon", "Can_Measure": "No"}
    ]
    
    csv_path = os.path.join(out_dir, "physical_experiment_readiness.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=readiness[0].keys())
        writer.writeheader()
        writer.writerows(readiness)
        
    print(f"Audit 7 CSV saved to {csv_path}")

    # Generate SVG
    svg_path = os.path.join(out_dir, "physical_experiment_readiness.svg")
    width = 1000
    height = 50 + len(readiness) * 40
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.yes { fill: #27ae60; }\n')
        f.write('.no { fill: #c0392b; }\n')
        f.write('.text { font-family: Arial; font-size: 13px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 16px; font-weight: bold; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="30" class="title">Audit 7: Physical Experiment Phenomenological Readiness</text>\n')
        
        y = 60
        for r in readiness:
            f.write(f'<text x="20" y="{y+15}" class="text">{r["Phenomenon"]}</text>\n')
            
            cls = "yes" if r["Can_Measure"] == "Yes" else "no"
            f.write(f'<rect x="250" y="{y}" width="100" height="22" rx="4" class="{cls}"/>\n')
            f.write(f'<text x="255" y="{y+15}" class="text" fill="white">Measure: {r["Can_Measure"]}</text>\n')
            
            f.write(f'<text x="370" y="{y+15}" class="text">Constraint: {r["Constraint"]}</text>\n')
            y += 40
            
        f.write('</svg>\n')
    print(f"Audit 7 SVG saved to {svg_path}")

if __name__ == "__main__":
    run_audit7()
