#!/usr/bin/env python3
import os
import sys
import time
import argparse
import threading
import psutil
import pandas as pd
import numpy as np
from datetime import datetime
from collections import deque

sys.path.append(os.path.abspath('scripts/phase5-adaptive-scheduling-agent'))
sys.path.append(os.path.abspath('scripts/phase6-live-evaluation'))

from google_trace_mapper import GoogleTraceMapper

try:
    from pyhive import hive
    PYHIVE_AVAILABLE = True
except ImportError:
    PYHIVE_AVAILABLE = False

class WriteDriver:
    """Background thread that executes INSERTs to create fragmentation."""
    def __init__(self, host="127.0.0.1", port=10000, table="local.tpch_sf100.lineitem", trace_mapper=None):
        self.host = host
        self.port = port
        self.table = table
        self.trace_mapper = trace_mapper
        self.stop_event = threading.Event()
        
    def start(self, start_time: float):
        self.start_time = start_time
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def stop(self):
        self.stop_event.set()
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)
            
    def _run(self):
        while not self.stop_event.is_set():
            elapsed = time.time() - self.start_time
            intensity = self.trace_mapper.get_intensity(elapsed) if self.trace_mapper else 0.5
            
            # Dynamic inter-write delay (high intensity = more frequent writes)
            # e.g., 30s at peak intensity, 60s at low intensity
            sleep_delay = 30.0 + (1.0 - intensity) * 30.0
            time.sleep(sleep_delay)
            
            if self.stop_event.is_set():
                break

            if not PYHIVE_AVAILABLE:
                continue
                
            try:
                # Randomize orderkey to avoid caching and simulate random ingestion
                random_start = np.random.randint(1, 6000000)
                sql = f"INSERT INTO {self.table} SELECT * FROM {self.table} WHERE L_ORDERKEY BETWEEN {random_start} AND {random_start + 100} LIMIT 100"
                conn = hive.Connection(host=self.host, port=self.port, username="ccbd")
                cursor = conn.cursor()
                cursor.execute(sql)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"[WriteDriver] Error inserting data: {e}")

class WorkloadDriver:
    """Background query runner driven by GoogleTraceMapper intensity."""
    def __init__(self, host="127.0.0.1", port=10000, table="local.tpch_sf100.lineitem", trace_mapper=None):
        self.host = host
        self.port = port
        self.table = table
        self.trace_mapper = trace_mapper
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        
        self.completed_queries = deque()

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
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)

    def _run(self):
        query_idx = 0
        while not self.stop_event.is_set():
            elapsed = time.time() - self.start_time
            intensity = self.trace_mapper.get_intensity(elapsed) if self.trace_mapper else 0.5
            
            # Dynamic inter-query delay (high intensity = low delay = heavy workload)
            sleep_delay = max(0.5, (1.0 - intensity) * 8.0)
            time.sleep(sleep_delay)

            if self.stop_event.is_set():
                break

            if not PYHIVE_AVAILABLE:
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
                with self.lock:
                    self.completed_queries.append(latency_ms)
            except Exception as e:
                latency_ms = (time.time() - t0) * 1000.0
                print(f"[WorkloadDriver] Query error ({latency_ms:.1f}ms): {e}")

    def pop_latency(self):
        with self.lock:
            if self.completed_queries:
                return self.completed_queries.popleft()
            return np.nan

def fetch_table_metadata(host, port, table):
    """Queries Spark Thrift Server for Iceberg table file metrics."""
    if not PYHIVE_AVAILABLE:
        return {"frag_file_count": 0, "table_size_mb": 0.0}

    try:
        conn = hive.Connection(host=host, port=port, username="ccbd")
        cursor = conn.cursor()
        cursor.execute(f"SELECT count(file_path), sum(file_size_in_bytes) FROM {table}.files")
        row = cursor.fetchall()[0]
        cursor.close()
        conn.close()
        count = row[0] if row[0] is not None else 0
        size_bytes = row[1] if row[1] is not None else 0
        return {
            "frag_file_count": int(count),
            "table_size_mb": float(size_bytes) / (1024.0 * 1024.0)
        }
    except Exception as e:
        print(f"[Telemetry] Metadata error: {e}")
        return {"frag_file_count": 0, "table_size_mb": 0.0}

def parse_args():
    parser = argparse.ArgumentParser(description="Phase 6A Data Collection Daemon")
    parser.add_argument("--table", type=str, default="local.tpch_sf100.lineitem", help="Target Iceberg table")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Spark Thrift Server host")
    parser.add_argument("--port", type=int, default=10000, help="Spark Thrift Server port")
    parser.add_argument("--duration-hours", type=float, default=4.0, help="Total test duration in hours")
    parser.add_argument("--output", type=str, default="results/phase6a_training_data.csv", help="Output CSV path")
    return parser.parse_args()

