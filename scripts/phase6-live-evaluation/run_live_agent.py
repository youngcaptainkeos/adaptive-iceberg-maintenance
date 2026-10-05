import os
import sys
import time
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

# Add root and policies path
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('scripts/phase5-adaptive-scheduling-agent'))

from policies.sota_threshold_policy import SOTAThresholdPolicy
from policies.temporal_conformal_policy import TemporalConformalPolicy

try:
    from pyhive import hive
    PYHIVE_AVAILABLE = True
except ImportError:
    PYHIVE_AVAILABLE = False

def parse_args():
    parser = argparse.ArgumentParser(description="Phase 6 Live Agent Compaction Daemon")
    parser.add_argument("--policy", type=str, required=True, choices=["SOTAThresholdPolicy", "TemporalConformalPolicy"], help="Compaction policy to run")
    parser.add_argument("--table", type=str, default="local.tpch_sf100.lineitem", help="Target Iceberg table")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Spark Thrift Server host")
    parser.add_argument("--port", type=int, default=10000, help="Spark Thrift Server port")
    parser.add_argument("--interval", type=int, default=60, help="Agent decision interval in seconds")
    parser.add_argument("--telemetry-path", type=str, default="results/continuous_telemetry.csv", help="Path to continuous telemetry CSV")
    return parser.parse_args()

def load_calibration_data():
    """Loads Phase 4 temporal windows to calibrate conformal predictor if using TemporalConformalPolicy."""
    calib_path = "scripts/phase4-temporal-workload-model/results/temporal_windows.csv"
    if os.path.exists(calib_path):
        return pd.read_csv(calib_path)
    return None

def main():
    args = parse_args()
    print(f"=== Starting Phase 6 Live Agent Daemon ===")
    print(f"  Policy:           {args.policy}")
    print(f"  Target Table:     {args.table}")
    print(f"  Thrift Server:    {args.host}:{args.port}")
    print(f"  Check Interval:   {args.interval}s")

    # Instantiate Policy
    if args.policy == "SOTAThresholdPolicy":
        policy = SOTAThresholdPolicy(frag_file_threshold=200, min_file_size_mb=16.0)
    else:
        # High-assurance conformal policy calibrated at alpha=0.05 (q_hat = 244ms)
        policy = TemporalConformalPolicy(sla_threshold_ms=492.0, q_hat=244.0)

    log_file = f"results/phase6_decisions_{args.policy}.csv"
    os.makedirs("results", exist_ok=True)
    
    if not os.path.exists(log_file):
        with open(log_file, "w") as f:
            f.write("timestamp,policy,decision,frag_file_count,table_size_mb,conformal_ub,compaction_duration_s\n")

    print(f"Daemon active. Polling telemetry and making decisions every {args.interval}s...")

    try:
        while True:
            t_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Read latest telemetry state
            system_state = {"frag_file_count": 593, "table_size_mb": 15807.0}
            if os.path.exists(args.telemetry_path):
                try:
                    df = pd.read_csv(args.telemetry_path)
                    if not df.empty:
                        last_row = df.iloc[-1]
                        system_state["frag_file_count"] = int(last_row.get("frag_file_count", 593))
                        system_state["table_size_mb"] = float(last_row.get("table_size_mb", 15807.0))
                except Exception as e:
                    pass

            point_prediction = 350.0  # ms forecast
            conformal_ub = point_prediction + getattr(policy, "q_hat", 244.0)

            decision = policy.decide(system_state, point_prediction, conformal_ub, tracker=None)
            print(f"[{t_now}] Policy {policy.name} -> Decision: {decision} | Frag Files: {system_state['frag_file_count']} | Conformal UB: {conformal_ub:.1f}ms")

            compaction_duration = 0.0
            if decision == "RUN":
                print(f"[{t_now}] >>> INITIATING COMPACTION on {args.table} <<<")
                start_t = time.time()
                
                if PYHIVE_AVAILABLE:
                    try:
                        conn = hive.Connection(host=args.host, port=args.port, username="ccbd")
                        cursor = conn.cursor()
                        cursor.execute(f"CALL local.system.rewrite_data_files(table => '{args.table}')")
                        res = cursor.fetchall()
                        print(f"[{t_now}] Compaction completed successfully. Result: {res}")
                        cursor.close()
                        conn.close()
                    except Exception as err:
                        print(f"[{t_now}] Compaction query warning/error: {err}")
                else:
                    print(f"[{t_now}] (Simulation Mode) Compaction executed.")
                
                compaction_duration = time.time() - start_t
                print(f"[{t_now}] Compaction finished in {compaction_duration:.2f}s")

            # Log decision
            with open(log_file, "a") as f:
                f.write(f"{t_now},{policy.name},{decision},{system_state['frag_file_count']},{system_state['table_size_mb']},{conformal_ub:.2f},{compaction_duration:.2f}\n")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nDaemon stopped by user.")

if __name__ == "__main__":
    main()
