import os
import csv

def run_audit1():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    out_dir = os.path.join(base_dir, "results")
    os.makedirs(out_dir, exist_ok=True)
    
    components = [
        {"Component": "Query Arrival Timings", "Provenance": "Simulated (NHPP)", "Pilot_Status": "Simulated", "Physical_Status": "Simulated (Trace-driven)", "Validation_Target": "Temporal Pipeline Logic"},
        {"Component": "Query Execution Engine", "Provenance": "Mock (Pilot)", "Pilot_Status": "Simulated", "Physical_Status": "Physical (Spark SQL)", "Validation_Target": "Temporal Pipeline Logic"},
        {"Component": "Table Fragmentation State", "Provenance": "Mock (Pilot)", "Pilot_Status": "Simulated", "Physical_Status": "Physical (Iceberg Metadata)", "Validation_Target": "Temporal Pipeline Logic"},
        {"Component": "System CPU Metrics", "Provenance": "Mock (Pilot)", "Pilot_Status": "Simulated", "Physical_Status": "Physical (psutil)", "Validation_Target": "Temporal Pipeline Logic"},
        {"Component": "Compaction Action", "Provenance": "Mock (Pilot)", "Pilot_Status": "Simulated", "Physical_Status": "Physical (Spark Action)", "Validation_Target": "Temporal Pipeline Logic"},
        {"Component": "Global Telemetry Daemon", "Provenance": "Physical (Python Thread)", "Pilot_Status": "Physical", "Physical_Status": "Physical", "Validation_Target": "Synchronization Integrity"},
        {"Component": "Window Construction", "Provenance": "Physical (Algorithm)", "Pilot_Status": "Physical", "Physical_Status": "Physical", "Validation_Target": "Dataset Extraction Logic"}
    ]
    
    csv_path = os.path.join(out_dir, "pilot_provenance.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=components[0].keys())
        writer.writeheader()
        writer.writerows(components)
        
    print(f"Audit 1 CSV saved to {csv_path}")

    # Generate SVG
    svg_path = os.path.join(out_dir, "pilot_provenance.svg")
    width = 900
    height = 50 + len(components) * 40
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.sim { fill: #f39c12; }\n')
        f.write('.phys { fill: #27ae60; }\n')
        f.write('.text { font-family: Arial; font-size: 13px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 16px; font-weight: bold; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="30" class="title">Audit 1: Pilot vs Physical Provenance Mapping</text>\n')
        
        y = 60
        for comp in components:
            f.write(f'<text x="20" y="{y+15}" class="text">{comp["Component"]}</text>\n')
            
            # Pilot Status
            pilot_cls = "phys" if "Physical" in comp["Pilot_Status"] else "sim"
            f.write(f'<rect x="250" y="{y}" width="100" height="22" rx="4" class="{pilot_cls}"/>\n')
            f.write(f'<text x="255" y="{y+15}" class="text" fill="white">Pilot: {comp["Pilot_Status"][:4]}</text>\n')
            
            # Physical Status
            phys_cls = "phys" if "Physical" in comp["Physical_Status"] else "sim"
            f.write(f'<rect x="360" y="{y}" width="200" height="22" rx="4" class="{phys_cls}"/>\n')
            f.write(f'<text x="365" y="{y+15}" class="text" fill="white">Target: {comp["Physical_Status"]}</text>\n')
            
            f.write(f'<text x="580" y="{y+15}" class="text">Validates: {comp["Validation_Target"]}</text>\n')
            y += 40
            
        f.write('</svg>\n')
    print(f"Audit 1 SVG saved to {svg_path}")

if __name__ == "__main__":
    run_audit1()
