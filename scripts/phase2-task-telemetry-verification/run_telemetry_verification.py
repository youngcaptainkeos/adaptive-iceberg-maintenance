import os
import re
import time
import json
import csv
from pyspark.sql import SparkSession

def main():
    print("Starting Phase 2J Spark Task-Level Telemetry Verification...")
    
    # Define directories
    events_dir = "scripts/phase2-task-telemetry-verification/spark-events"
    results_dir = "scripts/phase2-task-telemetry-verification/results"
    plans_dir = "scripts/phase2-task-telemetry-verification/results/physical_plans"
    sql_dir = "scripts/phase2-validated-layout-comparison/sql"
    
    # Initialize Spark Session with event logging enabled
    spark = SparkSession.builder \
        .appName("TelemetryVerificationSuite") \
        .config("spark.eventLog.enabled", "true") \
        .config("spark.eventLog.dir", events_dir) \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.warehouse.dir", "file:///home/shashank/Link to PDocuments/Capstone/implementation/spark-warehouse") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
        
    app_id = spark.sparkContext.applicationId
    print(f"Spark Application initialized. ID: {app_id}")
    
    try:
        # 1. Warm-up run to JIT compile and minimize initialization noise in logs
        warmup_sql = """
        SELECT sum(l_extendedprice * l_discount) as revenue 
        FROM local.tpch.lineitem 
        WHERE l_shipdate >= date '1994-01-01' AND l_shipdate < date '1994-01-01' + interval '1' year
        """
        print("Executing warm-up query...")
        spark.sparkContext.setJobGroup("warmup", "Warm-up execution")
        spark.sql(warmup_sql).collect()
        
        # 2. Run the 18 query-state combinations
        queries = ["1", "3", "6", "12", "14", "18"]
        states = ["control", "fragmented", "compacted"]
        
        for q in queries:
            for s in states:
                # Find matching SQL file
                sql_filename = f"query{q}_{s}.sql"
                sql_path = os.path.join(sql_dir, sql_filename)
                
                if not os.path.exists(sql_path):
                    print(f"Warning: SQL file {sql_path} does not exist. Skipping.")
                    continue
                    
                print(f"Executing Query Q{q} in state: {s.upper()}...")
                with open(sql_path, "r") as f:
                    query_text = f.read()
                    
                job_group_id = f"q{q}_{s}"
                spark.sparkContext.setJobGroup(job_group_id, f"Query Q{q} {s.upper()} run")
                
                # Execute and time the query wall-clock duration
                df = spark.sql(query_text)
                
                # Capture and save physical plan
                plan_str = df._jdf.queryExecution().toString()
                plan_out_path = os.path.join(plans_dir, f"q{q}_{s}_physical_plan.txt")
                with open(plan_out_path, "w") as plan_file:
                    plan_file.write(plan_str)
                    
                t_start = time.time()
                result = df.collect()
                t_end = time.time()
                
                print(f"Completed Q{q}_{s} in {t_end - t_start:.3f}s. Result rows: {len(result)}")
                
    finally:
        # Stop Spark Session to flush and close the event log
        print("Stopping Spark session...")
        spark.stop()
        
    # 3. Parse the event log file
    event_log_path = os.path.join(events_dir, app_id)
    print(f"Parsing Spark event log file: {event_log_path}")
    
    if not os.path.exists(event_log_path):
        raise FileNotFoundError(f"Spark event log file not found at: {event_log_path}")
        
    jobs, stages, tasks = parse_event_log(event_log_path)
    print(f"Parsing complete. Jobs: {len(jobs)}, Stages: {len(stages)}, Tasks: {len(tasks)}")
    
    # 4. Write results/task_telemetry_raw.csv
    raw_csv_path = os.path.join(results_dir, "task_telemetry_raw.csv")
    write_task_csv(raw_csv_path, tasks)
    
    # 5. Write results/stage_telemetry_summary.csv
    summary_csv_path = os.path.join(results_dir, "stage_telemetry_summary.csv")
    write_stage_csv(summary_csv_path, stages)
    
    print("Telemetry extraction and summarization finished successfully.")

