import os
import csv
import math

def get_corr(x_vals, y_vals):
    n = len(x_vals)
    if n == 0: return 0
    mean_x = sum(x_vals) / n
    mean_y = sum(y_vals) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals))
    den_x = sum((x - mean_x) ** 2 for x in x_vals)
    den_y = sum((y - mean_y) ** 2 for y in y_vals)
    if den_x == 0 or den_y == 0: return 0
    return num / math.sqrt(den_x * den_y)

def audit_leakage():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    log_path = os.path.join(base_dir, "results/temporal_windows.csv")
    
    if not os.path.exists(log_path):
        print("Temporal windows not found. Run pilot first.")
        return
        
    with open(log_path, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
        
    features = ['rolling_cpu_5m', 'rolling_query_rate_5m', 'current_cpu', 'compaction_active']
    target = 'target_future_interference_h5'
    
    leakage_risks = []
    
    for f in features:
        x_vals = [float(row[f]) for row in data]
        y_vals = [float(row[target]) for row in data]
        
        corr = get_corr(x_vals, y_vals)
        if abs(corr) > 0.95:
            leakage_risks.append((f, corr, "HIGH RISK - Possible Overlap"))
        elif corr == 0.0:
            leakage_risks.append((f, corr, "NO VARIANCE"))
        else:
            leakage_risks.append((f, corr, "SAFE"))
            
    csv_path = os.path.join(base_dir, "results/leakage_audit.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Feature", "Pearson Correlation to Target", "Status"])
        for risk in leakage_risks:
            writer.writerow(risk)
            
    print(f"Leakage audit complete. Results saved to {csv_path}")

    # Generate Visualization of Correlation
    svg_path = os.path.join(base_dir, "results/leakage_correlation.svg")
    width = 600
    height = 50 + len(features) * 40
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.bar { fill: #3498db; }\n')
        f.write('.safe { fill: #2ecc71; }\n')
        f.write('.danger { fill: #e74c3c; }\n')
        f.write('.text { font-family: Arial; font-size: 12px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 16px; font-weight: bold; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="30" class="title">Feature-Target Leakage Correlation Analysis</text>\n')
        
        y = 60
        for f_name, corr, status in leakage_risks:
            f.write(f'<text x="20" y="{y+15}" class="text">{f_name}</text>\n')
            
            cls = "danger" if status == "HIGH RISK - Possible Overlap" else "safe"
            w = abs(corr) * 200
            
            f.write(f'<rect x="250" y="{y}" width="{w}" height="20" class="{cls}"/>\n')
            f.write(f'<text x="{255 + w}" y="{y+15}" class="text">{corr:.3f}</text>\n')
            y += 40
            
        f.write('</svg>\n')

if __name__ == "__main__":
    audit_leakage()
