import os
import csv
import random
from workload_regime_controller import WorkloadRegimeController

def simulate_workload():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    
    controller = WorkloadRegimeController(seed=123)
    
    sim_duration = 3600 * 2 # 2 hours simulated
    current_time = 0.0
    
    controller.start(current_time)
    
    arrivals = []
    regime_transitions = [(0.0, controller.get_current_regime_name())]
    
    # Non-homogeneous Poisson Process (NHPP) simulation using thinning/step method
    rng = random.Random(42)
    
    while current_time < sim_duration:
        # Check transition
        if controller.update_regime(current_time):
            regime_transitions.append((current_time, controller.get_current_regime_name()))
            
        rate = controller.get_current_rate()
        
        # Inter-arrival time from exponential distribution
        # If rate is very small (recovery), it might take a long time
        inter_arrival = rng.expovariate(rate)
        
        # Advance clock
        current_time += inter_arrival
        if current_time < sim_duration:
            # Assign query type (e.g. 70% read, 30% update/write)
            q_type = "READ" if rng.random() < 0.7 else "UPDATE"
            arrivals.append({
                "timestamp": current_time,
                "regime": controller.get_current_regime_name(),
                "query_type": q_type
            })
            
    # Save CSVs
    arrivals_csv = os.path.join(base_dir, "results/workload_arrivals.csv")
    with open(arrivals_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "regime", "query_type"])
        writer.writeheader()
        writer.writerows(arrivals)
        
    regimes_csv = os.path.join(base_dir, "results/workload_regime_distribution.csv")
    with open(regimes_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["time", "regime_name"])
        for t, r in regime_transitions:
            writer.writerow([t, r])
            
    print(f"Generated {len(arrivals)} simulated queries over {sim_duration}s.")
    
    # Generate SVG timeline
    svg_path = os.path.join(base_dir, "results/workload_intensity_timeline.svg")
    width = 1000
    height = 300
    
    # Calculate binned arrival rate per minute
    bins = [0] * (sim_duration // 60 + 1)
    for a in arrivals:
        b = int(a['timestamp'] // 60)
        bins[b] += 1
        
    max_rate = max(bins) if bins else 1
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.bar { fill: #3498db; }\n')
        f.write('.LOW { fill: rgba(76, 175, 80, 0.2); }\n')
        f.write('.MODERATE { fill: rgba(255, 235, 59, 0.2); }\n')
        f.write('.HIGH { fill: rgba(255, 152, 0, 0.2); }\n')
        f.write('.BURST { fill: rgba(244, 67, 54, 0.2); }\n')
        f.write('.RECOVERY { fill: rgba(158, 158, 158, 0.2); }\n')
        f.write('.text { font-family: Arial; font-size: 10px; fill: #333; }\n')
        f.write('</style>\n')
        
        # Draw regime backgrounds
        for i in range(len(regime_transitions)):
            start_t = regime_transitions[i][0]
            end_t = regime_transitions[i+1][0] if i+1 < len(regime_transitions) else sim_duration
            
            x = (start_t / sim_duration) * 900 + 50
            w = ((end_t - start_t) / sim_duration) * 900
            regime_name = regime_transitions[i][1]
            
            f.write(f'<rect x="{x}" y="50" width="{w}" height="200" class="{regime_name}"/>\n')
            f.write(f'<text x="{x + 5}" y="65" class="text">{regime_name}</text>\n')
            
        # Draw binned arrival rates
        for i, val in enumerate(bins):
            if val == 0: continue
            x = (i * 60 / sim_duration) * 900 + 50
            h = (val / max_rate) * 150
            y = 250 - h
            f.write(f'<rect x="{x}" y="{y}" width="{max(1, 900 / len(bins))}" height="{h}" class="bar"/>\n')
            
        # Axes
        f.write('<line x1="50" y1="250" x2="950" y2="250" stroke="#333" stroke-width="1"/>\n')
        f.write('<text x="500" y="270" class="text" text-anchor="middle">Time (Minutes)</text>\n')
        f.write('<text x="20" y="150" class="text" transform="rotate(-90 20,150)" text-anchor="middle">Queries per Min</text>\n')
        
        f.write('</svg>\n')
    print(f"Timeline SVG written to {svg_path}")

if __name__ == "__main__":
    simulate_workload()