def main():
    args = parse_args()
    
    if not PYHIVE_AVAILABLE:
        print("ERROR: PyHive is not available. Phase 6 data collection CANNOT run in simulation mode.")
        sys.exit(1)

    # Validate Thrift connection
    try:
        conn = hive.Connection(host=args.host, port=args.port, username="ccbd")
        conn.close()
    except Exception as e:
        print(f"ERROR: Cannot connect to Spark Thrift Server at {args.host}:{args.port}. {e}")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print(f"=== Starting Phase 6A Data Collection ===")
    print(f"  Target Table:     {args.table}")
    print(f"  Duration:         {args.duration_hours} hours")
    print(f"  Output File:      {args.output}")

    trace_mapper = GoogleTraceMapper(test_duration_hours=args.duration_hours)
    read_driver = WorkloadDriver(host=args.host, port=args.port, table=args.table, trace_mapper=trace_mapper)
    write_driver = WriteDriver(host=args.host, port=args.port, table=args.table, trace_mapper=trace_mapper)

    # Write CSV Header
    header = ("timestamp,elapsed_s,cpu_util_pct,cpu_util_avg_1min,cpu_util_avg_5min,cpu_trend,"
              "mem_used_pct,disk_io_read_bytes,disk_io_write_bytes,frag_file_count,table_size_mb,"
              "avg_file_size_kb,intensity,compaction_active,query_latency_ms,query_latency_during_compaction_ms\n")
    with open(args.output, "w") as f:
        f.write(header)

    start_time = time.time()
    max_test_seconds = args.duration_hours * 3600.0
    
    read_driver.start(start_time)
    write_driver.start(start_time)

    cpu_history = deque(maxlen=300) # 5 minutes at 1Hz
    disk_io_initial = psutil.disk_io_counters()

    compaction_active = False
    compaction_thread = None
    last_compaction_time = 0

    def run_compaction():
        nonlocal compaction_active
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> EXECUTING DETERMINISTIC COMPACTION <<<")
            c_conn = hive.Connection(host=args.host, port=args.port, username="ccbd")
            c_cursor = c_conn.cursor()
            c_cursor.execute(f"CALL local.system.rewrite_data_files(table => '{args.table}')")
            c_cursor.fetchall()
            c_cursor.close()
            c_conn.close()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] <<< COMPACTION FINISHED <<<")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Compaction Error: {e}")
        finally:
            compaction_active = False

    try:
        while True:
            t_start_loop = time.time()
            elapsed_s = t_start_loop - start_time
            if elapsed_s >= max_test_seconds:
                print(f"\nCompleted target duration of {args.duration_hours} hours. Stopping.")
                break

            t_now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            intensity = trace_mapper.get_intensity(elapsed_s)

            # --- Telemetry Collection ---
            cpu_pct = psutil.cpu_percent(interval=None)
            cpu_history.append(cpu_pct)
            
            cpu_1min = np.mean(list(cpu_history)[-60:]) if len(cpu_history) > 0 else cpu_pct
            cpu_5min = np.mean(cpu_history) if len(cpu_history) > 0 else cpu_pct
            cpu_trend = cpu_1min - cpu_5min
            
            mem_pct = psutil.virtual_memory().percent
            
            disk_io = psutil.disk_io_counters()
            disk_read = disk_io.read_bytes - disk_io_initial.read_bytes
            disk_write = disk_io.write_bytes - disk_io_initial.write_bytes

            # Fetch table metadata (expensive, but necessary. At 1Hz it might take 100-200ms)
            table_metadata = fetch_table_metadata(args.host, args.port, args.table)
            frag_count = table_metadata["frag_file_count"]
            table_size = table_metadata["table_size_mb"]
            avg_file_kb = (table_size * 1024.0 / frag_count) if frag_count > 0 else 0.0

            # Get completed query latency (if any)
            lat_ms = read_driver.pop_latency()
            
            lat_compaction = lat_ms if compaction_active else np.nan
            lat_normal = np.nan if compaction_active else lat_ms

            # --- Trigger Compaction (Every 20 mins) ---
            # 20 mins = 1200 seconds
            if elapsed_s - last_compaction_time >= 1200.0 and elapsed_s > 60.0:
                if not compaction_active:
                    compaction_active = True
                    last_compaction_time = elapsed_s
                    compaction_thread = threading.Thread(target=run_compaction, daemon=True)
                    compaction_thread.start()

            # --- Logging ---
            with open(args.output, "a") as f:
                f.write(f"{t_now_str},{elapsed_s:.1f},{cpu_pct:.1f},{cpu_1min:.1f},{cpu_5min:.1f},{cpu_trend:.1f},"
                        f"{mem_pct:.1f},{disk_read},{disk_write},{frag_count},{table_size:.1f},"
                        f"{avg_file_kb:.1f},{intensity:.3f},{compaction_active},"
                        f"{lat_normal:.1f},{lat_compaction:.1f}\n")

            # Sleep to maintain ~1Hz tick rate
            loop_duration = time.time() - t_start_loop
            sleep_time = max(0.0, 1.0 - loop_duration)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nData collection interrupted by user.")
    finally:
        read_driver.stop()
        write_driver.stop()
        print(f"=== Finished Phase 6A Data Collection ({args.output}) ===")

if __name__ == "__main__":
    main()
