#!/usr/bin/env python3
import subprocess
import time
import sys
import os

WORKSPACE_DIR = "/media/shashank/Data1/PDocuments/Capstone/implementation"
PHASE3B_RUNNER_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals/runner")
sys.path.append(PHASE3B_RUNNER_DIR)

from run_phase3b_experiment import start_thrift_server, stop_thrift_server, get_spark_env

PHASE4_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase4-temporal-workload-model")
COLLECTOR_SCRIPT = os.path.join(PHASE4_DIR, "telemetry/unified_telemetry_collector.py")
RESULTS_DIR = os.path.join(PHASE4_DIR, "results")

def run_query(q_id="14"):
    q_path = os.path.join(WORKSPACE_DIR, f"scripts/phase2-validated-layout-comparison/sql/query{q_id}_control.sql")
    with open(q_path, "r") as f:
        sql = f.read()
    
    cmd = [
        "beeline",
        "-u", "jdbc:hive2://127.0.0.1:10000/default",
        "-n", "anonymous",
        "-p", "",
        "-f", q_path
    ]
    env = get_spark_env()
    print(f"Running Q{q_id}...")
    subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
    print("Resetting table (200 partitions)...")
    subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("Starting Phase 4 Temporal Telemetry Validation Dry-Run...")
    start_thrift_server("FIFO")
    
    csv_out = os.path.join(RESULTS_DIR, "validation_telemetry.csv")
    if os.path.exists(csv_out):
        os.remove(csv_out)
        
    print("Launching Unified Telemetry Collector daemon...")
    collector_proc = subprocess.Popen([
        "python3", COLLECTOR_SCRIPT,
        "--output", csv_out,
        "--interval", "1.0"
    ], env=os.environ.copy(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    try:
        # Give collector a second to initialize
        time.sleep(2)
        
        reset_table()
        time.sleep(5)
        
        run_query("14")
        time.sleep(10)
        
        run_query("1")
        time.sleep(5)
        
        print("Dry run complete. Validating telemetry output...")
    finally:
        collector_proc.terminate()
        stop_thrift_server()
        
    # Validation
    with open(csv_out, "r") as f:
        lines = f.readlines()
        if len(lines) > 1:
            print(f"\nSUCCESS: Generated {len(lines)-1} telemetry rows at 1Hz.")
            print(f"Schema Headers: {lines[0].strip()}")
            print(f"Sample Row: {lines[-1].strip()}")
        else:
            print("\nFAILURE: No telemetry rows generated.")

if __name__ == "__main__":
    main()
