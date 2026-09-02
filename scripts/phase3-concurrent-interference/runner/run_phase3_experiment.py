import os
import sys
import time
import json
import subprocess
import urllib.request
import argparse
import csv

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"

def get_spark_env():
    env = os.environ.copy()
    spark_home = f"{WORKSPACE_DIR}/software/spark-3.3.4"
    env["JAVA_HOME"] = "/usr/lib/jvm/java-11-openjdk-amd64"
    env["SPARK_HOME"] = spark_home
    env["SPARK_LOG_DIR"] = "/tmp"
    env["SPARK_LOCAL_IP"] = "127.0.0.1"
    env["SPARK_LOCAL_HOSTNAME"] = "localhost"
    env["PYTHONPATH"] = f"{spark_home}/python:{spark_home}/python/lib/py4j-0.10.9.5-src.zip:{env.get('PYTHONPATH', '')}"
    env["PATH"] = f"{spark_home}/bin:{env.get('PATH', '')}"
    return env

def stop_thrift_server():
    print("Stopping Spark Thrift Server...")
    env = get_spark_env()
    subprocess.run([f"{WORKSPACE_DIR}/software/spark-3.3.4/sbin/stop-thriftserver.sh"], env=env, cwd=WORKSPACE_DIR, capture_output=True)
    
    # Wait for port 10000 to be released
    print("Waiting for port 10000 to be released...")
    for i in range(15):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("127.0.0.1", 10000))
            s.close()
            # Port is still bound, sleep and retry
            time.sleep(1)
        except Exception:
            # Port is free
            break
    print("Port 10000 is free.")

def start_thrift_server(mode):
    # Ensure server is stopped first
    stop_thrift_server()
    time.sleep(1)
    
    # Create and clean spark event log directory
    event_log_dir = f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/spark-events"
    rm_cmd = f"rm -rf '{event_log_dir}' && mkdir -p '{event_log_dir}'"
    subprocess.run(rm_cmd, shell=True, check=True)
        
    print(f"Starting Spark Thrift Server in {mode} mode...")
    env = get_spark_env()
    
    cmd = [
        f"{WORKSPACE_DIR}/software/spark-3.3.4/sbin/start-thriftserver.sh",
        "--driver-memory", "4g",
        "--conf", "spark.driver.host=127.0.0.1",
        "--conf", "spark.driver.bindAddress=127.0.0.1",
        "--conf", "spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        "--conf", "spark.sql.catalog.local=org.apache.iceberg.spark.SparkCatalog",
        "--conf", "spark.sql.catalog.local.type=hadoop",
        "--conf", f"spark.sql.catalog.local.warehouse=file://{WORKSPACE_DIR}/warehouse",
        "--conf", "spark.eventLog.enabled=true",
        "--conf", f"spark.eventLog.dir=file://{event_log_dir.replace(' ', '%20')}",
        "--hiveconf", "hive.server2.thrift.port=10000",
        "--hiveconf", "hive.server2.thrift.bind.host=127.0.0.1"
    ]
    
    if mode == "FIFO":
        cmd.extend(["--conf", "spark.scheduler.mode=FIFO"])
    elif mode == "FAIR":
        cmd.extend([
            "--conf", "spark.scheduler.mode=FAIR",
            "--conf", "spark.scheduler.allocation.file=scripts/phase3-concurrent-interference/config/fairscheduler.xml"
        ])
        
    subprocess.run(cmd, env=env, cwd=WORKSPACE_DIR, check=True)
    
    # Wait for server to bind to port 10000
    print("Waiting for Thrift Server to bind to port 10000...")
    for i in range(30):
        try:
            # Simple socket check
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("127.0.0.1", 10000))
            s.close()
            print("Thrift Server is online.")
            return True
        except Exception:
            time.sleep(2)
            
    # On timeout, print logs for debugging
    print("Error: Thrift Server failed to bind. Printing log files in /tmp:")
    try:
        for f in os.listdir("/tmp"):
            if f.startswith("spark-") and f.endswith(".out"):
                log_path = os.path.join("/tmp", f)
                print(f"=== Log: {log_path} ===")
                with open(log_path, "r") as lf:
                    lines = lf.readlines()
                    for line in lines[-50:]:
                        print(line.rstrip())
    except Exception as le:
        print(f"Could not read logs: {le}")
        
    raise TimeoutError("Thrift Server failed to bind to port 10000 in 60 seconds.")