def parse_event_log(event_log_path):
    jobs = {}
    stage_to_group = {}
    stages = {}
    tasks = []
    
    with open(event_log_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except Exception as e:
                print(f"Error parsing line: {e}")
                continue
                
            event_type = event.get("Event")
            
            if event_type == "SparkListenerJobStart":
                job_id = event.get("Job ID")
                properties = event.get("Properties", {})
                job_group = properties.get("spark.jobGroup.id", "unknown")
                stage_ids = event.get("Stage IDs", [])
                
                # Check if this job belongs to one of our measured query-states
                if any(job_group.startswith(f"q{q}_") for q in [1, 3, 6, 12, 14, 18]):
                    jobs[job_id] = {
                        "job_id": job_id,
                        "job_group": job_group,
                        "stage_ids": stage_ids
                    }
                    for stage_id in stage_ids:
                        stage_to_group[stage_id] = job_group
                        
            elif event_type == "SparkListenerStageSubmitted":
                stage_info = event.get("Stage Info", {})
                stage_id = stage_info.get("Stage ID")
                if stage_id in stage_to_group:
                    stages[stage_id] = {
                        "stage_id": stage_id,
                        "stage_name": stage_info.get("Stage Name", ""),
                        "num_tasks": stage_info.get("Number of Tasks", 0),
                        "submission_time": stage_info.get("Submission Time"),
                        "completion_time": None,
                        "tasks": []
                    }
                    
            elif event_type == "SparkListenerStageCompleted":
                stage_info = event.get("Stage Info", {})
                stage_id = stage_info.get("Stage ID")
                if stage_id in stages:
                    stages[stage_id]["completion_time"] = stage_info.get("Completion Time")
                    stages[stage_id]["num_tasks"] = stage_info.get("Number of Tasks", stages[stage_id]["num_tasks"])
                    
            elif event_type == "SparkListenerTaskEnd":
                stage_id = event.get("Stage ID")
                if stage_id in stage_to_group:
                    task_info = event.get("Task Info", {})
                    task_metrics = event.get("Task Metrics", {})
                    
                    if task_info.get("Failed") or task_info.get("Killed"):
                        continue
                        
                    # Extract file splits read
                    accumulables = task_info.get("Accumulables", [])
                    file_splits_read = 0
                    for acc in accumulables:
                        if acc.get("Name") == "number of file splits read":
                            try:
                                file_splits_read = int(acc.get("Update", 0))
                            except (ValueError, TypeError):
                                file_splits_read = 0
                            break
                            
                    input_metrics = task_metrics.get("Input Metrics", {})
                    
                    task_data = {
                        "query_state": stage_to_group[stage_id],
                        "stage_id": stage_id,
                        "task_id": task_info.get("Task ID"),
                        "task_index": task_info.get("Index"),
                        "launch_time": task_info.get("Launch Time"),
                        "finish_time": task_info.get("Finish Time"),
                        "duration_ms": task_info.get("Finish Time", 0) - task_info.get("Launch Time", 0),
                        "executor_run_time_ms": task_metrics.get("Executor Run Time", 0),
                        "executor_cpu_time_ms": int(task_metrics.get("Executor CPU Time", 0) / 1000000),
                        "jvm_gc_time_ms": task_metrics.get("JVM GC Time", 0),
                        "executor_deserialize_time_ms": task_metrics.get("Executor Deserialize Time", 0),
                        "result_serialization_time_ms": task_metrics.get("Result Serialization Time", 0),
                        "input_bytes_read": input_metrics.get("Bytes Read", 0),
                        "input_records_read": input_metrics.get("Records Read", 0),
                        "file_splits_read": file_splits_read
                    }
                    
                    tasks.append(task_data)
                    if stage_id in stages:
                        stages[stage_id]["tasks"].append(task_data)
                        
    return jobs, stages, tasks

def compute_max_concurrency(tasks_in_stage):
    if not tasks_in_stage:
        return 0
    events = []
    for t in tasks_in_stage:
        events.append((t['launch_time'], 1))
        events.append((t['finish_time'], -1))
        
    events.sort(key=lambda x: (x[0], -x[1]))
    
    max_overlap = 0
    current_overlap = 0
    for _, val in events:
        current_overlap += val
        if current_overlap > max_overlap:
            max_overlap = current_overlap
    return max_overlap

def split_query_state(qs):
    parts = qs.split("_")
    query_num = parts[0].upper()
    state_name = parts[1].capitalize()
    return query_num, state_name

def write_task_csv(filepath, tasks):
    headers = [
        "query", "state", "stage_id", "task_id", "task_index", 
        "launch_time", "finish_time", "duration_ms", 
        "executor_run_time_ms", "executor_cpu_time_ms", "jvm_gc_time_ms", 
        "executor_deserialize_time_ms", "result_serialization_time_ms", 
        "input_bytes_read", "input_records_read", "file_splits_read"
    ]
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        for t in tasks:
            query, state = split_query_state(t["query_state"])
            writer.writerow([
                query, state, t["stage_id"], t["task_id"], t["task_index"],
                t["launch_time"], t["finish_time"], t["duration_ms"],
                t["executor_run_time_ms"], t["executor_cpu_time_ms"], t["jvm_gc_time_ms"],
                t["executor_deserialize_time_ms"], t["result_serialization_time_ms"],
                t["input_bytes_read"], t["input_records_read"], t["file_splits_read"]
            ])
    print(f"Saved raw task telemetry to: {filepath}")

def write_stage_csv(filepath, stages):
    headers = [
        "query", "state", "stage_id", "stage_name", "task_count", 
        "stage_duration_ms", "total_task_duration_ms", "avg_task_duration_ms", 
        "max_task_duration_ms", "sum_input_bytes", "sum_input_records", 
        "sum_file_splits", "max_concurrency", "utilized_parallelism_ratio"
    ]
    
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        
        # Sort stages by stage_id to keep order logical
        for stage_id in sorted(stages.keys()):
            s = stages[stage_id]
            tasks = s["tasks"]
            if not tasks:
                continue
                
            query, state = split_query_state(tasks[0]["query_state"])
            
            # Stage duration
            if s["completion_time"] and s["submission_time"]:
                stage_dur = s["completion_time"] - s["submission_time"]
            else:
                # Fallback to tasks boundary
                launches = [t["launch_time"] for t in tasks if t["launch_time"] is not None]
                finishes = [t["finish_time"] for t in tasks if t["finish_time"] is not None]
                stage_dur = max(finishes) - min(launches) if launches and finishes else 0
                
            durations = [t["duration_ms"] for t in tasks]
            total_task_dur = sum(durations)
            avg_task_dur = total_task_dur / len(tasks) if tasks else 0
            max_task_dur = max(durations) if tasks else 0
            
            sum_bytes = sum(t["input_bytes_read"] for t in tasks)
            sum_records = sum(t["input_records_read"] for t in tasks)
            sum_splits = sum(t["file_splits_read"] for t in tasks)
            
            max_conc = compute_max_concurrency(tasks)
            utilized_ratio = max_conc / 16.0  # 16 CPU cores available
            
            writer.writerow([
                query, state, stage_id, s["stage_name"], len(tasks),
                stage_dur, total_task_dur, f"{avg_task_dur:.2f}", max_task_dur,
                sum_bytes, sum_records, sum_splits, max_conc, f"{utilized_ratio:.4f}"
            ])
            
    print(f"Saved stage telemetry summary to: {filepath}")

if __name__ == "__main__":
    main()
