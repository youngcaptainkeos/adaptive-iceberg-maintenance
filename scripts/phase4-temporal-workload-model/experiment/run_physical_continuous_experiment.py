import os
import sys
import time
import csv
import threading
import subprocess
import argparse
import random

import os
WORKSPACE_DIR = os.environ.get("REPO_DIR", "/media/shashank/Data1/PDocuments/Capstone/implementation")
PHASE3B_RUNNER_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals/runner")
sys.path.append(PHASE3B_RUNNER_DIR)

from run_phase3b_experiment import start_thrift_server, stop_thrift_server, get_spark_env

PHASE4_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase4-temporal-workload-model")
sys.path.append(os.path.join(PHASE4_DIR, "workload"))
from workload_regime_controller import WorkloadRegimeController

COLLECTOR_SCRIPT = os.path.join(PHASE4_DIR, "telemetry/unified_telemetry_collector.py")
RESULTS_DIR = os.path.join(PHASE4_DIR, "results")
QUERIES_CSV = os.path.join(RESULTS_DIR, "physical_queries.csv")

# Global locks and lists for thread-safe logging
query_log_lock = threading.Lock()
query_logs = []

# Concurrency cap to prevent 16GB RAM from overflowing with JVMs
concurrency_cap = threading.Semaphore(8)

def run_beeline_query(q_id, q_type, regime, start_time_actual):
    # Depending on query type, pick a random query
    # If READ, pick from Q1, Q3, Q6, Q12, Q14, Q18
    # Actually Q1 is a long read, Q14 is short
    if q_type == "READ":
        real_q_id = random.choice([1, 3, 6, 12, 14, 18])
    else:
        # If UPDATE, use Q14 as proxy or a heavy read
        real_q_id = 14

    q_path = os.path.join(WORKSPACE_DIR, f"scripts/phase2-validated-layout-comparison/sql/query{real_q_id}_control.sql")
    
    cmd = [
        "beeline",
        "-u", "jdbc:hive2://127.0.0.1:10000/default",
        "-n", "anonymous",
        "-p", "",
        "-f", q_path
    ]
    env = get_spark_env()
    
    # Block until a slot is free to prevent JVM OOM
    concurrency_cap.acquire()
    t0 = time.time()
    try:
        subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        status = "SUCCESS"
    except subprocess.CalledProcessError:
        status = "FAILED"
    finally:
        concurrency_cap.release()
        
    t1 = time.time()
    
    duration_ms = (t1 - t0) * 1000
    
    with query_log_lock:
        query_logs.append({
            "query_start_time": t0,
            "query_end_time": t1,
            "query_duration_ms": duration_ms,
            "regime": regime,
            "query_type": q_type,
            "query_id": real_q_id,
            "status": status
        })

def run_compaction():
    print(f"[{time.strftime('%H:%M:%S')}] Triggering background Iceberg compaction...")
    sql = "CALL local.system.rewrite_data_files('local.experiment.interference_treatment');"
    cmd = [
        "beeline",
        "-u", "jdbc:hive2://127.0.0.1:10000/default",
        "-n", "anonymous",
        "-p", "",
        "-e", sql
    ]
    env = get_spark_env()
    try:
        subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"[{time.strftime('%H:%M:%S')}] Compaction finished successfully.")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Compaction failed: {e}")