def get_active_app_id_and_port():
    for port in range(4040, 4046):
        try:
            url = f"http://127.0.0.1:{port}/api/v1/applications"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    apps = json.loads(response.read().decode())
                    if apps:
                        return apps[0]["id"], port
        except Exception:
            continue
    return None, None

def wait_for_compaction_to_start(app_id, port, rep, timeout=60):
    url = f"http://127.0.0.1:{port}/api/v1/applications/{app_id}/jobs"
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    jobs = json.loads(response.read().decode())
                    for job in jobs:
                        if job.get("status") == "RUNNING" or job.get("numActiveTasks", 0) > 0:
                            print(f"Compaction job started: Job ID {job.get('jobId')} (Name: {job.get('name')})")
                            return True
        except Exception:
            pass
        time.sleep(0.5)
    print("Warning: Timeout waiting for compaction to start.")
    return False

def reset_table():
    print("Resetting table to 200-partition fragmented state...")
    env = get_spark_env()
    subprocess.run([
        "python3", 
        f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/preparation/create_interference_tables.py"
    ], env=env, check=True)

def run_query(query_id, rep, run_type, pool):
    query_file = f"{WORKSPACE_DIR}/scripts/phase2-validated-layout-comparison/sql/query{query_id}_control.sql"
    with open(query_file, "r") as f:
        sql_text = f.read().replace("local.tpch.lineitem", "local.experiment.interference_treatment")
        
    job_group = f"Q{query_id}_rep{rep}_{run_type}"
    beeline_cmd = [
        "beeline",
        "-u", "jdbc:hive2://127.0.0.1:10000/default",
        "-n", "anonymous",
        "-p", "",
        "-e", f"SET spark.scheduler.pool={pool}; SET spark.jobGroup.id={job_group}; {sql_text}"
    ]
    
    t0 = time.time()
    env = get_spark_env()
    subprocess.run(beeline_cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    t1 = time.time()
    
    duration_ms = (t1 - t0) * 1000.0
    print(f"  Query Q{query_id} ({run_type}) finished in {duration_ms:.2f} ms")
    return t0, t1, duration_ms

def execute_experiment(mode, repetitions, query_runs_file, compaction_runs_file):
    query_runs_writer = csv.writer(query_runs_file)
    compaction_runs_writer = csv.writer(compaction_runs_file)
    
    print(f"\n=========================================")
    print(f"Starting Experiment: Scheduler Mode = {mode}")
    print(f"=========================================")
    
    start_thrift_server(mode)
    time.sleep(3)
    
    app_id, ui_port = get_active_app_id_and_port()
    print(f"Active Spark App ID: {app_id} on port {ui_port}")
    
    queries = ["1", "3", "6", "12", "14", "18"]
    
    for rep in range(repetitions):
        is_warmup = rep < 2
        rep_label = f"Warmup {rep}" if is_warmup else f"Repetition {rep}"
        print(f"\n--- {rep_label} ---")
        
        # Determine counterbalanced ordering
        # Cycle: A (Baseline) -> B (Concurrent) or B -> A
        if rep % 2 == 0:
            order = ["baseline", "concurrent"]
        else:
            order = ["concurrent", "baseline"]
            
        for run_type in order:
            print(f"\nStarting {run_type.upper()} phase...")
            reset_table()
            
            if run_type == "baseline":
                for q in queries:
                    t_start, t_end, dur = run_query(q, rep, "baseline", "foreground")
                    query_runs_writer.writerow([
                        mode, rep, "baseline", f"Q{q}", t_start, t_end, dur, "none"
                    ])
                    query_runs_file.flush()
            else:
                # Concurrent Phase: Start background rewrite
                print("Launching background Iceberg compaction rewrite...")
                compaction_cmd = [
                    "beeline",
                    "-u", "jdbc:hive2://127.0.0.1:10000/default",
                    "-n", "anonymous",
                    "-p", "",
                    "-e", f"SET spark.scheduler.pool=background; SET spark.jobGroup.id=compaction_rep{rep}; CALL local.system.rewrite_data_files(table => 'local.experiment.interference_treatment')"
                ]
                
                t_comp_start = time.time()
                env = get_spark_env()
                comp_proc = subprocess.Popen(compaction_cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Wait for compaction task execution to begin
                wait_for_compaction_to_start(app_id, ui_port, rep)
                
                # Run foreground queries
                for q in queries:
                    t_start, t_end, dur = run_query(q, rep, "concurrent", "foreground")
                    query_runs_writer.writerow([
                        mode, rep, "concurrent", f"Q{q}", t_start, t_end, dur, "concurrent"
                    ])
                    query_runs_file.flush()
                    
                # Wait for compaction to finish
                comp_proc.wait()
                t_comp_end = time.time()
                comp_dur = (t_comp_end - t_comp_start) * 1000.0
                print(f"Background compaction finished in {comp_dur:.2f} ms")
                compaction_runs_writer.writerow([
                    mode, rep, t_comp_start, t_comp_end, comp_dur
                ])
                compaction_runs_file.flush()

def main():
    parser = argparse.ArgumentParser(description="Phase 3A Concurrent Workload Interference Experiment Runner")
    parser.add_argument("--repetitions", type=int, default=12, help="Number of repetitions including 2 warmups (default: 12)")
    parser.add_argument("--fifo-only", action="store_true", help="Run only the FIFO scheduling mode")
    parser.add_argument("--fair-only", action="store_true", help="Run only the FAIR scheduling mode")
    args = parser.parse_args()
    
    os.makedirs(f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/results", exist_ok=True)
    
    query_csv_path = f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/results/query_runs.csv"
    comp_csv_path = f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/results/compaction_runs.csv"
    
    query_file_exists = os.path.exists(query_csv_path) and os.path.getsize(query_csv_path) > 0
    comp_file_exists = os.path.exists(comp_csv_path) and os.path.getsize(comp_csv_path) > 0
    
    query_runs_file = open(query_csv_path, "a" if query_file_exists else "w", newline="")
    compaction_runs_file = open(comp_csv_path, "a" if comp_file_exists else "w", newline="")
    
    query_writer = csv.writer(query_runs_file)
    comp_writer = csv.writer(compaction_runs_file)
    
    if not query_file_exists:
        query_writer.writerow([
            "scheduler_mode", "repetition", "run_type", "query", 
            "client_start_time", "client_end_time", "client_duration_ms", "overlap_type"
        ])
        query_runs_file.flush()
        
    if not comp_file_exists:
        comp_writer.writerow([
            "scheduler_mode", "repetition", "client_start_time", "client_end_time", "client_duration_ms"
        ])
        compaction_runs_file.flush()
    
    modes = []
    if args.fifo_only:
        modes = ["FIFO"]
    elif args.fair_only:
        modes = ["FAIR"]
    else:
        modes = ["FIFO", "FAIR"]
        
    try:
        # Reset table first to ensure it's in the fragmented pre-state
        reset_table()
        
        # Pre-experiment layout validation
        print("Running pre-experiment layouts validation...")
        env = get_spark_env()
        subprocess.run([
            "python3", 
            f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/preparation/validate_state.py", 
            "--mode", "pre"
        ], env=env, check=True)
        
        for mode in modes:
            execute_experiment(mode, args.repetitions, query_runs_file, compaction_runs_file)
            
        print("\nAll experiments finished successfully.")
        
        # Post-experiment layout validation
        print("Running post-experiment layouts validation...")
        subprocess.run([
            "python3", 
            f"{WORKSPACE_DIR}/scripts/phase3-concurrent-interference/preparation/validate_state.py", 
            "--mode", "post"
        ], env=env, check=True)
        
    finally:
        query_runs_file.close()
        compaction_runs_file.close()
        stop_thrift_server()
        
if __name__ == "__main__":
    main()
