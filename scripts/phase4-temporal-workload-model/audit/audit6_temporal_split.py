import os
import csv

def run_audit6():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    out_dir = os.path.join(base_dir, "results")
    
    splits = [
        {"Protocol": "A. Random Window Split", "Leakage_Risk": "Extreme", "Temporal_Realism": "None", "Verdict": "Rejected (Lookback overlaps)"},
        {"Protocol": "B. Chronological Split (e.g. 70/15/15)", "Leakage_Risk": "None", "Temporal_Realism": "High", "Verdict": "SELECTED (Strict timeline preservation)"},
        {"Protocol": "C. Blocked Temporal Split (k-fold time series)", "Leakage_Risk": "Moderate", "Temporal_Realism": "Moderate", "Verdict": "Rejected (Requires discarding gap buffers)"},
        {"Protocol": "D. Episode-Level Split", "Leakage_Risk": "None", "Temporal_Realism": "Very High", "Verdict": "Secondary/Optional (Depends on distinct episodes)"},
        {"Protocol": "E. Future-Distribution Shift Test", "Leakage_Risk": "None", "Temporal_Realism": "Extreme", "Verdict": "Recommended for Final Holdout"}
    ]
    
    csv_path = os.path.join(out_dir, "temporal_split_design.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=splits[0].keys())
        writer.writeheader()
        writer.writerows(splits)
        
    print(f"Audit 6 CSV saved to {csv_path}")

    # Generate SVG
    svg_path = os.path.join(out_dir, "temporal_split_design.svg")
    width = 1100
    height = 50 + len(splits) * 40
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.sel { fill: #27ae60; }\n')
        f.write('.rej { fill: #c0392b; }\n')
        f.write('.warn { fill: #f39c12; }\n')
        f.write('.text { font-family: Arial; font-size: 13px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 16px; font-weight: bold; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="30" class="title">Audit 6: Temporal Split Protocol Selection</text>\n')
        
        y = 60
        for s in splits:
            f.write(f'<text x="20" y="{y+15}" class="text">{s["Protocol"]}</text>\n')
            
            cls = "sel" if "SELECTED" in s["Verdict"] or "Recommended" in s["Verdict"] else ("warn" if "Optional" in s["Verdict"] else "rej")
            w = 250
            
            f.write(f'<rect x="350" y="{y}" width="{w}" height="22" rx="4" class="{cls}"/>\n')
            f.write(f'<text x="355" y="{y+15}" class="text" fill="white">{s["Verdict"]}</text>\n')
            
            f.write(f'<text x="620" y="{y+15}" class="text">Leakage Risk: {s["Leakage_Risk"]} | Realism: {s["Temporal_Realism"]}</text>\n')
            y += 40
            
        f.write('</svg>\n')
    print(f"Audit 6 SVG saved to {svg_path}")

if __name__ == "__main__":
    run_audit6()
