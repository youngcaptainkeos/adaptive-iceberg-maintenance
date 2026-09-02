#!/usr/bin/env python3
import os
import sys
import json
import csv
import glob

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
SPARK_EVENTS_DIR = os.path.join(PHASE3B_DIR, "spark-events")
RESULTS_DIR = os.path.join(PHASE3B_DIR, "results")

def parse_event_logs():
    event_files = glob.glob(os.path.join(SPARK_EVENTS_DIR, "local-*")) + glob.glob(os.path.join(SPARK_EVENTS_DIR, "eventlog*"))
    if not event_files:
        print("No event log files found in:", SPARK_EVENTS_DIR)
        return

    jobs = {}
    tasks = []

    for filepath in sorted(event_files):
        print(f"Parsing event log: {filepath}")
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

                if event_type == "SparkListenerJobStart":
                    job_id = event.get("Job ID")
                    props = event.get("Properties", {})
                    group_id = props.get("spark.jobGroup.id", "unknown")
                    pool = props.get("spark.scheduler.pool", "default")
                    jobs[job_id] = {
                        "job_id": job_id,
                        "group_id": group_id,
                        "pool": pool,
                        "submission_time": event.get("Submission Time"),
                        "completion_time": None
                    }

                elif event_type == "SparkListenerJobEnd":
                    job_id = event.get("Job ID")
                    if job_id in jobs:
                        jobs[job_id]["completion_time"] = event.get("Completion Time")

                elif event_type == "SparkListenerTaskEnd":
                    task_info = event.get("Task Info", {})
                    task_metrics = event.get("Task Metrics", {})
                    if task_info.get("Failed") or task_info.get("Killed"):
                        continue
                    launch_time = task_info.get("Launch Time", 0)
                    finish_time = task_info.get("Finish Time", 0)
                    duration = finish_time - launch_time if launch_time and finish_time else 0
                    
                    tasks.append({
                        "stage_id": event.get("Stage ID"),
                        "task_id": task_info.get("Task ID"),
                        "launch_time": launch_time,
                        "finish_time": finish_time,
                        "duration_ms": duration,
                        "executor_cpu_time_ms": task_metrics.get("Executor CPU Time", 0) / 1000000.0,
                        "jvm_gc_time_ms": task_metrics.get("JVM GC Time", 0),
                        "deserialize_time_ms": task_metrics.get("Executor Deserialize Time", 0),
                        "serialize_time_ms": task_metrics.get("Result Serialization Time", 0),
                        "peak_memory_bytes": task_metrics.get("Peak Execution Memory", 0),
                        "disk_spilled_bytes": task_metrics.get("Disk Bytes Spilled", 0),
                        "memory_spilled_bytes": task_metrics.get("Memory Bytes Spilled", 0)
                    })

    os.makedirs(RESULTS_DIR, exist_ok=True)
    task_csv = os.path.join(RESULTS_DIR, "phase3b_task_telemetry.csv")
    with open(task_csv, "w", newline="") as f:
        if tasks:
            writer = csv.DictWriter(f, fieldnames=list(tasks[0].keys()))
            writer.writeheader()
            writer.writerows(tasks)

    print(f"Extracted {len(tasks)} task telemetry records to {task_csv}")

if __name__ == "__main__":
    parse_event_logs()
