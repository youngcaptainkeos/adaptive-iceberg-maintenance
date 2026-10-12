#!/usr/bin/env python3
"""
Experiment & Run Version Manager for Apache Iceberg Adaptive Compaction.
Automatically organizes, iterates, and tracks experiment runs:
  results/runs/run_001/
  results/runs/run_002/
  ...
Each run directory contains its own data, models, evaluations, and metadata.
"""

import os
import sys
import json
import re
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_RUNS_DIR = "results/runs"

def get_git_commit():
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], 
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return commit
    except Exception:
        return "unknown"

def get_next_run_number(base_dir=DEFAULT_RUNS_DIR) -> int:
    """Scans base_dir for run_XXX folders and returns the next integer (1-indexed)."""
    os.makedirs(base_dir, exist_ok=True)
    existing_nums = []
    for item in os.listdir(base_dir):
        m = re.match(r"^run_(\d+)", item)
        if m and os.path.isdir(os.path.join(base_dir, item)):
            existing_nums.append(int(m.group(1)))
    return (max(existing_nums) + 1) if existing_nums else 1

def init_run(run_type="custom", description="", base_dir=DEFAULT_RUNS_DIR, run_num=None):
    """
    Initializes a new run directory with data, models, and eval subfolders.
    Returns metadata dict with all generated paths.
    """
    if run_num is None:
        run_num = get_next_run_number(base_dir)
        
    run_id = f"run_{run_num:03d}"
    run_path = os.path.join(base_dir, run_id)
    
    data_dir = os.path.join(run_path, "data")
    models_dir = os.path.join(run_path, "models")
    eval_dir = os.path.join(run_path, "eval")
    
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(eval_dir, exist_ok=True)
    
    meta = {
        "run_id": run_id,
        "run_number": run_num,
        "type": run_type,
        "description": description,
        "status": "running",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": None,
        "git_commit": get_git_commit(),
        "paths": {
            "root": run_path,
            "data": data_dir,
            "models": models_dir,
            "eval": eval_dir,
            "training_data": os.path.join(data_dir, "training_data.csv"),
            "run_a_baseline": os.path.join(eval_dir, "run_a_baseline.csv"),
            "run_b_costbenefit": os.path.join(eval_dir, "run_b_costbenefit.csv")
        },
        "metrics": {}
    }
    
    meta_file = os.path.join(run_path, "run_meta.json")
    with open(meta_file, "w") as f:
        json.dump(meta, f, indent=4)
        
    # Update latest symlink if supported
    latest_link = os.path.join(base_dir, "latest")
    try:
        if os.path.islink(latest_link) or os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(run_id, latest_link)
    except Exception:
        pass
        
    return meta

def complete_run(run_id, status="completed", metrics=None, base_dir=DEFAULT_RUNS_DIR):
    """Marks a run as completed and records summary metrics."""
    run_path = os.path.join(base_dir, run_id)
    meta_file = os.path.join(run_path, "run_meta.json")
    if not os.path.exists(meta_file):
        print(f"Warning: {meta_file} not found.")
        return
        
    with open(meta_file, "r") as f:
        meta = json.load(f)
        
    meta["status"] = status
    meta["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if metrics:
        meta["metrics"].update(metrics)
        
    with open(meta_file, "w") as f:
        json.dump(meta, f, indent=4)
    print(f"Run {run_id} marked as '{status}'.")

def list_runs(base_dir=DEFAULT_RUNS_DIR):
    """Prints a structured summary of all existing runs."""
    if not os.path.exists(base_dir):
        print(f"No runs found in {base_dir}")
        return
        
    items = sorted([d for d in os.listdir(base_dir) if re.match(r"^run_\d+", d)])
    if not items:
        print(f"No runs found in {base_dir}")
        return
        
    print(f"\n{'RUN ID':<10} | {'TYPE':<18} | {'STATUS':<12} | {'CREATED':<20} | {'DESCRIPTION'}")
    print("-" * 85)
    for run_id in items:
        meta_file = os.path.join(base_dir, run_id, "run_meta.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r") as f:
                    meta = json.load(f)
                rtype = meta.get("type", "custom")
                status = meta.get("status", "unknown")
                created = meta.get("created_at", "unknown")
                desc = meta.get("description", "")
                print(f"{run_id:<10} | {rtype:<18} | {status:<12} | {created:<20} | {desc}")
            except Exception as e:
                print(f"{run_id:<10} | error reading meta: {e}")
        else:
            print(f"{run_id:<10} | (no run_meta.json)")
    print("")

def main():
    parser = argparse.ArgumentParser(description="Experiment & Run Version Manager")
    subparsers = parser.add_subparsers(dest="command")
    
    # Init command
    p_init = subparsers.add_parser("init", help="Initialize next iterated run folder")
    p_init.add_argument("--type", default="experiment", help="Run type (e.g. mini_validation, master_20h, ablative)")
    p_init.add_argument("--desc", default="", help="Description of run")
    p_init.add_argument("--run-dir", default=DEFAULT_RUNS_DIR, help="Base directory for runs")
    p_init.add_argument("--bash", action="store_true", help="Output export statements for bash eval")
    
    # Complete command
    p_comp = subparsers.add_parser("complete", help="Mark run as completed")
    p_comp.add_argument("run_id", help="Run ID e.g. run_001")
    p_comp.add_argument("--status", default="completed", help="Final status")
    p_comp.add_argument("--run-dir", default=DEFAULT_RUNS_DIR, help="Base directory for runs")
    
    # List command
    p_list = subparsers.add_parser("list", help="List all runs")
    p_list.add_argument("--run-dir", default=DEFAULT_RUNS_DIR, help="Base directory for runs")
    
    # Next command
    p_next = subparsers.add_parser("next", help="Show next run ID")
    p_next.add_argument("--run-dir", default=DEFAULT_RUNS_DIR, help="Base directory for runs")
    
    args = parser.parse_args()
    
    if args.command == "init":
        meta = init_run(run_type=args.type, description=args.desc, base_dir=args.run_dir)
        if args.bash:
            print(f"export RUN_ID='{meta['run_id']}';")
            print(f"export RUN_DIR='{meta['paths']['root']}';")
            print(f"export DATA_DIR='{meta['paths']['data']}';")
            print(f"export MODELS_DIR='{meta['paths']['models']}';")
            print(f"export EVAL_DIR='{meta['paths']['eval']}';")
            print(f"export TRAINING_DATA='{meta['paths']['training_data']}';")
            print(f"export RUN_A_CSV='{meta['paths']['run_a_baseline']}';")
            print(f"export RUN_B_CSV='{meta['paths']['run_b_costbenefit']}';")
        else:
            print(json.dumps(meta, indent=2))
            
    elif args.command == "complete":
        complete_run(args.run_id, status=args.status, base_dir=args.run_dir)
        
    elif args.command == "list":
        list_runs(base_dir=args.run_dir)
        
    elif args.command == "next":
        num = get_next_run_number(base_dir=args.run_dir)
        print(f"run_{num:03d}")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
