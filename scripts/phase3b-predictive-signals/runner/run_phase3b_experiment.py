#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import urllib.request
import argparse
import csv

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
RESULTS_DIR = os.path.join(PHASE3B_DIR, "results")
CONFIG_DIR = os.path.join(PHASE3B_DIR, "config")
SPARK_EVENTS_DIR = os.path.join(PHASE3B_DIR, "spark-events")

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
    for i in range(15):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("127.0.0.1", 10000))
            s.close()
            time.sleep(1)
        except Exception:
            break
    print("Port 10000 is free.")

def start_thrift_server(mode):
    stop_thrift_server()
    time.sleep(1)
    
    rm_cmd = f"rm -rf '{SPARK_EVENTS_DIR}' && mkdir -p '{SPARK_EVENTS_DIR}'"
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
        "--conf", f"spark.eventLog.dir=file://{SPARK_EVENTS_DIR.replace(' ', '%20')}",
        "--hiveconf", "hive.server2.thrift.port=10000",
        "--hiveconf", "hive.server2.thrift.bind.host=127.0.0.1"
    ]
    
    if mode == "FIFO":
        cmd.extend(["--conf", "spark.scheduler.mode=FIFO"])
    elif mode == "FAIR":
        cmd.extend([
            "--conf", "spark.scheduler.mode=FAIR",
            "--conf", f"spark.scheduler.allocation.file={CONFIG_DIR}/fairscheduler.xml"
        ])
        
    subprocess.run(cmd, env=env, cwd=WORKSPACE_DIR, check=True)
    
    print("Waiting for Thrift Server to bind to port 10000...")
    for i in range(30):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("127.0.0.1", 10000))
            s.close()
            print("Thrift Server is online.")
            return True
        except Exception:
            time.sleep(2)
            
    raise TimeoutError("Thrift Server failed to bind to port 10000.")

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

