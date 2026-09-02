import os
import sys
import json
import csv

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"

def parse_single_event_log(filepath):
    print(f"Parsing event log: {filepath}")
    
    scheduler_mode = "UNKNOWN"
    
    # Store events data
    jobs = {}        # job_id -> {job_id, group_id, description, submission_time, completion_time, stage_ids, pool}
    stages = {}      # stage_id -> {stage_id, job_id, submission_time, completion_time, num_tasks}
    tasks = []       # list of task dicts
    
    stage_to_job = {}
    
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
                
            event_type = event.get("Event")
            
            # 1. Environment Details
            if event_type == "SparkListenerSparkStart":
                spark_props = event.get("Driver Logs", {}).get("Spark Properties", {})
                if not spark_props:
                    spark_props = event.get("Spark Properties", {})
                scheduler_mode = spark_props.get("spark.scheduler.mode", "UNKNOWN").upper()
                
            # 2. Job Start
            elif event_type == "SparkListenerJobStart":
                job_id = event.get("Job ID")
                properties = event.get("Properties", {})
                job_group = properties.get("spark.jobGroup.id", "unknown")
                pool = properties.get("spark.scheduler.pool", "default")
                stage_ids = event.get("Stage IDs", [])
                
                jobs[job_id] = {
                    "job_id": job_id,
                    "group_id": job_group,
                    "description": properties.get("spark.job.description", ""),
                    "submission_time": event.get("Submission Time"),
                    "completion_time": None,
                    "stage_ids": stage_ids,
                    "pool": pool
                }
                
                for sid in stage_ids:
                    stage_to_job[sid] = job_id
                    
            # 3. Job End
            elif event_type == "SparkListenerJobEnd":
                job_id = event.get("Job ID")
                if job_id in jobs:
                    jobs[job_id]["completion_time"] = event.get("Completion Time")
                    
            # 4. Stage Submitted
            elif event_type == "SparkListenerStageSubmitted":
                stage_info = event.get("Stage Info", {})
                stage_id = stage_info.get("Stage ID")
                job_id = stage_to_job.get(stage_id, -1)
                
                stages[stage_id] = {
                    "stage_id": stage_id,
                    "job_id": job_id,
                    "submission_time": stage_info.get("Submission Time"),
                    "completion_time": None,
                    "num_tasks": stage_info.get("Number of Tasks", 0)
                }
                
            # 5. Stage Completed
            elif event_type == "SparkListenerStageCompleted":
                stage_info = event.get("Stage Info", {})
                stage_id = stage_info.get("Stage ID")
                if stage_id in stages:
                    stages[stage_id]["completion_time"] = stage_info.get("Completion Time")
                    
            # 6. Task End
            elif event_type == "SparkListenerTaskEnd":
                stage_id = event.get("Stage ID")
                task_info = event.get("Task Info", {})
                task_metrics = event.get("Task Metrics", {})
                
                if task_info.get("Failed") or task_info.get("Killed"):
                    continue
                    
                launch_time = task_info.get("Launch Time")
                finish_time = task_info.get("Finish Time")
                duration = finish_time - launch_time if launch_time and finish_time else 0
                
                cpu_time_ms = task_metrics.get("Executor CPU Time", 0) / 1000000.0
                gc_time_ms = task_metrics.get("JVM GC Time", 0)
                
                input_metrics = task_metrics.get("Input Metrics", {})
                input_bytes = input_metrics.get("Bytes Read", 0)
                
                shuffle_read = task_metrics.get("Shuffle Read Metrics", {})
                shuffle_read_bytes = shuffle_read.get("Local Bytes Read", 0) + shuffle_read.get("Remote Bytes Read", 0)
                
                shuffle_write = task_metrics.get("Shuffle Write Metrics", {})
                shuffle_write_bytes = shuffle_write.get("Shuffle Bytes Written", 0)
                
                tasks.append({
                    "task_id": task_info.get("Task ID"),
                    "stage_id": stage_id,
                    "launch_time": launch_time,
                    "finish_time": finish_time,
                    "duration_ms": duration,
                    "cpu_time_ms": cpu_time_ms,
                    "gc_time_ms": gc_time_ms,
                    "input_bytes": input_bytes,
                    "shuffle_read_bytes": shuffle_read_bytes,
                    "shuffle_write_bytes": shuffle_write_bytes
                })
                
    if scheduler_mode == "UNKNOWN":
        for job in jobs.values():
            if job["pool"] in ["foreground", "background"]:
                scheduler_mode = "FAIR"
                break
        if scheduler_mode == "UNKNOWN":
            scheduler_mode = "FIFO"
            
    return scheduler_mode, jobs, stages, tasks

def compute_max_concurrency(tasks):
    events = []
    for t in tasks:
        launch = t.get("launch_time")
        finish = t.get("finish_time")
        if launch is not None and finish is not None:
            events.append((launch, 1))
            events.append((finish, -1))
            
    if not events:
        return 0
        
    events.sort(key=lambda x: (x[0], x[1]))
    
    current = 0
    max_c = 0
    for time, val in events:
        current += val
        if current > max_c:
            max_c = current
            
    return max_c

