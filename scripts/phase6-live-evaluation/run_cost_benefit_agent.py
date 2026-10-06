#!/usr/bin/env python3
import os
import sys
import json
import time
import argparse
import threading
import psutil
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from collections import deque

sys.path.append(os.path.abspath('scripts/phase5-adaptive-scheduling-agent'))
sys.path.append(os.path.abspath('scripts/phase6-live-evaluation'))

from google_trace_mapper import GoogleTraceMapper
from policies.sota_threshold_policy import SOTAThresholdPolicy
from collect_training_data import WorkloadDriver, WriteDriver, fetch_table_metadata

try:
    from pyhive import hive
    PYHIVE_AVAILABLE = True
except ImportError:
    PYHIVE_AVAILABLE = False

class CostBenefitPolicy:
    def __init__(self, model_dir="scripts/phase6-live-evaluation/models"):
        print(f"Loading models from {model_dir}...")
        self.model_a = joblib.load(f"{model_dir}/model_a_compaction.joblib")
        self.model_b = joblib.load(f"{model_dir}/model_b_baseline.joblib")
        
        with open(f"{model_dir}/model_metadata.json", "r") as f:
            self.metadata = json.load(f)
            
        self.features = self.metadata["features"]
        self.q_a = self.metadata["model_a"]["q_hat"]
        self.q_b = self.metadata["model_b"]["q_hat"]
        
    def decide(self, telemetry: dict):
        df = pd.DataFrame([telemetry])
        
        # Predict C_compact
        X_a = df[self.features]
        pred_a = self.model_a.predict(X_a)[0]
        c_compact = pred_a + self.q_a
        
        # Predict C_defer (projected +2 files due to writes)
        df_defer = df.copy()
        df_defer['frag_file_count'] = df_defer['frag_file_count'] + 2.0
        X_b = df_defer[self.features]
        pred_b = self.model_b.predict(X_b)[0]
        c_defer = pred_b + self.q_b
        
        decision = "RUN" if c_compact < c_defer else "DEFER"
        return decision, c_compact, c_defer

def parse_args():
    parser = argparse.ArgumentParser(description="Phase 6C Cost-Benefit Agent Daemon")
    parser.add_argument("--policy", type=str, required=True, choices=["SOTAThresholdPolicy", "CostBenefitPolicy"])
    parser.add_argument("--table", type=str, default="local.tpch_sf100.lineitem", help="Target Iceberg table")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Spark Thrift Server host")
    parser.add_argument("--port", type=int, default=10000, help="Spark Thrift Server port")
    parser.add_argument("--duration-hours", type=float, default=8.0, help="Total test duration in hours")
    parser.add_argument("--output", type=str, required=True, help="Output CSV path")
    return parser.parse_args()