def wait_for_compaction_to_start(app_id, port, timeout=60):
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
                            print(f"  Compaction job started: Job ID {job.get('jobId')}")
                            return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def reset_table(num_partitions):
    print(f"Resetting experimental table with {num_partitions} partitions...")
    sql_script = f"""
    DROP TABLE IF EXISTS local.experiment.interference_treatment;
    CREATE TABLE local.experiment.interference_treatment
    USING iceberg
    AS SELECT * FROM local.tpch.lineitem
    DISTRIBUTE BY (l_orderkey % {num_partitions});
    """
    beeline_cmd = [
        "beeline",
        "-u", "jdbc:hive2://127.0.0.1:10000/default",
        "-n", "anonymous",
        "-p", "",
        "-e", sql_script
    ]
    env = get_spark_env()
    subprocess.run(beeline_cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("Table reset complete.")

def get_pre_decision_system_metrics(sys_metrics_file):
    # Read the last few lines of sys_metrics_file to compute pre-decision averages
    if not os.path.exists(sys_metrics_file):
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    try:
        with open(sys_metrics_file, 'r') as f:
            lines = f.readlines()
        if len(lines) <= 1:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        last_lines = [l.strip().split(',') for l in lines[-5:] if len(l.strip().split(',')) >= 10]
        if not last_lines:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        cpus = [float(row[1]) for row in last_lines]
        mems = [float(row[5]) for row in last_lines]
        rbytes = [float(row[6]) for row in last_lines]
        wbytes = [float(row[7]) for row in last_lines]
        rios = [float(row[8]) for row in last_lines]
        wios = [float(row[9]) for row in last_lines]
        return (
            sum(cpus)/len(cpus), sum(mems)/len(mems),
            sum(rbytes)/len(rbytes), sum(wbytes)/len(wbytes),
            sum(rios)/len(rios), sum(wios)/len(wios)
        )
    except Exception as e:
        print(f"Warning reading pre-decision metrics: {e}")
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

def run_query(query_id, config_id, rep, run_type, pool):
    query_file = f"{WORKSPACE_DIR}/scripts/phase2-validated-layout-comparison/sql/query{query_id}_control.sql"
    with open(query_file, "r") as f:
        sql_text = f.read().replace("local.tpch.lineitem", "local.experiment.interference_treatment")
        
    job_group = f"Q{query_id}_{config_id}_rep{rep}_{run_type}"
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

def main():
    parser = argparse.ArgumentParser(description="Phase 3B Predictive Signals Experiment Harness")
    parser.add_argument("--repetitions-per-config", type=int, default=5, help="Repetitions per config (default: 5 = 1 warmup + 4 measured)")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    query_csv_path = os.path.join(RESULTS_DIR, "phase3b_query_runs.csv")
    comp_csv_path = os.path.join(RESULTS_DIR, "phase3b_compaction_runs.csv")
    pred_csv_path = os.path.join(RESULTS_DIR, "phase3b_pre_decision_signals.csv")
    sys_metrics_csv = os.path.join(RESULTS_DIR, "phase3b_system_metrics.csv")

    # Start system metrics collector daemon
    print("Starting system_metrics_collector background process...")
    sys_proc = subprocess.Popen([
        "python3", os.path.join(PHASE3B_DIR, "telemetry/system_metrics_collector.py"),
        "--output", sys_metrics_csv,
        "--interval", "1.0"
    ])
    time.sleep(2)

    query_file_obj = open(query_csv_path, "a" if os.path.exists(query_csv_path) else "w", newline="")
    comp_file_obj = open(comp_csv_path, "a" if os.path.exists(comp_csv_path) else "w", newline="")
    pred_file_obj = open(pred_csv_path, "a" if os.path.exists(pred_csv_path) else "w", newline="")

    query_writer = csv.writer(query_file_obj)
    comp_writer = csv.writer(comp_file_obj)
    pred_writer = csv.writer(pred_file_obj)

    if os.path.getsize(query_csv_path) == 0 if os.path.exists(query_csv_path) else True:
        query_writer.writerow(["config_id", "frag_files", "workload_type", "scheduler_mode", "repetition", "run_type", "query", "client_start_time", "client_end_time", "duration_ms"])
        query_file_obj.flush()
    if os.path.getsize(comp_csv_path) == 0 if os.path.exists(comp_csv_path) else True:
        comp_writer.writerow(["config_id", "frag_files", "workload_type", "scheduler_mode", "repetition", "client_start_time", "client_end_time", "duration_ms"])
        comp_file_obj.flush()
    if os.path.getsize(pred_csv_path) == 0 if os.path.exists(pred_csv_path) else True:
        pred_writer.writerow([
            "config_id", "repetition", "frag_files", "workload_type", "scheduler_mode",
            "table_size_mb", "avg_file_size_kb",
            "pre_cpu_util_pct", "pre_mem_used_pct", "pre_disk_read_bytes_sec", "pre_disk_write_bytes_sec", "pre_disk_read_iops", "pre_disk_write_iops", "decision_timestamp"
        ])
        pred_file_obj.flush()

    # 3-factor Parameter Matrix:
    # 1. Fragmentation Files: [50, 200, 500]
    # 2. Workload Type: ["single_stream" (Q14), "multi_stream" (Q1,Q3,Q6,Q12,Q14,Q18)]
    # 3. Scheduler Mode: ["FIFO", "FAIR"]
    frag_levels = [50, 200, 500]
    workload_types = ["single_stream", "multi_stream"]
    modes = ["FIFO", "FAIR"]

    try:
        for mode in modes:
            start_thrift_server(mode)
            time.sleep(2)
            app_id, ui_port = get_active_app_id_and_port()
            
            for frag in frag_levels:
                for wtype in workload_types:
                    config_id = f"frag{frag}_{wtype}_{mode}"
                    print(f"\n=========================================")
                    print(f"Executing Configuration: {config_id}")
                    print(f"=========================================")
                    
                    queries = ["14"] if wtype == "single_stream" else ["1", "3", "6", "12", "14", "18"]
                    
                    for rep in range(args.repetitions_per_config):
                        is_warmup = (rep == 0)
                        rep_label = f"Warmup {rep}" if is_warmup else f"Repetition {rep}"
                        print(f"\n--- {config_id} | {rep_label} ---")
                        
                        # Interleaved counterbalanced order
                        order = ["baseline", "concurrent"] if rep % 2 == 0 else ["concurrent", "baseline"]
                        
                        for run_type in order:
                            print(f"Starting {run_type.upper()} phase for {config_id}...")
                            reset_table(frag)
                            
                            if run_type == "baseline":
                                for q in queries:
                                    t0, t1, dur = run_query(q, config_id, rep, "baseline", "foreground")
                                    query_writer.writerow([config_id, frag, wtype, mode, rep, "baseline", f"Q{q}", t0, t1, dur])
                                    query_file_obj.flush()
                            else:
                                # Sample Pre-Decision Signals BEFORE launching compaction
                                print("Sampling pre-decision system resource signals...")
                                cpu_p, mem_p, rbytes_p, wbytes_p, rios_p, wios_p = get_pre_decision_system_metrics(sys_metrics_csv)
                                table_mb = 145.0 # ~145 MB lineitem subset table
                                avg_file_kb = (table_mb * 1024.0) / frag
                                dec_time = time.time()
                                
                                pred_writer.writerow([
                                    config_id, rep, frag, wtype, mode,
                                    f"{table_mb:.2f}", f"{avg_file_kb:.2f}",
                                    f"{cpu_p:.2f}", f"{mem_p:.2f}", f"{rbytes_p:.0f}", f"{wbytes_p:.0f}", f"{rios_p:.1f}", f"{wios_p:.1f}", f"{dec_time:.3f}"
                                ])
                                pred_file_obj.flush()
                                
                                print("Launching background Iceberg compaction rewrite...")
                                comp_cmd = [
                                    "beeline",
                                    "-u", "jdbc:hive2://127.0.0.1:10000/default",
                                    "-n", "anonymous",
                                    "-p", "",
                                    "-e", f"SET spark.scheduler.pool=background; SET spark.jobGroup.id=comp_{config_id}_rep{rep}; CALL local.system.rewrite_data_files(table => 'local.experiment.interference_treatment')"
                                ]
                                t_comp_start = time.time()
                                env = get_spark_env()
                                comp_proc = subprocess.Popen(comp_cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                
                                wait_for_compaction_to_start(app_id, ui_port)
                                
                                for q in queries:
                                    t0, t1, dur = run_query(q, config_id, rep, "concurrent", "foreground")
                                    query_writer.writerow([config_id, frag, wtype, mode, rep, "concurrent", f"Q{q}", t0, t1, dur])
                                    query_file_obj.flush()
                                    
                                comp_proc.wait()
                                t_comp_end = time.time()
                                comp_dur = (t_comp_end - t_comp_start) * 1000.0
                                print(f"Background compaction finished in {comp_dur:.2f} ms")
                                comp_writer.writerow([config_id, frag, wtype, mode, rep, t_comp_start, t_comp_end, comp_dur])
                                comp_file_obj.flush()
                            
                            # 5-second cooling period between phases
                            time.sleep(5)
                            
            stop_thrift_server()
            
    finally:
        query_file_obj.close()
        comp_file_obj.close()
        pred_file_obj.close()
        sys_proc.terminate()
        stop_thrift_server()
        print("\nPhase 3B Parameter Sweep Experiment Harness Execution Finished.")

if __name__ == "__main__":
    main()
