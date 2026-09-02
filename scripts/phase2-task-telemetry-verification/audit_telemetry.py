import os
import json
import csv

def main():
    events_dir = "scripts/phase2-task-telemetry-verification/spark-events"
    results_dir = "scripts/phase2-task-telemetry-verification/results"
    
    # Phase 2G means
    phase2g_means = {
        "Q1": {"Control": 6.599, "Fragmented": 2.697, "Compacted": 5.251},
        "Q3": {"Control": 1.101, "Fragmented": 0.663, "Compacted": 0.955},
        "Q6": {"Control": 0.379, "Fragmented": 0.285, "Compacted": 0.297},
        "Q12": {"Control": 0.628, "Fragmented": 0.635, "Compacted": 0.558},
        "Q14": {"Control": 0.491, "Fragmented": 0.422, "Compacted": 0.428},
        "Q18": {"Control": 2.418, "Fragmented": 2.756, "Compacted": 3.189}
    }
    
    # Find the latest event log in the spark-events directory
    files = [f for f in os.listdir(events_dir) if f.startswith("local-")]
    if not files:
        print("No event log files found.")
        return
        
    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(events_dir, f)))
    event_log_path = os.path.join(events_dir, latest_file)
    print(f"Auditing event log: {event_log_path}")
    
    # Store job times per job group
    # group_id -> { "start": min_time, "end": max_time }
    group_times = {}
    
    # Also parse task count, bytes, splits per group to double check
    group_metrics = {}
    
    with open(event_log_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except:
                continue
                
            event_type = event.get("Event")
            
            if event_type == "SparkListenerJobStart":
                job_id = event.get("Job ID")
                properties = event.get("Properties", {})
                group_id = properties.get("spark.jobGroup.id", "unknown")
                submit_time = event.get("Submission Time")
                
                if any(group_id.startswith(f"q{q}_") for q in [1, 3, 6, 12, 14, 18]) and submit_time:
                    if group_id not in group_times:
                        group_times[group_id] = {"start": submit_time, "end": submit_time}
                    else:
                        group_times[group_id]["start"] = min(group_times[group_id]["start"], submit_time)
                        
            elif event_type == "SparkListenerJobEnd":
                job_id = event.get("Job ID")
                completion_time = event.get("Completion Time")
                
                # To find group_id, we need to map job_id to group_id. Let's do another pass or track it.
                
    # Let's do a two-pass parser to map job_id to group_id properly
    job_to_group = {}
    with open(event_log_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except:
                continue
            
            event_type = event.get("Event")
            if event_type == "SparkListenerJobStart":
                job_id = event.get("Job ID")
                properties = event.get("Properties", {})
                group_id = properties.get("spark.jobGroup.id", "unknown")
                if any(group_id.startswith(f"q{q}_") for q in [1, 3, 6, 12, 14, 18]):
                    job_to_group[job_id] = group_id
                    submit_time = event.get("Submission Time")
                    if group_id not in group_times:
                        group_times[group_id] = {"start": submit_time, "end": submit_time}
                    else:
                        group_times[group_id]["start"] = min(group_times[group_id]["start"], submit_time)
                        
            elif event_type == "SparkListenerJobEnd":
                job_id = event.get("Job ID")
                completion_time = event.get("Completion Time")
                if job_id in job_to_group and completion_time:
                    group_id = job_to_group[job_id]
                    group_times[group_id]["end"] = max(group_times[group_id]["end"], completion_time)

    # Calculate runtimes
    # Write comparison CSV
    comp_csv_path = os.path.join(results_dir, "phase2g_vs_phase2j_runtime_comparison.csv")
    
    with open(comp_csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "query", "state", "phase2g_mean_seconds", "phase2j_telemetry_seconds", "absolute_difference_seconds", "percentage_difference"
        ])
        
        queries = ["1", "3", "6", "12", "14", "18"]
        states = ["control", "fragmented", "compacted"]
        
        for q in queries:
            for s in states:
                group_id = f"q{q}_{s}"
                q_label = f"Q{q}"
                s_label = s.capitalize()
                
                p2g_val = phase2g_means[q_label][s_label]
                
                if group_id in group_times:
                    t_info = group_times[group_id]
                    p2j_val = (t_info["end"] - t_info["start"]) / 1000.0  # ms to seconds
                else:
                    p2j_val = 0.0
                    
                diff = p2j_val - p2g_val
                pct_diff = (diff / p2g_val) * 100.0 if p2g_val != 0 else 0.0
                
                writer.writerow([
                    q_label, s_label, f"{p2g_val:.4f}", f"{p2j_val:.4f}", f"{diff:.4f}", f"{pct_diff:.2f}%"
                ])
                
    print(f"Saved runtime comparison CSV to: {comp_csv_path}")

if __name__ == "__main__":
    main()