def compute_union_overlap(s1_start, s1_end, other_intervals):
    if not s1_start or not s1_end or s1_end <= s1_start:
        return 0.0
    
    # Clip intervals to [s1_start, s1_end]
    clipped = []
    for start, end in other_intervals:
        if not start or not end or end <= start:
            continue
        overlap_start = max(start, s1_start)
        overlap_end = min(end, s1_end)
        if overlap_end > overlap_start:
            clipped.append((overlap_start, overlap_end))
            
    if not clipped:
        return 0.0
        
    # Merge intervals
    clipped.sort(key=lambda x: x[0])
    merged = []
    current_start, current_end = clipped[0]
    for start, end in clipped[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    merged.append((current_start, current_end))
    
    # Sum durations
    return sum(end - start for start, end in merged)

def match_job_to_run(job, query_runs, comp_runs):
    desc = job.get("description", "")
    s_time = job["submission_time"]
    if not s_time:
        return None
    s_sec = s_time / 1000.0
    
    # 1. Compaction job check
    if "rewrite_data_files" in desc or job.get("group_id", "").startswith("compaction_rep"):
        # Match with compaction runs
        for cr in comp_runs:
            if cr["start_time"] - 5.0 <= s_sec <= cr["end_time"] + 5.0:
                return {
                    "type": "compaction",
                    "scheduler_mode": cr["scheduler_mode"],
                    "repetition": cr["repetition"],
                    "run_type": "concurrent",
                    "query": "compaction"
                }
        # Fallback using group_id split
        group = job.get("group_id", "")
        if group.startswith("compaction_rep"):
            try:
                rep = int(group.replace("compaction_rep", ""))
                return {
                    "type": "compaction",
                    "scheduler_mode": "UNKNOWN",
                    "repetition": rep,
                    "run_type": "concurrent",
                    "query": "compaction"
                }
            except:
                pass
        return {
            "type": "compaction",
            "scheduler_mode": "UNKNOWN",
            "repetition": -1,
            "run_type": "concurrent",
            "query": "compaction"
        }
        
    # 2. Query job check
    for qr in query_runs:
        if qr["start_time"] - 2.0 <= s_sec <= qr["end_time"] + 2.0:
            return {
                "type": "query",
                "scheduler_mode": qr["scheduler_mode"],
                "repetition": qr["repetition"],
                "run_type": qr["run_type"],
                "query": qr["query"]
            }
            
    # Proximity fallback: find closest query run within 15 seconds of start
    best_qr = None
    min_diff = 15.0
    for qr in query_runs:
        diff = abs(s_sec - qr["start_time"])
        if diff < min_diff:
            min_diff = diff
            best_qr = qr
            
    if best_qr:
        return {
            "type": "query",
            "scheduler_mode": best_qr["scheduler_mode"],
            "repetition": best_qr["repetition"],
            "run_type": best_qr["run_type"],
            "query": best_qr["query"]
        }
            
    return None

def analyze_overlap_and_write():
    log_dir = f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/spark-events"
    if not os.path.exists(log_dir):
        print(f"Error: Event log directory {log_dir} does not exist!")
        sys.exit(1)
        
    log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.startswith("local-")]
    if not log_files:
        print(f"Error: No Spark event logs found in {log_dir}!")
        sys.exit(1)
        
    # Load query runs from query_runs.csv
    query_runs = []
    query_runs_csv = f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/results/query_runs.csv"
    if os.path.exists(query_runs_csv):
        with open(query_runs_csv, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                query_runs.append({
                    "scheduler_mode": row["scheduler_mode"],
                    "repetition": int(row["repetition"]),
                    "run_type": row["run_type"],
                    "query": row["query"],
                    "start_time": float(row["client_start_time"]),
                    "end_time": float(row["client_end_time"]),
                    "duration_ms": float(row["client_duration_ms"])
                })
                
    # Load compaction runs from compaction_runs.csv
    comp_runs = []
    comp_runs_csv = f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/results/compaction_runs.csv"
    if os.path.exists(comp_runs_csv):
        with open(comp_runs_csv, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                comp_runs.append({
                    "scheduler_mode": row["scheduler_mode"],
                    "repetition": int(row["repetition"]),
                    "start_time": float(row["client_start_time"]),
                    "end_time": float(row["client_end_time"]),
                    "duration_ms": float(row["client_duration_ms"])
                })
                
    print(f"Loaded {len(query_runs)} query runs and {len(comp_runs)} compaction runs.")
    
    extracted_path = f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/results/telemetry_extracted.csv"
    task_path = f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/results/task_telemetry.csv"
    stage_path = f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/results/stage_telemetry.csv"
    
    # Initialize files and writers
    f_extracted = open(extracted_path, "w", newline="")
    f_task = open(task_path, "w", newline="")
    f_stage = open(stage_path, "w", newline="")
    
    w_extracted = csv.writer(f_extracted)
    w_task = csv.writer(f_task)
    w_stage = csv.writer(f_stage)
    
    w_extracted.writerow([
        "scheduler_mode", "repetition", "run_type", "query", "job_id",
        "spark_start_time", "spark_end_time", "spark_duration_ms",
        "compaction_start_time", "compaction_end_time", "overlap_ms", "overlap_pct",
        "num_tasks", "sum_task_duration_ms", "avg_task_duration_ms"
    ])
    
    w_task.writerow([
        "scheduler_mode", "repetition", "run_type", "query", "job_id",
        "stage_id", "task_id", "launch_time", "finish_time", "duration_ms",
        "cpu_time_ms", "gc_time_ms", "input_bytes", "shuffle_read_bytes", "shuffle_write_bytes"
    ])
    
    w_stage.writerow([
        "scheduler_mode", "repetition", "run_type", "query", "job_id",
        "stage_id", "submission_time", "completion_time", "duration_ms",
        "num_tasks", "max_concurrency", "overlap_duration_ms"
    ])
    
    for filepath in log_files:
        mode, jobs, stages, tasks = parse_single_event_log(filepath)
        print(f"  Processed {filepath}: Mode={mode}, Jobs={len(jobs)}, Stages={len(stages)}, Tasks={len(tasks)}")
        
        # Map tasks by stage
        tasks_by_stage = {}
        for t in tasks:
            sid = t["stage_id"]
            if sid not in tasks_by_stage:
                tasks_by_stage[sid] = []
            tasks_by_stage[sid].append(t)
            
        # Index compaction jobs by repetition
        compactions = {}
        for jid, job in jobs.items():
            match = match_job_to_run(job, query_runs, comp_runs)
            if match and match["type"] == "compaction":
                rep = match["repetition"]
                compactions[rep] = job
                
        # Now process each job
        for jid, job in jobs.items():
            match = match_job_to_run(job, query_runs, comp_runs)
            if not match:
                continue
                
            run_type = match["run_type"]
            rep = match["repetition"]
            query = match["query"]
            job_mode = match["scheduler_mode"]
            if job_mode == "UNKNOWN":
                job_mode = mode
                
            s_time = job["submission_time"]
            c_time = job["completion_time"]
            if s_time is None or c_time is None:
                continue
                
            dur = c_time - s_time
            
            # Collect job tasks
            job_tasks = []
            for sid in job["stage_ids"]:
                job_tasks.extend(tasks_by_stage.get(sid, []))
                
            num_tasks = len(job_tasks)
            sum_dur = sum(t["duration_ms"] for t in job_tasks)
            avg_dur = sum_dur / num_tasks if num_tasks > 0 else 0.0
            
            # Overlap calculations
            comp_start = ""
            comp_end = ""
            overlap_ms = 0.0
            overlap_pct = 0.0
            
            if run_type == "concurrent" and rep in compactions:
                comp_job = compactions[rep]
                cs = comp_job["submission_time"]
                ce = comp_job["completion_time"]
                if cs is not None and ce is not None:
                    comp_start = cs
                    comp_end = ce
                    
                    overlap_s = max(s_time, cs)
                    overlap_e = min(c_time, ce)
                    if overlap_e > overlap_s:
                        overlap_ms = overlap_e - overlap_s
                        overlap_pct = overlap_ms / dur if dur > 0 else 0.0
                        
            # Write job-level metrics (extracted path)
            w_extracted.writerow([
                job_mode, rep, run_type, query, jid,
                s_time, c_time, dur,
                comp_start, comp_end, overlap_ms, f"{overlap_pct:.4f}",
                num_tasks, sum_dur, f"{avg_dur:.2f}"
            ])
            
            # Write task-level metrics
            for t in job_tasks:
                w_task.writerow([
                    job_mode, rep, run_type, query, jid,
                    t["stage_id"], t["task_id"], t["launch_time"], t["finish_time"], t["duration_ms"],
                    f"{t['cpu_time_ms']:.2f}", t["gc_time_ms"], t["input_bytes"],
                    t["shuffle_read_bytes"], t["shuffle_write_bytes"]
                ])
                
            # Write stage-level metrics
            for sid in job["stage_ids"]:
                if sid not in stages:
                    continue
                st = stages[sid]
                st_start = st["submission_time"]
                st_end = st["completion_time"]
                if st_start is None or st_end is None:
                    continue
                
                st_dur = st_end - st_start
                st_tasks = tasks_by_stage.get(sid, [])
                
                # Compute max concurrency
                max_c = compute_max_concurrency(st_tasks)
                
                # Compute overlap duration with other stages in the same job
                other_intervals = []
                for osid in job["stage_ids"]:
                    if osid != sid and osid in stages:
                        ost = stages[osid]
                        if ost["submission_time"] and ost["completion_time"]:
                            other_intervals.append((ost["submission_time"], ost["completion_time"]))
                            
                st_overlap = compute_union_overlap(st_start, st_end, other_intervals)
                
                w_stage.writerow([
                    job_mode, rep, run_type, query, jid,
                    sid, st_start, st_end, st_dur,
                    len(st_tasks), max_c, st_overlap
                ])
                
    f_extracted.close()
    f_task.close()
    f_stage.close()
    print("Telemetry extraction complete!")

if __name__ == "__main__":
    analyze_overlap_and_write()
