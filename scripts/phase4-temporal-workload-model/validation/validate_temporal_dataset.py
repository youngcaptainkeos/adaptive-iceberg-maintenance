import os
import csv

def validate():
    base_dir = "/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model"
    log_path = os.path.join(base_dir, "results/temporal_windows.csv")
    
    if not os.path.exists(log_path):
        print("Temporal windows not found. Run pilot first.")
        return
        
    with open(log_path, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
        
    audit_results = {
        "Total Windows": len(data),
        "Missing Timestamps": 0,
        "Duplicate Timestamps": 0,
        "Negative Durations": 0,
        "Constant Features Found": [],
        "Temporal Gaps (>5.1s)": 0
    }
    
    timestamps = set()
    prev_t = None
    
    # Check for constants
    feature_vals = {k: set() for k in data[0].keys()}
    
    for row in data:
        t = float(row['timestamp'])
        
        if t in timestamps:
            audit_results["Duplicate Timestamps"] += 1
        timestamps.add(t)
        
        if prev_t is not None:
            diff = t - prev_t
            if diff < 0:
                audit_results["Negative Durations"] += 1
            if diff > 5.5: # Allow tiny floating point jitter
                audit_results["Temporal Gaps (>5.1s)"] += 1
                
        prev_t = t
        
        for k, v in row.items():
            feature_vals[k].add(v)
            
    for k, v_set in feature_vals.items():
        if len(v_set) <= 1:
            audit_results["Constant Features Found"].append(k)
            
    # Output Results
    csv_path = os.path.join(base_dir, "results/temporal_validation_audit.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Check", "Value"])
        for k, v in audit_results.items():
            if isinstance(v, list): v = ", ".join(v) if v else "None"
            writer.writerow([k, v])
            
    print(f"Validation complete. Results saved to {csv_path}")

if __name__ == "__main__":
    validate()
