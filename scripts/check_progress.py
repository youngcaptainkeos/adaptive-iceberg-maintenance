#!/usr/bin/env python3
"""
Zero-Dependency Live Progress Monitor for Phase 6 20-Hour Live Evaluation.
Uses only standard library (csv, os, sys, subprocess) - requires NO pandas or numpy.
"""

import os
import sys
import csv
import subprocess
from datetime import datetime

REPO_DIR = "/mnt/nfs-storage/shashank_prafullathta/implementation"
if not os.path.exists(REPO_DIR):
    REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(REPO_DIR, "results")

def get_service_status():
    try:
        res = subprocess.check_output(
            ["systemctl", "--user", "is-active", "phase6_pipeline.service"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return res
    except Exception:
        return "unknown"

def inspect_data_collection():
    csv_path = os.path.join(RESULTS_DIR, "phase6a_master_training_data.csv")
    if not os.path.exists(csv_path):
        return None
    try:
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = 0
            queries = 0
            comp_ticks = 0
            last_row = None
            for r in reader:
                rows += 1
                last_row = r
                q_lat = r.get("query_latency_ms")
                if q_lat and q_lat != "nan" and q_lat != "":
                    try:
                        if float(q_lat) > 0:
                            queries += 1
                    except ValueError:
                        pass
                if r.get("compaction_active") == "True":
                    comp_ticks += 1
                    
            if rows == 0 or last_row is None:
                return None
                
            elapsed_m = float(last_row.get("elapsed_s", 0)) / 60.0
            pct = min((elapsed_m / 240.0) * 100.0, 100.0)
            current_files = last_row.get("frag_file_count", "N/A")
            cpu = float(last_row.get("cpu_util_pct", 0))
            mem = float(last_row.get("mem_used_pct", 0))
            return {
                "elapsed_m": elapsed_m,
                "target_m": 240.0,
                "pct": pct,
                "rows": rows,
                "queries": queries,
                "comp_ticks": comp_ticks,
                "current_files": current_files,
                "cpu": cpu,
                "mem": mem
            }
    except Exception as e:
        return {"error": str(e)}

def inspect_eval_progress(filename, target_hours=8.0):
    csv_path = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(csv_path):
        return None
    try:
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = 0
            compactions = 0
            last_row = None
            for r in reader:
                rows += 1
                last_row = r
                if r.get("decision") == "RUN":
                    compactions += 1
            if rows == 0 or last_row is None:
                return None
            elapsed_m = float(last_row.get("elapsed_s", 0)) / 60.0
            target_m = target_hours * 60.0
            pct = min((elapsed_m / target_m) * 100.0, 100.0)
            last_p95 = float(last_row.get("p95_query_latency_ms", 0))
            return {
                "elapsed_m": elapsed_m,
                "target_m": target_m,
                "pct": pct,
                "steps": rows,
                "last_p95": last_p95,
                "compactions": compactions
            }
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=" * 65)
    print("   PHASE 6 MASTER EVALUATION: LIVE PROGRESS MONITOR")
    print(f"   Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    
    status = get_service_status()
    status_icon = "🟢 ACTIVE" if status == "active" else f"🔴 {status.upper()}"
    print(f"Pipeline Service:   {status_icon} (phase6_pipeline.service)")
    
    # Check Step 4 / 5 first (later stages)
    eval_b = inspect_eval_progress("phase6c_run_b_costbenefit.csv", target_hours=8.0)
    eval_a = inspect_eval_progress("phase6c_run_a_baseline.csv", target_hours=8.0)
    data_col = inspect_data_collection()
    
    if eval_b:
        print("\n>>> ACTIVE STAGE: Step 5 - Cost-Benefit Agent Evaluation (8 Hours)")
        print(f"  Progress:         {eval_b['elapsed_m']:.1f} / {eval_b['target_m']:.0f} mins ({eval_b['pct']:.1f}%)")
        print(f"  Current P95 Lat:  {eval_b['last_p95']:.1f} ms")
        print(f"  Compactions Run:  {eval_b['compactions']}")
    elif eval_a:
        print("\n>>> ACTIVE STAGE: Step 4 - SOTA Baseline Policy Evaluation (8 Hours)")
        print(f"  Progress:         {eval_a['elapsed_m']:.1f} / {eval_a['target_m']:.0f} mins ({eval_a['pct']:.1f}%)")
        print(f"  Current P95 Lat:  {eval_a['last_p95']:.1f} ms")
        print(f"  Compactions Run:  {eval_a['compactions']}")
    elif data_col:
        print("\n>>> ACTIVE STAGE: Step 2 - Master Data Collection (4 Hours)")
        if "error" in data_col:
            print(f"  Reading data:     {data_col['error']}")
        else:
            bar_len = 30
            filled = int(bar_len * (data_col['pct'] / 100.0))
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"  Progress:         [{bar}] {data_col['pct']:.1f}%")
            print(f"  Elapsed Time:     {data_col['elapsed_m']:.1f} / {data_col['target_m']:.0f} mins ({data_col['elapsed_m']/60:.2f} hrs)")
            print(f"  Telemetry Ticks:  {data_col['rows']:,} samples")
            print(f"  Completed Queries:{data_col['queries']} queries executed")
            print(f"  Compaction Load:  {data_col['comp_ticks']} active compaction seconds")
            print(f"  Iceberg Files:    {data_col['current_files']} parquet data files")
            print(f"  Node Load:        CPU {data_col['cpu']:.1f}% | RAM {data_col['mem']:.1f}%")
    else:
        print("\n>>> Status: Initializing Thrift Server / Setup...")
        
    print("\n" + "-" * 65)
    print("Recent Service Log Snippet:")
    try:
        logs = subprocess.check_output(
            ["journalctl", "--user", "-u", "phase6_pipeline.service", "-n", "4", "--no-pager"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        print(logs if logs else "  (No log output available)")
    except Exception:
        print("  (Run 'journalctl --user -u phase6_pipeline.service -n 10' for logs)")
    print("=" * 65)

if __name__ == "__main__":
    main()