def flush_logs():
    with query_log_lock:
        if not query_logs:
            return
        
        file_exists = os.path.exists(QUERIES_CSV)
        with open(QUERIES_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "query_start_time", "query_end_time", "query_duration_ms", 
                "regime", "query_type", "query_id", "status"
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerows(query_logs)
            
        query_logs.clear()

def reset_table():
    sql = """
    DROP TABLE IF EXISTS local.experiment.interference_treatment;
    CREATE TABLE local.experiment.interference_treatment
    USING iceberg
    AS SELECT * FROM local.tpch.lineitem
    DISTRIBUTE BY (l_orderkey % 200);
    """
    cmd = [
        "beeline",
        "-u", "jdbc:hive2://127.0.0.1:10000/default",
        "-n", "anonymous",
        "-p", "",
        "-e", sql
    ]
    env = get_spark_env()
    print("Resetting Iceberg table to baseline 200 partitions...")
    subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("Table reset complete.")

def main():
    parser = argparse.ArgumentParser(description="Phase 4 Physical Continuous Experiment")
    parser.add_argument("--duration-hours", type=float, default=4.0, help="Duration in hours")
    parser.add_argument("--compaction-min", type=float, default=1200, help="Min time between compactions in seconds")
    parser.add_argument("--compaction-max", type=float, default=2400, help="Max time between compactions in seconds")
    args = parser.parse_args()
    
    total_duration_sec = args.duration_hours * 3600
    
    print(f"Starting Phase 4 Continuous Physical Experiment for {args.duration_hours} hours...")
    
    # 1. Start Thrift Server
    start_thrift_server("FAIR")
    
    # 2. Reset table
    reset_table()
    
    csv_out = os.path.join(RESULTS_DIR, "physical_telemetry.csv")
    if os.path.exists(csv_out):
        os.remove(csv_out)
    if os.path.exists(QUERIES_CSV):
        os.remove(QUERIES_CSV)
        
    # 3. Start unified telemetry collector
    print("Starting background telemetry collector (1Hz)...")
    collector_proc = subprocess.Popen([
        "python3", COLLECTOR_SCRIPT,
        "--output", csv_out,
        "--interval", "1.0"
    ], env=os.environ.copy(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 4. Main simulation loop
    controller = WorkloadRegimeController(seed=42)
    start_real_time = time.time()
    
    # Init controller
    controller.start(0.0)
    
    rng = random.Random(123)
    
    last_checkpoint = start_real_time
    
    # Deterministic scheduling for first compaction
    next_compaction_time = start_real_time + rng.uniform(args.compaction_min, args.compaction_max)
    
    threads = []
    
    try:
        while True:
            current_real_time = time.time()
            elapsed = current_real_time - start_real_time
            
            if elapsed >= total_duration_sec:
                break
                
            # Update regime
            if controller.update_regime(elapsed):
                print(f"[{time.strftime('%H:%M:%S')}] Regime Transitioned to {controller.get_current_regime_name()}")
                
            rate = controller.get_current_rate()
            # NHPP Inter-arrival time (exponential)
            inter_arrival = rng.expovariate(rate)
            
            # Since this is real time, we actually sleep the inter-arrival time
            # But we break it up into small chunks to allow checking limits/compactions
            sleep_chunks = max(1, int(inter_arrival / 0.5))
            sleep_time = inter_arrival / sleep_chunks
            
            for _ in range(sleep_chunks):
                time.sleep(sleep_time)
                
                # Checkpoints
                if time.time() - last_checkpoint > 1800: # 30 mins
                    print(f"[{time.strftime('%H:%M:%S')}] Checkpointing logs...")
                    flush_logs()
                    last_checkpoint = time.time()
                    
                # Background Compaction
                if time.time() > next_compaction_time:
                    threading.Thread(target=run_compaction, daemon=True).start()
                    # Schedule next compaction
                    next_compaction_time = time.time() + rng.uniform(args.compaction_min, args.compaction_max)
                    
            # After sleeping inter-arrival, spawn a query
            q_type = "READ" if rng.random() < 0.7 else "UPDATE"
            t = threading.Thread(target=run_beeline_query, args=(0, q_type, controller.get_current_regime_name(), time.time()))
            t.daemon = True
            t.start()
            threads.append(t)
            
            # Cleanup finished threads list periodically to avoid memory leak
            if len(threads) > 100:
                threads = [th for th in threads if th.is_alive()]
                
    except KeyboardInterrupt:
        print("Experiment interrupted by user.")
    finally:
        print("Experiment duration reached. Waiting for final queries to complete (max 30s)...")
        # Wait up to 30s for threads to finish
        t_wait_start = time.time()
        while any(th.is_alive() for th in threads) and time.time() - t_wait_start < 30:
            time.sleep(1)
            
        print("Flushing final logs...")
        flush_logs()
        
        print("Terminating collector daemon...")
        collector_proc.terminate()
        
        print("Stopping Spark Thrift Server...")
        stop_thrift_server()
        
        print("Phase 4 Continuous Experiment Finished successfully.")

if __name__ == "__main__":
    main()
