#!/usr/bin/env python3
"""
Phase 6C / 6.1D Live Agent Evaluation Daemon
Methodology v2.1

Features:
- Supports 4 evaluation policies:
  * CostBenefitPolicy (Conformalized dual-regime expected multi-query cost)
  * AutoCompPolicy (Gruenheid et al., VLDB 2024 / Microsoft & LinkedIn)
  * PeriodicCronPolicy (AWS EMR / Databricks Operational Standard)
  * TunedThresholdPolicy (Active auto-optimize threshold, frag_threshold=40)
- Principled action space: Defers immediately if candidate_small_files <= 0.
- Iceberg execution verification: Inspects rewritten_data_files_count to log true NO_OPs.
- Grounded SF100 SLA threshold: default --sla-ms 6750.0.
"""

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
from policies.literature_baselines import AutoCompPolicy, PeriodicCronPolicy, TunedThresholdPolicy
from collect_training_data import WorkloadDriver, WriteDriver, fetch_table_metadata

try:
    from pyhive import hive
    PYHIVE_AVAILABLE = True
except ImportError:
    PYHIVE_AVAILABLE = False


class CostBenefitPolicy:
    """Conformalized Cost-Benefit Decision Policy with multi-query expected cost."""

    def __init__(self, model_dir="scripts/phase6-live-evaluation/models", model_a=None, model_b=None, metadata=None):
        if model_a is not None and model_b is not None and metadata is not None:
            self.model_a = model_a
            self.model_b = model_b
            self.metadata = metadata
        else:
            print(f"Loading models from {model_dir}...")
            self.model_a = joblib.load(os.path.join(model_dir, "model_a_compaction.joblib"))
            self.model_b = joblib.load(os.path.join(model_dir, "model_b_baseline.joblib"))
            with open(os.path.join(model_dir, "model_metadata.json"), "r") as f:
                self.metadata = json.load(f)

        self.features = self.metadata["features"]
        self.q_a = float(self.metadata["model_a"]["q_hat"])
        self.q_b = float(self.metadata["model_b"]["q_hat"])

        print(f"Model A q_hat: {self.q_a:.1f}ms | Model B q_hat: {self.q_b:.1f}ms")
        if self.q_a <= 0.0 or self.q_b <= 0.0:
            print("\n[CRITICAL ERROR] The loaded models have a safety bound of 0.0ms. This means they were trained on corrupted/fake data.")
            print("Refusing to run the experiment with a broken brain. Fix the data and retrain.")
            sys.exit(1)

    def decide(self, telemetry: dict):
        """
        Evaluates whether to trigger table compaction or defer.
        Applies principled action space: if candidate_small_files <= 0, compaction is ineligible.
        Evaluates multi-query expected latency across all 4 query types (Q0..Q3).
        """
        candidate_small = telemetry.get('candidate_small_files', 0)
        if candidate_small <= 0:
            # Table has no candidate small files; maintenance is ineligible in the action space
            return "DEFER", 0.0, 0.0

        # Evaluate expected latency across all 4 query types
        costs_compact = []
        costs_defer = []
        for q in range(4):
            t_q = telemetry.copy()
            for i in range(4):
                t_q[f'q_{i}'] = 1.0 if i == q else 0.0

            df_q = pd.DataFrame([t_q])
            pa = self.model_a.predict(df_q[self.features])[0]
            costs_compact.append(pa)

            t_defer = t_q.copy()
            t_defer['frag_file_count'] = t_defer.get('frag_file_count', 0) + 2.0
            t_defer['candidate_small_files'] = t_defer.get('candidate_small_files', 0) + 2.0
            df_defer = pd.DataFrame([t_defer])
            pb = self.model_b.predict(df_defer[self.features])[0]
            costs_defer.append(pb)

        pred_a = float(np.mean(costs_compact))
        pred_b = float(np.mean(costs_defer))
        c_compact = pred_a + self.q_a
        c_defer = pred_b + self.q_b

        decision = "RUN" if c_compact < c_defer else "DEFER"
        return decision, c_compact, c_defer


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 6C / 6.1D Cost-Benefit & Literature Baseline Agent Daemon")
    parser.add_argument("--policy", type=str, required=True,
                        choices=["CostBenefitPolicy", "AutoCompPolicy", "PeriodicCronPolicy", "TunedThresholdPolicy"],
                        help="Policy to execute during live evaluation")
    parser.add_argument("--table", type=str, default="local.tpch_sf100.lineitem", help="Target Iceberg table")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Spark Thrift Server host")
    parser.add_argument("--port", type=int, default=10000, help="Spark Thrift Server port")
    parser.add_argument("--duration-hours", type=float, default=8.0, help="Total test duration in hours")
    parser.add_argument("--model-dir", type=str, default="scripts/phase6-live-evaluation/models",
                        help="Directory containing trained models")
    parser.add_argument("--sla-ms", type=float, default=6750.0, help="Grounded SLA threshold in ms")
    parser.add_argument("--cron-interval-min", type=float, default=60.0, help="Interval for PeriodicCronPolicy")
    parser.add_argument("--frag-threshold", type=int, default=40, help="Threshold for TunedThresholdPolicy")
    parser.add_argument("--output", type=str, required=True, help="Output CSV path")
    return parser.parse_args()


