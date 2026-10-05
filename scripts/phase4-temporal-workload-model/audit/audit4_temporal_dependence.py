import os
import csv
import math

def get_autocorrelation(series, lag):
    n = len(series)
    if n <= lag: return 0
    mean = sum(series) / n
    var = sum((x - mean)**2 for x in series)
    if var == 0: return 0
    cov = sum((series[i] - mean) * (series[i+lag] - mean) for i in range(n - lag))
    return cov / var

def run_audit4():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    out_dir = os.path.join(base_dir, "results")
    
    # We will compute autocorrelation on the generated unified_telemetry_log.csv
    log_path = os.path.join(out_dir, "unified_telemetry_log.csv")
    if not os.path.exists(log_path):
        print("Log file missing. Run pilot first.")
        return
        
    with open(log_path, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
        
    cpu = [float(row['cpu_utilization_pct']) for row in data]
    n = len(cpu)
    
    # Calculate autocorrelations
    lags = [1, 5, 12, 60] # 5s, 25s, 1m, 5m
    acf = {lag: get_autocorrelation(cpu, lag) for lag in lags}
    
    # Effective Sample Size (ESS) using AR(1) approximation
    rho = acf[1]
    ess = n * ((1 - rho) / (1 + rho)) if rho < 1 else 1
    
    results = [
        {"Metric": "Total Rows (N)", "Value": f"{n}", "Interpretation": "Raw window count"},
        {"Metric": "Autocorrelation Lag 1 (5s)", "Value": f"{acf[1]:.3f}", "Interpretation": "High short-term dependence"},
        {"Metric": "Autocorrelation Lag 12 (1m)", "Value": f"{acf[12]:.3f}", "Interpretation": "Moderate medium-term dependence"},
        {"Metric": "Autocorrelation Lag 60 (5m)", "Value": f"{acf[60]:.3f}", "Interpretation": "Low long-term dependence"},
        {"Metric": "Effective Sample Size (ESS)", "Value": f"{ess:.1f}", "Interpretation": "True independent episode count"}
    ]
    
    csv_path = os.path.join(out_dir, "temporal_dependence_analysis.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        
    print(f"Audit 4 CSV saved to {csv_path}")

    # Generate SVG Correlogram
    svg_path = os.path.join(out_dir, "temporal_dependence_analysis.svg")
    width = 800
    height = 300
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.bar { fill: #9b59b6; }\n')
        f.write('.text { font-family: Arial; font-size: 12px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 16px; font-weight: bold; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="30" class="title">Audit 4: Autocorrelation (Temporal Dependence) of CPU</text>\n')
        f.write(f'<text x="20" y="50" class="text">ESS (Effective Sample Size): {ess:.1f} independent episodes out of {n} rows</text>\n')
        
        # Plot ACF
        for i, lag in enumerate(lags):
            x = 100 + i * 150
            h = abs(acf[lag]) * 150
            y = 250 - h
            f.write(f'<rect x="{x}" y="{y}" width="40" height="{h}" class="bar"/>\n')
            f.write(f'<text x="{x}" y="270" class="text">Lag {lag}</text>\n')
            f.write(f'<text x="{x}" y="{y-10}" class="text">{acf[lag]:.2f}</text>\n')
            
        f.write('<line x1="50" y1="250" x2="750" y2="250" stroke="#333" stroke-width="1"/>\n')
        f.write('</svg>\n')
    print(f"Audit 4 SVG saved to {svg_path}")

if __name__ == "__main__":
    run_audit4()
