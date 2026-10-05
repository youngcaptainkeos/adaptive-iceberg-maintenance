import os
import csv

def run_audit3():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    out_dir = os.path.join(base_dir, "results")
    
    # 5 Target Definitions
    targets = [
        {"Target": "1. Point QIR at t+h", "Representativeness": "Low", "Noise_Susceptibility": "High", "Actionability": "Low", "Verdict": "Rejected (Ignores interval cost)"},
        {"Target": "2. Mean QIR over [t, t+h]", "Representativeness": "High", "Noise_Susceptibility": "Low", "Actionability": "High", "Verdict": "SELECTED (Captures total degradation)"},
        {"Target": "3. Max QIR over [t, t+h]", "Representativeness": "Moderate", "Noise_Susceptibility": "High", "Actionability": "Moderate", "Verdict": "Rejected (Over-penalizes brief anomalies)"},
        {"Target": "4. 95th Percentile QIR", "Representativeness": "Moderate", "Noise_Susceptibility": "Moderate", "Actionability": "Moderate", "Verdict": "Rejected (Too conservative for proactive thresholding)"},
        {"Target": "5. SLA Violation Indicator", "Representativeness": "Low", "Noise_Susceptibility": "Low", "Actionability": "Moderate", "Verdict": "Rejected (Binary loss destroys magnitude gradients)"}
    ]
    
    csv_path = os.path.join(out_dir, "temporal_target_comparison.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=targets[0].keys())
        writer.writeheader()
        writer.writerows(targets)
        
    print(f"Audit 3 CSV saved to {csv_path}")
    
    # Generate MD Report
    md_path = os.path.join(base_dir, "reports/temporal_target_decision.md")
    with open(md_path, 'w') as f:
        f.write("# Audit 3: Target Definition Decision\n\n")
        f.write("## Objective\nDetermine which definition of Future QIR best answers the policy question: *'Will compaction initiated now interfere with the upcoming workload?'*\n\n")
        
        f.write("## Candidate Evaluation\n")
        for t in targets:
            f.write(f"### {t['Target']}\n")
            f.write(f"- **Representativeness**: {t['Representativeness']}\n")
            f.write(f"- **Noise Susceptibility**: {t['Noise_Susceptibility']}\n")
            f.write(f"- **Verdict**: {t['Verdict']}\n\n")
            
        f.write("## Scientific Conclusion\n")
        f.write("We formally select **Option 2: Mean QIR over [t, t+h]**. Compaction is a long-running process (often spanning minutes). Point metrics or maxima fail to capture the integral of the degradation penalty across the entire compaction window. The Mean QIR directly correlates to total latency cost, providing a continuous loss surface for the model to learn from.\n")
        
    print(f"Audit 3 MD saved to {md_path}")

    # Generate SVG
    svg_path = os.path.join(out_dir, "temporal_target_comparison.svg")
    width = 900
    height = 50 + len(targets) * 40
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.sel { fill: #27ae60; }\n')
        f.write('.rej { fill: #c0392b; }\n')
        f.write('.text { font-family: Arial; font-size: 13px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 16px; font-weight: bold; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="30" class="title">Audit 3: Target Selection Analysis</text>\n')
        
        y = 60
        for t in targets:
            f.write(f'<text x="20" y="{y+15}" class="text">{t["Target"]}</text>\n')
            
            cls = "sel" if "SELECTED" in t["Verdict"] else "rej"
            w = 120 if "SELECTED" in t["Verdict"] else 120
            
            f.write(f'<rect x="250" y="{y}" width="{w}" height="22" rx="4" class="{cls}"/>\n')
            f.write(f'<text x="255" y="{y+15}" class="text" fill="white">{t["Verdict"][:8]}</text>\n')
            
            f.write(f'<text x="390" y="{y+15}" class="text">Repr: {t["Representativeness"]} | Noise: {t["Noise_Susceptibility"]}</text>\n')
            y += 40
            
        f.write('</svg>\n')
    print(f"Audit 3 SVG saved to {svg_path}")

if __name__ == "__main__":
    run_audit3()
