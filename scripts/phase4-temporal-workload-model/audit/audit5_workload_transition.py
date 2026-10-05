import os
import csv
from collections import Counter

def run_audit5():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    out_dir = os.path.join(base_dir, "results")
    
    csv_path = os.path.join(out_dir, "workload_regime_distribution.csv")
    if not os.path.exists(csv_path):
        print("Workload distribution missing. Run pilot first.")
        return
        
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
        
    transitions = []
    durations = []
    
    for i in range(len(data) - 1):
        curr_r = data[i]['regime_name']
        next_r = data[i+1]['regime_name']
        t1 = float(data[i]['time'])
        t2 = float(data[i+1]['time'])
        
        transitions.append(f"{curr_r} -> {next_r}")
        durations.append({"regime": curr_r, "duration": t2 - t1})
        
    trans_counts = Counter(transitions)
    
    # Calculate average durations
    avg_dur = {}
    for d in durations:
        r = d['regime']
        if r not in avg_dur: avg_dur[r] = []
        avg_dur[r].append(d['duration'])
        
    avg_dur = {r: sum(vals)/len(vals) for r, vals in avg_dur.items()}
    
    results = []
    for t, c in trans_counts.items():
        results.append({"Transition": t, "Count": c, "Avg_Duration_Before_Transition_s": avg_dur.get(t.split(" -> ")[0], 0)})
        
    out_csv = os.path.join(out_dir, "workload_transition_analysis.csv")
    with open(out_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Transition", "Count", "Avg_Duration_Before_Transition_s"])
        writer.writeheader()
        writer.writerows(results)
        
    print(f"Audit 5 CSV saved to {out_csv}")

    # Generate SVG Network / Bar
    svg_path = os.path.join(out_dir, "workload_transition_analysis.svg")
    width = 800
    height = 50 + len(results) * 40
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.bar { fill: #3498db; }\n')
        f.write('.text { font-family: Arial; font-size: 13px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 16px; font-weight: bold; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="30" class="title">Audit 5: Workload Regime Transitions</text>\n')
        
        y = 60
        max_c = max(trans_counts.values()) if trans_counts else 1
        for res in results:
            f.write(f'<text x="20" y="{y+15}" class="text">{res["Transition"]}</text>\n')
            
            w = (res["Count"] / max_c) * 400
            f.write(f'<rect x="250" y="{y}" width="{max(1, w)}" height="20" class="bar"/>\n')
            f.write(f'<text x="{255 + w}" y="{y+15}" class="text">{res["Count"]} times (Avg {res["Avg_Duration_Before_Transition_s"]:.0f}s)</text>\n')
            y += 40
            
        f.write('</svg>\n')
    print(f"Audit 5 SVG saved to {svg_path}")

if __name__ == "__main__":
    run_audit5()
