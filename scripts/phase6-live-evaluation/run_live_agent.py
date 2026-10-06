#!/usr/bin/env python3
import os
import sys
import time
import argparse
import threading
import pandas as pd
import numpy as np
from datetime import datetime

# Add root and policies path
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('scripts/phase5-adaptive-scheduling-agent'))
sys.path.append(os.path.abspath('scripts/phase6-live-evaluation'))

from policies.sota_threshold_policy import SOTAThresholdPolicy
from policies.temporal_conformal_policy import TemporalConformalPolicy
from google_trace_mapper import GoogleTraceMapper

try:
    from pyhive import hive
    PYHIVE_AVAILABLE = True
except ImportError:
    PYHIVE_AVAILABLE = False

class ConsecutiveDeferralTracker:
    def __init__(self):
        self.consecutive_deferrals = 0

    def record_decision(self, decision: str):
        if decision in ["RUN", "FORCED_OVERRIDE"]:
            self.consecutive_deferrals = 0
        else:
            self.consecutive_deferrals += 1

    def should_force_run(self, max_deferrals: int = 3) -> bool:
        return self.consecutive_deferrals >= max_deferrals

class WorkloadDriver:
    """Background query runner driven by GoogleTraceMapper intensity."""
    def __init__(self, host="127.0.0.1", port=10000, table="local.tpch_sf100.lineitem", trace_mapper=None, sla_threshold_ms=492.0):
        self.host = host
        self.port = port
        self.table = table
        self.trace_mapper = trace_mapper
        self.sla_threshold_ms = sla_threshold_ms
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        
        self.total_queries = 0
        self.sla_violations = 0
        self.cumulative_latency_ms = 0.0
        self.recent_latencies = []

        self.queries = [
            f"SELECT count(*), sum(L_EXTENDEDPRICE * (1 - L_DISCOUNT)) FROM {self.table} WHERE L_SHIPDATE >= '1995-01-01' AND L_SHIPDATE <= '1995-03-31'",
            f"SELECT L_RETURNFLAG, L_LINESTATUS, count(*), sum(L_QUANTITY), avg(L_DISCOUNT) FROM {self.table} GROUP BY L_RETURNFLAG, L_LINESTATUS",
            f"SELECT count(*) FROM {self.table} WHERE L_DISCOUNT > 0.05 AND L_QUANTITY < 24",
            f"SELECT max(L_EXTENDEDPRICE), min(L_EXTENDEDPRICE) FROM {self.table} WHERE L_SHIPDATE >= '1996-01-01'"
        ]

    def start(self, start_time: float):
        self.start_time = start_time
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _run(self):
        query_idx = 0
        while not self.stop_event.is_set():
            elapsed = time.time() - self.start_time
            intensity = self.trace_mapper.get_intensity(elapsed) if self.trace_mapper else 0.5
            
            # Dynamic inter-query delay (high intensity = low delay = heavy workload)
            sleep_delay = max(0.5, (1.0 - intensity) * 8.0)
            time.sleep(sleep_delay)

            if not PYHIVE_AVAILABLE:
                # Simulation mode query delay
                sim_latency = 200.0 + intensity * 250.0 + np.random.normal(0, 15.0)
                sim_latency = max(50.0, sim_latency)
                self._record_query_result(sim_latency)
                continue

            sql = self.queries[query_idx % len(self.queries)]
            query_idx += 1
            
            t0 = time.time()
            try:
                conn = hive.Connection(host=self.host, port=self.port, username="ccbd")
                cursor = conn.cursor()
                cursor.execute(sql)
                cursor.fetchall()
                cursor.close()
                conn.close()
                latency_ms = (time.time() - t0) * 1000.0
                self._record_query_result(latency_ms)
            except Exception as e:
                # If compaction is running, query may take longer or retry
                latency_ms = (time.time() - t0) * 1000.0
                self._record_query_result(max(latency_ms, 600.0))

    def _record_query_result(self, latency_ms: float):
        with self.lock:
            self.total_queries += 1
            self.cumulative_latency_ms += latency_ms
            if latency_ms > self.sla_threshold_ms:
                self.sla_violations += 1
            self.recent_latencies.append(latency_ms)
            if len(self.recent_latencies) > 50:
                self.recent_latencies.pop(0)

    def get_stats(self):
        with self.lock:
            avg_lat = np.mean(self.recent_latencies) if self.recent_latencies else 0.0
            sla_rate = (self.sla_violations / self.total_queries * 100.0) if self.total_queries > 0 else 0.0
            return {
                "total_queries": self.total_queries,
                "cumulative_latency_s": self.cumulative_latency_ms / 1000.0,
                "avg_query_latency_ms": avg_lat,
                "sla_violations": self.sla_violations,
                "sla_violation_rate": sla_rate
            }

