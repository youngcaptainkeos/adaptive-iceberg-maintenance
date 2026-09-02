#!/usr/bin/env python3
import os
import sys
import csv

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
RESULTS_DIR = os.path.join(PHASE3B_DIR, "results")

def build_dataset():
    query_csv = os.path.join(RESULTS_DIR, "phase3b_query_runs.csv")
    comp_csv = os.path.join(RESULTS_DIR, "phase3b_compaction_runs.csv")
    pred_csv = os.path.join(RESULTS_DIR, "phase3b_pre_decision_signals.csv")
    out_dataset_csv = os.path.join(RESULTS_DIR, "dataset_predictive_signals.csv")

    if not os.path.exists(query_csv) or not os.path.exists(pred_csv):
        print("Error: Input CSVs missing in results directory.")
        return

    # Load pre-decision signals: key = (config_id, repetition)
    pred_signals = {}
    with open(pred_csv, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rep = int(r["repetition"])
            if rep > 0: # Filter out warmup rep 0
                key = (r["config_id"], rep)
                pred_signals[key] = r

    # Load query runs
    base_runs = {} # (config_id, repetition, query) -> duration_ms
    conc_runs = [] # list of conc run dicts
    with open(query_csv, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rep = int(r["repetition"])
            if rep == 0:
                continue
            config_id = r["config_id"]
            query = r["query"]
            dur = float(r["duration_ms"])
            run_type = r["run_type"]

            if run_type == "baseline":
                base_runs[(config_id, rep, query)] = dur
            elif run_type == "concurrent":
                conc_runs.append({
                    "config_id": config_id,
                    "repetition": rep,
                    "query": query,
                    "concurrent_duration_ms": dur,
                    "client_start_time": float(r["client_start_time"]),
                    "client_end_time": float(r["client_end_time"])
                })

    dataset = []
    for conc in conc_runs:
        config_id = conc["config_id"]
        rep = conc["repetition"]
        query = conc["query"]
        key = (config_id, rep)

        if (config_id, rep, query) not in base_runs:
            continue
        if key not in pred_signals:
            continue

        base_dur = base_runs[(config_id, rep, query)]
        conc_dur = conc["concurrent_duration_ms"]

        # Compute paired QIR (%) per trial repetition
        qir_pct = ((conc_dur - base_dur) / base_dur) * 100.0
        sla_violation_10pct = 1 if qir_pct > 10.0 else 0

        p = pred_signals[key]

        row = {
            "config_id": config_id,
            "repetition": rep,
            "query": query,

            # --- Pre-Decision Signals (X_pred: Usable for Scheduling Policy) ---
            "frag_files": float(p["frag_files"]),
            "workload_type": p["workload_type"],
            "scheduler_mode": p["scheduler_mode"],
            "table_size_mb": float(p["table_size_mb"]),
            "avg_file_size_kb": float(p["avg_file_size_kb"]),
            "pre_cpu_util_pct": float(p["pre_cpu_util_pct"]),
            "pre_mem_used_pct": float(p["pre_mem_used_pct"]),
            "pre_disk_read_bytes_sec": float(p["pre_disk_read_bytes_sec"]),
            "pre_disk_write_bytes_sec": float(p["pre_disk_write_bytes_sec"]),
            "pre_disk_read_iops": float(p["pre_disk_read_iops"]),
            "pre_disk_write_iops": float(p["pre_disk_write_iops"]),
            "baseline_duration_ms": base_dur,

            # --- Offline Evaluation Telemetry (X_eval: Offline Analysis Only) ---
            "concurrent_duration_ms": conc_dur,
            "client_start_time_concurrent": conc["client_start_time"],
            "client_end_time_concurrent": conc["client_end_time"],

            # --- Targets (Y) ---
            "qir_pct": qir_pct,
            "sla_violation_10pct": sla_violation_10pct
        }
        dataset.append(row)

    if not dataset:
        print("Error: No paired dataset rows could be generated.")
        return

    fieldnames = list(dataset[0].keys())
    with open(out_dataset_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dataset)

    print(f"Predictive dataset successfully created with {len(dataset)} paired samples across {len(set(d['config_id'] for d in dataset))} configurations.")
    print(f"Saved to: {out_dataset_csv}")

if __name__ == "__main__":
    build_dataset()