def main():
    args = parse_args()

    if not PYHIVE_AVAILABLE:
        print("ERROR: PyHive is not available. CANNOT run in simulation mode.")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print(f"=== Starting Phase 6C / 6.1D Live Agent Evaluation ===")
    print(f"  Policy:           {args.policy}")
    print(f"  Target Table:     {args.table}")
    print(f"  Duration:         {args.duration_hours} hours")
    print(f"  SLA Threshold:    {args.sla_ms} ms")
    print(f"  Model Directory:  {args.model_dir}")
    print(f"  Output File:      {args.output}")

    # Instantiate chosen policy
    if args.policy == "AutoCompPolicy":
        policy = AutoCompPolicy(small_file_ratio_threshold=0.20, min_candidate_files=30)
    elif args.policy == "PeriodicCronPolicy":
        policy = PeriodicCronPolicy(interval_minutes=args.cron_interval_min)
    elif args.policy == "TunedThresholdPolicy":
        policy = TunedThresholdPolicy(frag_threshold=args.frag_threshold)
    else:
        policy = CostBenefitPolicy(model_dir=args.model_dir)

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
            frag_count = table_metadata.get("frag_file_count", 0)
            candidate_small = table_metadata.get("candidate_small_files", 0)
            table_size = table_metadata.get("table_size_mb", 0.0)
            avg_file_kb = (table_size * 1024.0 / frag_count) if frag_count > 0 else 0.0

            telemetry = {
                "cpu_util_avg_1min": cpu_1min,
                "cpu_util_avg_5min": cpu_5min,
                "cpu_trend": cpu_trend,
                "mem_used_pct": mem_pct,
                "frag_file_count": frag_count,
                "candidate_small_files": candidate_small,
                "table_size_mb": table_size,
                "avg_file_size_kb": avg_file_kb,
                "intensity": intensity
            }

            # Decide based on policy type
            if args.policy == "CostBenefitPolicy":
                decision, c_compact, c_defer = policy.decide(telemetry)
            else:
                decision = policy.decide(table_metadata, elapsed_s=elapsed_s)
                c_compact, c_defer = 0.0, 0.0

            print(f"[{t_now}] [{regime} {intensity:.2f}] {args.policy} -> {decision} | "
                  f"Files: {frag_count} (Small: {candidate_small}) | "
                  f"C_compact: {c_compact:.1f} | C_defer: {c_defer:.1f}")

            compaction_duration = 0.0
            if decision == "RUN":
                print(f"[{t_now}] >>> EXECUTING COMPACTION ON {args.table} <<<")
                c_start = time.time()
                try:
                    conn = hive.Connection(host=args.host, port=args.port, username="ccbd")
                    cursor = conn.cursor()
                    cursor.execute(f"CALL local.system.rewrite_data_files(table => '{args.table}')")
                    rows = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    compaction_duration = time.time() - c_start

                    rewritten_files = rows[0][0] if rows and len(rows) > 0 and rows[0][0] is not None else 0
                    added_files = rows[0][1] if rows and len(rows) > 0 and rows[0][1] is not None else 0

                    if rewritten_files == 0:
                        print(f"[{t_now}] NOTICE: Iceberg rewrote 0 files (NO-OP). Logging as NO_OP.")
                        decision = "NO_OP"
                    else:
                        print(f"[{t_now}] Compaction completed: rewrote {rewritten_files} files -> {added_files} files in {compaction_duration:.2f}s")
                except Exception as err:
                    compaction_duration = time.time() - c_start
                    print(f"[{t_now}] Compaction error ({compaction_duration:.2f}s): {err}")

            # Get Driver Stats (SLA violations and P95 latency)
            with read_driver.lock:
                recent = list(read_driver.completed_queries)
                latencies = [x[1] if isinstance(x, (tuple, list)) else x for x in recent]
                p95_lat = float(np.percentile(latencies, 95)) if len(latencies) > 0 else 0.0
                violations = sum(1 for l in latencies if l > args.sla_ms)
                sla_rate = (violations / len(latencies) * 100.0) if len(latencies) > 0 else 0.0
                read_driver.completed_queries.clear()  # Reset for next window

            # Log step to CSV
            with open(args.output, "a") as f:
                f.write(f"{t_now},{elapsed_s:.1f},{args.policy},{decision},{frag_count},{table_size:.1f},"
                        f"{c_compact:.2f},{c_defer:.2f},{p95_lat:.2f},{sla_rate:.2f},"
                        f"{compaction_duration:.2f},{regime},{intensity:.3f}\n")

            time.sleep(60.0)  # Tick every 60 seconds for decision

    except KeyboardInterrupt:
        print("\nEvaluation daemon interrupted by user.")
    finally:
        read_driver.stop()
        write_driver.stop()
        print(f"=== Finished Phase 6C / 6.1D Evaluation ({args.output}) ===")


if __name__ == "__main__":
    main()
