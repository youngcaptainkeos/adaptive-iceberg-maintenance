#!/usr/bin/env python3
import time
import psutil
import csv
import argparse
import urllib.request
import json
import os

def get_active_app_id_and_port():
    for port in range(4040, 4046):
        try:
            url = f"http://127.0.0.1:{port}/api/v1/applications"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    apps = json.loads(response.read().decode())
                    if apps and len(apps) > 0:
                        return apps[0]["id"], port
        except Exception:
            continue
    return None, None

def get_spark_metrics():
    app_id, port = get_active_app_id_and_port()
    if not app_id:
        return 0, 0, False
        
    active_jobs = 0
    active_tasks = 0
    compaction_active = False
    
    try:
        url = f"http://127.0.0.1:{port}/api/v1/applications/{app_id}/jobs"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=1) as response:
            if response.status == 200:
                jobs = json.loads(response.read().decode())
                for job in jobs:
                    if job.get("status") == "RUNNING" or job.get("numActiveTasks", 0) > 0:
                        active_jobs += 1
                        active_tasks += job.get("numActiveTasks", 0)
                        
                        # Identify compaction jobs by checking if it's in the background pool
                        # The API doesn't expose jobGroup directly in the jobs endpoint without hitting SQL endpoint
                        # But we can assume if job name contains 'rewrite' or we can rely on active_jobs > 1 for interference
                        # Actually, we can check the description for "rewrite" or "CALL"
                        desc = job.get("description", "").lower()
                        name = job.get("name", "").lower()
                        if "rewrite" in desc or "rewrite" in name or "call" in desc:
                            compaction_active = True
    except Exception:
        pass
        
    return active_jobs, active_tasks, compaction_active

def main():
    parser = argparse.ArgumentParser(description="Unified 1Hz Telemetry Collector")
    parser.add_argument("--output", type=str, required=True, help="Output CSV path")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    args = parser.parse_args()

    # Initial disk I/O counters
    last_disk = psutil.disk_io_counters()
    last_time = time.time()
    
    file_exists = os.path.exists(args.output)
    with open(args.output, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "cpu_utilization_pct", "memory_used_pct", 
                "disk_read_bytes_sec", "disk_write_bytes_sec", 
                "disk_read_iops", "disk_write_iops", 
                "active_spark_jobs", "active_spark_tasks", 
                "queued_queries", "running_queries", 
                "compaction_active", "frag_file_count", 
                "table_size_mb", "last_query_duration_ms", "last_compaction_duration_ms"
            ])
            f.flush()
            
        print(f"Starting unified telemetry collector to {args.output} at {args.interval}Hz...")
        
        while True:
            current_time = time.time()
            dt = current_time - last_time
            if dt == 0:
                dt = 0.001
                
            # System Metrics
            cpu_pct = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            mem_pct = mem.percent
            
            curr_disk = psutil.disk_io_counters()
            if curr_disk and last_disk:
                read_bytes_sec = (curr_disk.read_bytes - last_disk.read_bytes) / dt
                write_bytes_sec = (curr_disk.write_bytes - last_disk.write_bytes) / dt
                read_iops = (curr_disk.read_count - last_disk.read_count) / dt
                write_iops = (curr_disk.write_count - last_disk.write_count) / dt
            else:
                read_bytes_sec = write_bytes_sec = read_iops = write_iops = 0.0
                
            last_disk = curr_disk
            last_time = current_time
            
            # Spark Metrics
            active_jobs, active_tasks, comp_active = get_spark_metrics()
            
            # The remaining schema fields (queued_queries, running_queries, frag_file_count, etc.)
            # are inherently difficult to capture reliably from outside without a custom Spark listener.
            # For this validation, we will default them to 0 and rely on the experiment runner to join them later if needed.
            queued_queries = 0
            running_queries = active_jobs if not comp_active else max(0, active_jobs - 1)
            frag_file_count = 0
            table_size_mb = 0.0
            last_query_dur = 0.0
            last_comp_dur = 0.0
            
            writer.writerow([
                f"{current_time:.3f}", f"{cpu_pct:.1f}", f"{mem_pct:.1f}",
                f"{read_bytes_sec:.0f}", f"{write_bytes_sec:.0f}",
                f"{read_iops:.1f}", f"{write_iops:.1f}",
                active_jobs, active_tasks,
                queued_queries, running_queries,
                comp_active, frag_file_count,
                table_size_mb, last_query_dur, last_comp_dur
            ])
            f.flush()
            
            # Sleep to maintain 1Hz (accounting for execution time)
            elapsed = time.time() - current_time
            sleep_time = max(0, args.interval - elapsed)
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()