def main():
    args = parse_args()
    
    if not PYHIVE_AVAILABLE:
        print("ERROR: PyHive is not available. CANNOT run in simulation mode.")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    print(f"=== Starting Phase 6C Live Agent Evaluation ===")
    print(f"  Policy:           {args.policy}")
    print(f"  Target Table:     {args.table}")
    print(f"  Duration:         {args.duration_hours} hours")
    print(f"  Output File:      {args.output}")

    if args.policy == "SOTAThresholdPolicy":
        policy = SOTAThresholdPolicy(frag_file_threshold=200, min_file_size_mb=16.0)
    else:
        policy = CostBenefitPolicy()

    trace_mapper = GoogleTraceMapper(test_duration_hours=args.duration_hours)
    read_driver = WorkloadDriver(host=args.host, port=args.port, table=args.table, trace_mapper=trace_mapper)
    write_driver = WriteDriver(host=args.host, port=args.port, table=args.table, trace_mapper=trace_mapper)

    # Write CSV Header
    header = ("timestamp,elapsed_s,policy,decision,frag_file_count,table_size_mb,"
              "c_compact,c_defer,p95_query_latency_ms,rolling_sla_violation_rate,"
              "compaction_duration_s,regime,intensity\n")
    with open(args.output, "w") as f:
        f.write(header)

    start_time = time.time()
    max_test_seconds = args.duration_hours * 3600.0
    
    read_driver.start(start_time)
    write_driver.start(start_time)

    cpu_history = deque(maxlen=300)
    
    try:
        while True:
            t_start_loop = time.time()
            elapsed_s = t_start_loop - start_time
            if elapsed_s >= max_test_seconds:
                print(f"\nCompleted target duration of {args.duration_hours} hours. Stopping.")
                break

            t_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            regime = trace_mapper.get_regime(elapsed_s)
            intensity = trace_mapper.get_intensity(elapsed_s)

            # Gather Telemetry for decision making
            cpu_pct = psutil.cpu_percent(interval=None)
            cpu_history.append(cpu_pct)
            cpu_1min = np.mean(list(cpu_history)[-60:]) if len(cpu_history) > 0 else cpu_pct
            cpu_5min = np.mean(cpu_history) if len(cpu_history) > 0 else cpu_pct
            cpu_trend = cpu_1min - cpu_5min
            mem_pct = psutil.virtual_memory().percent

            table_metadata = fetch_table_metadata(args.host, args.port, args.table)
            frag_count = table_metadata["frag_file_count"]
            table_size = table_metadata["table_size_mb"]
            avg_file_kb = (table_size * 1024.0 / frag_count) if frag_count > 0 else 0.0

            telemetry = {
                "cpu_util_avg_1min": cpu_1min,
                "cpu_util_avg_5min": cpu_5min,
                "cpu_trend": cpu_trend,
                "mem_used_pct": mem_pct,
                "frag_file_count": frag_count,
                "table_size_mb": table_size,
                "avg_file_size_kb": avg_file_kb,
                "intensity": intensity
            }

            # Decide
            if args.policy == "SOTAThresholdPolicy":
                decision = policy.decide(table_metadata, 0, 0, None)
                c_compact = 0.0
                c_defer = 0.0
            else:
                decision, c_compact, c_defer = policy.decide(telemetry)

            print(f"[{t_now}] [{regime} {intensity:.2f}] {args.policy} -> {decision} | Files: {frag_count} | C_compact: {c_compact:.1f} | C_defer: {c_defer:.1f}")

            compaction_duration = 0.0
            if decision == "RUN":
                print(f"[{t_now}] >>> EXECUTING COMPACTION ON {args.table} <<<")
                c_start = time.time()
                try:
                    conn = hive.Connection(host=args.host, port=args.port, username="ccbd")
                    cursor = conn.cursor()
                    cursor.execute(f"CALL local.system.rewrite_data_files(table => '{args.table}')")
                    cursor.fetchall()
                    cursor.close()
                    conn.close()
                    compaction_duration = time.time() - c_start
                    print(f"[{t_now}] Compaction completed in {compaction_duration:.2f}s")
                except Exception as err:
                    compaction_duration = time.time() - c_start
                    print(f"[{t_now}] Compaction error ({compaction_duration:.2f}s): {err}")

            # Get Driver Stats (SLA violations and P95 latency)
            with read_driver.lock:
                recent = list(read_driver.completed_queries)
                p95_lat = np.percentile(recent, 95) if len(recent) > 0 else 0.0
                violations = sum(1 for x in recent if x > 492.0)
                sla_rate = (violations / len(recent) * 100.0) if len(recent) > 0 else 0.0
                read_driver.completed_queries.clear() # Reset for next 60s window

            # Log step to CSV
            with open(args.output, "a") as f:
                f.write(f"{t_now},{elapsed_s:.1f},{args.policy},{decision},{frag_count},{table_size:.1f},"
                        f"{c_compact:.2f},{c_defer:.2f},{p95_lat:.2f},{sla_rate:.2f},"
                        f"{compaction_duration:.2f},{regime},{intensity:.3f}\n")

            time.sleep(60.0) # Tick every 60 seconds for decision

    except KeyboardInterrupt:
        print("\nEvaluation daemon interrupted by user.")
    finally:
        read_driver.stop()
        write_driver.stop()
        print(f"=== Finished Phase 6C Evaluation ({args.output}) ===")

if __name__ == "__main__":
    main()
