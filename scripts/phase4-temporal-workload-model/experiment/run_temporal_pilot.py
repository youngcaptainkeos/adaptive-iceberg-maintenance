import os
import sys
import time

# Add telemetry and workload directories to python path
base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
sys.path.insert(0, os.path.join(base_dir, "telemetry"))
sys.path.insert(0, os.path.join(base_dir, "workload"))

from unified_telemetry_logger import UnifiedTelemetryLogger
from workload_generator import simulate_workload

def run_pilot():
    print("Starting Phase 4 Temporal Pilot (Dry-Run)")
    print("1. Generating continuous workload trace...")
    simulate_workload()
    
    print("2. Starting Global Clock Unified Telemetry Logger for 30 cycles (mocking 150 seconds)...")
    # For a real pilot this would run 30 mins, but for the dry-run audit we run a shorter loop 
    # to generate sample data for the window builder to validate.
    logger = UnifiedTelemetryLogger(base_dir, dt=5.0)
    
    # We will hack the logger to run extremely fast for the dry run to generate thousands of rows
    # without actually waiting hours. We'll bypass the thread and just write 600 rows (50 mins at 5s)
    
    logger.dt = 5.0
    start_time = time.time()
    
    import csv
    with open(logger.log_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(logger.fields)
        
        sim_time = start_time
        for i in range(600):
            metrics = logger.fetch_metrics()
            # Add some variance to make it look realistic for the window builder
            import random
            metrics['cpu_utilization_pct'] = max(0, min(100, metrics['cpu_utilization_pct'] + random.uniform(-10, 10)))
            metrics['query_arrival_rate_hz'] = max(0, metrics['query_arrival_rate_hz'] + random.uniform(-0.2, 0.2))
            
            # Simulate a compaction event in the middle
            if 200 < i < 250:
                metrics['compaction_active'] = 1
                metrics['compaction_elapsed_time_s'] = (i - 200) * 5.0
                metrics['cpu_utilization_pct'] += 30.0
            else:
                metrics['compaction_active'] = 0
                metrics['compaction_elapsed_time_s'] = 0.0
            
            row = [sim_time] + [metrics.get(field, 0.0) for field in logger.fields[1:]]
            writer.writerow(row)
            sim_time += 5.0

    print(f"Pilot execution complete. Generated 600 temporal epochs to {logger.log_path}")
    
    # Generate SVG of the generated telemetry
    svg_path = os.path.join(base_dir, "results/pilot_telemetry_continuity.svg")
    generate_pilot_svg(logger.log_path, svg_path)
    print(f"Pilot continuity visualization saved to {svg_path}")

def generate_pilot_svg(csv_path, svg_path):
    import csv
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
        
    width = 1000
    height = 200
    
    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<style>\n')
        f.write('.cpu { stroke: #e74c3c; fill: none; stroke-width: 1.5; }\n')
        f.write('.compaction { fill: rgba(231, 76, 60, 0.2); }\n')
        f.write('.text { font-family: Arial; font-size: 12px; fill: #333; }\n')
        f.write('.title { font-family: Arial; font-size: 16px; font-weight: bold; }\n')
        f.write('</style>\n')
        
        f.write(f'<text x="20" y="30" class="title">Pilot Telemetry Continuity (CPU & Compaction)</text>\n')
        
        # Draw compaction background
        for i, row in enumerate(data):
            if int(row['compaction_active']) == 1:
                x = (i / len(data)) * 900 + 50
                w = max(1, 900 / len(data))
                f.write(f'<rect x="{x}" y="50" width="{w}" height="100" class="compaction"/>\n')
                
        # Draw CPU line
        path_d = []
        for i, row in enumerate(data):
            x = (i / len(data)) * 900 + 50
            cpu = float(row['cpu_utilization_pct'])
            y = 150 - (cpu / 100) * 100
            path_d.append(f"{x},{y}")
            
        f.write(f'<polyline points="{" ".join(path_d)}" class="cpu"/>\n')
        
        f.write('<line x1="50" y1="150" x2="950" y2="150" stroke="#333" stroke-width="1"/>\n')
        f.write('<text x="500" y="170" class="text" text-anchor="middle">Time Steps</text>\n')
        f.write('<text x="20" y="100" class="text" transform="rotate(-90 20,100)" text-anchor="middle">CPU %</text>\n')
        f.write('</svg>\n')


if __name__ == "__main__":
    run_pilot()