def parse_args():
    parser = argparse.ArgumentParser(description="Phase 6 Live Agent Compaction Daemon")
    parser.add_argument("--policy", type=str, required=True, choices=["SOTAThresholdPolicy", "TemporalConformalPolicy"], help="Compaction policy to run")
    parser.add_argument("--table", type=str, default="local.tpch_sf100.lineitem", help="Target Iceberg table")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Spark Thrift Server host")
    parser.add_argument("--port", type=int, default=10000, help="Spark Thrift Server port")
    parser.add_argument("--interval", type=int, default=60, help="Agent decision interval in seconds")
    parser.add_argument("--duration-hours", type=float, default=8.0, help="Total test duration in hours")
    parser.add_argument("--output", type=str, default=None, help="Output CSV path")
    return parser.parse_args()

def fetch_table_telemetry(host, port, table):
    """Queries Spark Thrift Server for Iceberg table file metrics."""
    default_state = {"frag_file_count": 593, "table_size_mb": 15807.0}
    if not PYHIVE_AVAILABLE:
        return default_state

    try:
        conn = hive.Connection(host=host, port=port, username="ccbd")
        cursor = conn.cursor()
        cursor.execute(f"SELECT count(file_path), sum(file_size_in_bytes) FROM {table}.files")
        row = cursor.fetchall()[0]
        cursor.close()
        conn.close()
        count = row[0] if row[0] is not None else 593
        size_bytes = row[1] if row[1] is not None else 15807 * 1024 * 1024
        return {
            "frag_file_count": int(count),
            "table_size_mb": float(size_bytes) / (1024.0 * 1024.0)
        }
    except Exception as e:
        return default_state

def main():
    args = parse_args()
    policy_name = args.policy
    
    if args.output:
        output_csv = args.output
    else:
        if policy_name == "SOTAThresholdPolicy":
            output_csv = "results/phase6_run_a_sota.csv"
        else:
            output_csv = "results/phase6_run_b_conformal.csv"

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    print(f"==========================================================")
    print(f"=== Starting Phase 6 Live Agent Evaluation Daemon ===")
    print(f"  Policy:           {policy_name}")
    print(f"  Target Table:     {args.table}")
    print(f"  Thrift Host/Port: {args.host}:{args.port}")
    print(f"  Decision Interval:{args.interval}s")
    print(f"  Duration:         {args.duration_hours} hours")
    print(f"  Output File:      {output_csv}")
    print(f"==========================================================")

    # Initialize policy
    if policy_name == "SOTAThresholdPolicy":
        policy = SOTAThresholdPolicy(frag_file_threshold=200, min_file_size_mb=16.0)
        q_hat = 0.0
    else:
        # High-assurance conformal policy calibrated at alpha=0.05 (q_hat = 244.0ms)
        policy = TemporalConformalPolicy(sla_threshold=492.0, max_consecutive_deferrals=3)
        policy.q_hat = 244.0

    trace_mapper = GoogleTraceMapper(test_duration_hours=args.duration_hours)
    tracker = ConsecutiveDeferralTracker()
    driver = WorkloadDriver(host=args.host, port=args.port, table=args.table, trace_mapper=trace_mapper, sla_threshold_ms=492.0)

    # Write CSV Header if not exists
    header = "timestamp,elapsed_s,policy,decision,frag_file_count,table_size_mb,conformal_ub,avg_query_latency_ms,sla_violation_rate,compaction_duration_s,regime,intensity,forced_override\n"
    with open(output_csv, "w") as f:
        f.write(header)

    start_time = time.time()
    max_test_seconds = args.duration_hours * 3600.0
    driver.start(start_time)

    try:
        while True:
            elapsed_s = time.time() - start_time
            if elapsed_s >= max_test_seconds:
                print(f"\nCompleted target duration of {args.duration_hours} hours ({elapsed_s:.1f}s elapsed). Stopping evaluation.")
                break

            t_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            regime = trace_mapper.get_regime(elapsed_s)
            intensity = trace_mapper.get_intensity(elapsed_s)

            # Get system telemetry & driver stats
            system_state = fetch_table_telemetry(args.host, args.port, args.table)
            stats = driver.get_stats()

            # Point prediction (estimated compaction penalty given intensity & file count)
            frag_files = system_state["frag_file_count"]
            point_pred = 180.0 + (intensity * 150.0) + (frag_files * 0.15)
            
            if policy_name == "SOTAThresholdPolicy":
                conformal_ub = point_pred
                raw_decision = policy.decide(system_state, point_pred, conformal_ub, tracker)
                forced_override = False
                decision = raw_decision
            else:
                conformal_ub = point_pred + getattr(policy, "q_hat", 244.0)
                forced_override = tracker.should_force_run(max_deferrals=3)
                if forced_override:
                    decision = "FORCED_OVERRIDE"
                else:
                    decision = policy.decide(system_state, point_pred, conformal_ub, tracker)

            print(f"[{t_now}] [{regime} {intensity:.2f}] {policy_name} -> {decision} | Files: {system_state['frag_file_count']} | Latency: {stats['avg_query_latency_ms']:.1f}ms | Conformal UB: {conformal_ub:.1f}ms", flush=True)

            compaction_duration = 0.0
            if decision in ["RUN", "FORCED_OVERRIDE"]:
                print(f"[{t_now}] >>> EXECUTING COMPACTION ON {args.table} (Reason: {decision}) <<<")
                c_start = time.time()
                if PYHIVE_AVAILABLE:
                    try:
                        conn = hive.Connection(host=args.host, port=args.port, username="ccbd")
                        cursor = conn.cursor()
                        cursor.execute(f"CALL local.system.rewrite_data_files(table => '{args.table}')")
                        res = cursor.fetchall()
                        cursor.close()
                        conn.close()
                        compaction_duration = time.time() - c_start
                        print(f"[{t_now}] Compaction completed in {compaction_duration:.2f}s | Result: {res}")
                    except Exception as err:
                        compaction_duration = time.time() - c_start
                        print(f"[{t_now}] Compaction query error/timeout ({compaction_duration:.2f}s): {err}")
                else:
                    time.sleep(2.5)
                    compaction_duration = time.time() - c_start
                    print(f"[{t_now}] (Simulation Mode) Compaction simulated in {compaction_duration:.2f}s")

            tracker.record_decision(decision)

            # Log step to CSV
            with open(output_csv, "a") as f:
                f.write(f"{t_now},{elapsed_s:.1f},{policy_name},{decision},{system_state['frag_file_count']},{system_state['table_size_mb']:.1f},{conformal_ub:.2f},{stats['avg_query_latency_ms']:.2f},{stats['sla_violation_rate']:.2f},{compaction_duration:.2f},{regime},{intensity:.3f},{forced_override}\n")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nEvaluation daemon interrupted by user.")
    finally:
        driver.stop()
        print(f"=== Live Agent Evaluation Finished ({output_csv}) ===")

if __name__ == "__main__":
    main()
