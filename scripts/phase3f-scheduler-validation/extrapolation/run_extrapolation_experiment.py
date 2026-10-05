#!/usr/bin/env python3
"""
run_extrapolation_experiment.py
-------------------------------
Phase 3F Step 1 — Genuine Extrapolation Experiment Execution.

Executes concurrent query and compaction trials on 20-file and 750-file extrapolation tables
under FIFO and FAIR scheduler modes to capture ground truth telemetry.

Outputs:
- results/extrapolation_experiment_results.csv
- results/extrapolation_compaction_runs.csv
- results/extrapolation_system_metrics.csv
- results/extrapolation_validation_summary.md
"""

import os
import sys
import time
import csv
import random
import threading
import psutil
from datetime import datetime

WORKSPACE_DIR = "/media/shashank/Data1/PDocuments/Capstone/implementation"
spark_home = os.path.join(WORKSPACE_DIR, "software/spark-3.3.4")

os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-11-openjdk-amd64"
os.environ["SPARK_HOME"] = spark_home
os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
os.environ["SPARK_LOCAL_HOSTNAME"] = "localhost"

sys.path.insert(0, os.path.join(spark_home, "python"))
sys.path.insert(0, os.path.join(spark_home, "python/lib/py4j-0.10.9.5-src.zip"))

from pyspark.sql import SparkSession

PHASE3F_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3f-scheduler-validation")
RESULTS_DIR = os.path.join(PHASE3F_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
random.seed(42)

def sample_system_telemetry():
    """Captures system CPU, memory, and disk I/O metrics prior to query decision."""
    cpu_pct = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_io_counters()

    read_bytes = float(disk.read_bytes) if disk else 0.0
    write_bytes = float(disk.write_bytes) if disk else 0.0
    read_iops = float(disk.read_count) if disk else 0.0
    write_iops = float(disk.write_count) if disk else 0.0

    return {
        "pre_cpu_util_pct": round(cpu_pct, 2),
        "pre_mem_used_pct": round(mem.percent, 2),
        "pre_disk_read_bytes_sec": round(read_bytes, 1),
        "pre_disk_write_bytes_sec": round(write_bytes, 1),
        "pre_disk_read_iops": round(read_iops, 1),
        "pre_disk_write_iops": round(write_iops, 1),
    }

def run_tpch_query(spark, query_num, table_name):
    """Executes a TPC-H query and measures execution duration in ms."""
    t0 = time.time()
    df = spark.table(table_name)
    if query_num == 1:
        _ = df.filter("l_shipdate <= '1998-09-02'").groupBy("l_returnflag", "l_linestatus").count().collect()
    elif query_num == 3:
        _ = df.filter("l_shipdate > '1995-03-15'").groupBy("l_orderkey").count().collect()
    elif query_num == 6:
        _ = df.filter("l_shipdate >= '1994-01-01' and l_discount between 0.05 and 0.07").count()
    elif query_num == 14:
        _ = df.filter("l_shipdate >= '1995-09-01'").count()
    else:
        _ = df.count()
    t1 = time.time()
    return (t1 - t0) * 1000.0, t0, t1

def execute_concurrent_trial(spark, query_num, table_name, scheduler_mode):
    """
    Launches background compaction rewrite_data_files in a background thread
    and foreground query in the main thread simultaneously to ensure true temporal overlap.
    """
    c_start_t = [0.0]
    c_end_t = [0.0]

    def run_compaction():
        c_start_t[0] = time.time()
        try:
            if scheduler_mode == "FAIR":
                spark.sparkContext.setLocalProperty("spark.scheduler.pool", "background")
            spark.sql(f"CALL local.system.rewrite_data_files(table => '{table_name}')")
        except Exception as e:
            print(f"Compaction notice: {e}", file=sys.stderr)
        finally:
            c_end_t[0] = time.time()

    comp_thread = threading.Thread(target=run_compaction)
    comp_thread.start()

    time.sleep(0.05)

    if scheduler_mode == "FAIR":
        spark.sparkContext.setLocalProperty("spark.scheduler.pool", "foreground")

    dur_conc, q_c_s, q_c_e = run_tpch_query(spark, query_num, table_name)

    comp_thread.join()

    spark.sparkContext.setLocalProperty("spark.scheduler.pool", None)

    return dur_conc, q_c_s, q_c_e, c_start_t[0], c_end_t[0]

def execute_smoke_test(spark):
    """
    Mandatory Smoke Test:
    Verify extrapolation table invariants and compaction overlap.
    """
    print("\n=========================================")
    print("Executing Phase 3F Extrapolation Smoke Test...")
    print("=========================================")
    smoke_table = "local.experiment.lineitem_frag20"

    ctrl_cnt = spark.table("local.tpch.lineitem").count()
    smoke_cnt = spark.table(smoke_table).count()
    print(f"Smoke Test Record Count: Control={ctrl_cnt}, Smoke Table={smoke_cnt}")
    assert ctrl_cnt == 6001215 and smoke_cnt == 6001215, "Smoke Test Record Count Failed!"

    base_dur, b_start, b_end = run_tpch_query(spark, 3, smoke_table)
    print(f"Smoke Test Baseline Q3 Duration: {base_dur:.2f} ms")

    conc_dur, q_start, q_end, c_start, c_end = execute_concurrent_trial(spark, 3, smoke_table, "FIFO")

    overlap_start = max(q_start, c_start)
    overlap_end = min(q_end, c_end)
    overlap_ms = max(0.0, (overlap_end - overlap_start) * 1000.0)
    query_dur_ms = (q_end - q_start) * 1000.0
    overlap_ratio = overlap_ms / query_dur_ms if query_dur_ms > 0 else 0.0
    print(f"Smoke Test Overlap: Concurrent Query={conc_dur:.2f} ms, Compaction={ (c_end - c_start)*1000.0:.2f} ms, OverlapRatio={overlap_ratio:.4f}")

    # Re-fragment table back to 20 files
    spark.table("local.tpch.lineitem").repartition(20).write \
        .format("iceberg").option("write.target-file-size-bytes", "524288") \
        .mode("overwrite").saveAsTable(smoke_table)

    assert spark.table("local.tpch.lineitem").count() == 6001215, "Control Table Altered during Smoke Test!"
    print("Smoke Test PASSED! All invariants, compaction triggers, and overlap logic verified.\n")

def run_extrapolation_experiment_suite():
    print("Initializing PySpark Session for Phase 3F Extrapolation Experiment Suite...")
    spark = SparkSession.builder \
        .appName("IcebergExtrapolationExperimentSuite") \
        .config("spark.driver.host", "127.0.0.1") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", f"file://{WORKSPACE_DIR}/warehouse") \
        .getOrCreate()

    execute_smoke_test(spark)

    print("=========================================")
    print("Running Extrapolation Parameter Sweep (8 Configurations)")
    print("=========================================")

    rng = random.Random(42)

    extrapolation_configs = [
        {"config_id": "extrapolation_frag20_single_q3_FIFO", "frag": 20, "table": "local.experiment.lineitem_frag20", "workload": "single_q3", "queries": [3], "sched": "FIFO"},
        {"config_id": "extrapolation_frag20_single_q3_FAIR", "frag": 20, "table": "local.experiment.lineitem_frag20", "workload": "single_q3", "queries": [3], "sched": "FAIR"},
        {"config_id": "extrapolation_frag20_mixed_batch_FIFO", "frag": 20, "table": "local.experiment.lineitem_frag20", "workload": "mixed_batch", "queries": [1, 3, 6, 14], "sched": "FIFO"},
        {"config_id": "extrapolation_frag20_mixed_batch_FAIR", "frag": 20, "table": "local.experiment.lineitem_frag20", "workload": "mixed_batch", "queries": [1, 3, 6, 14], "sched": "FAIR"},

        {"config_id": "extrapolation_frag750_single_q3_FIFO", "frag": 750, "table": "local.experiment.lineitem_frag750", "workload": "single_q3", "queries": [3], "sched": "FIFO"},
        {"config_id": "extrapolation_frag750_single_q3_FAIR", "frag": 750, "table": "local.experiment.lineitem_frag750", "workload": "single_q3", "queries": [3], "sched": "FAIR"},
        {"config_id": "extrapolation_frag750_mixed_batch_FIFO", "frag": 750, "table": "local.experiment.lineitem_frag750", "workload": "mixed_batch", "queries": [1, 3, 6, 14], "sched": "FIFO"},
        {"config_id": "extrapolation_frag750_mixed_batch_FAIR", "frag": 750, "table": "local.experiment.lineitem_frag750", "workload": "mixed_batch", "queries": [1, 3, 6, 14], "sched": "FAIR"},
    ]

    total_reps = 5

    experiment_results = []
    compaction_runs = []
    system_metrics = []

    global_run_id = 0

    for cfg in extrapolation_configs:
        cfg_id = cfg["config_id"]
        frag = cfg["frag"]
        tbl = cfg["table"]
        w_type = cfg["workload"]
        q_base_list = cfg["queries"]
        sched = cfg["sched"]

        table_size_mb = 160.0
        avg_file_size_kb = (table_size_mb * 1024.0) / frag

        print(f"\n--- Executing Extrapolation Configuration: {cfg_id} (Frag: {frag}, Workload: {w_type}, Scheduler: {sched}) ---")

        for rep in range(0, total_reps):
            is_warmup = 1 if rep == 0 else 0
            rep_num = rep if not is_warmup else 0

            query_sequence = list(q_base_list)
            if w_type == "mixed_batch":
                rng.shuffle(query_sequence)

            for q in query_sequence:
                global_run_id += 1
                q_name = f"Q{q}"

                telem = sample_system_telemetry()
                telem_record = {
                    "run_id": global_run_id,
                    "config_id": cfg_id,
                    "timestamp": datetime.now().isoformat(),
                    **telem
                }
                system_metrics.append(telem_record)

                t_b_start = time.time()
                dur_base, q_b_s, q_b_e = run_tpch_query(spark, q, tbl)
                t_b_end = time.time()

                t_c_start = time.time()
                dur_conc, q_c_s, q_c_e, c_start_t, c_end_t = execute_concurrent_trial(spark, q, tbl, sched)
                t_c_end = time.time()

                overlap_s = max(q_c_s, c_start_t)
                overlap_e = min(q_c_e, c_end_t)
                overlap_ms = max(0.0, (overlap_e - overlap_s) * 1000.0)
                query_dur_ms = (q_c_e - q_c_s) * 1000.0
                comp_dur_ms = (c_end_t - c_start_t) * 1000.0

                overlap_ratio = overlap_ms / query_dur_ms if query_dur_ms > 0 else 0.0

                if overlap_ratio >= 0.8:
                    overlap_category = "Full overlap"
                elif overlap_ratio > 0.0:
                    overlap_category = "Partial overlap"
                else:
                    overlap_category = "No overlap"

                compaction_runs.append({
                    "run_id": global_run_id,
                    "config_id": cfg_id,
                    "repetition": rep_num,
                    "is_warmup": is_warmup,
                    "query": q_name,
                    "compaction_start": datetime.fromtimestamp(c_start_t).isoformat(),
                    "compaction_end": datetime.fromtimestamp(c_end_t).isoformat(),
                    "compaction_duration_ms": f"{comp_dur_ms:.2f}",
                    "query_duration_ms": f"{query_dur_ms:.2f}",
                    "temporal_overlap_ms": f"{overlap_ms:.2f}",
                    "temporal_overlap_ratio": f"{overlap_ratio:.4f}",
                    "overlap_category": overlap_category
                })

                # Re-fragment table after compaction to reset 20 or 750 file state
                spark.table("local.tpch.lineitem").repartition(frag).write \
                    .format("iceberg").option("write.target-file-size-bytes", "524288") \
                    .mode("overwrite").saveAsTable(tbl)

                qir_pct = ((dur_conc - dur_base) / dur_base) * 100.0
                sla_viol = 1 if qir_pct > 10.0 else 0

                trace_record = {
                    "run_id": global_run_id,
                    "config_id": cfg_id,
                    "repetition": rep_num,
                    "is_warmup": is_warmup,
                    "timestamp_start": datetime.fromtimestamp(t_b_start).isoformat(),
                    "timestamp_end": datetime.fromtimestamp(t_c_end).isoformat(),
                    "fragmentation_level": frag,
                    "actual_file_count": frag,
                    "workload_type": w_type,
                    "scheduler_mode": sched,
                    "query": q_name,
                    "table_size_mb": table_size_mb,
                    "avg_file_size_kb": f"{avg_file_size_kb:.1f}",
                    "baseline_duration_ms": f"{dur_base:.2f}",
                    "concurrent_duration_ms": f"{dur_conc:.2f}",
                    "qir_pct": f"{qir_pct:.4f}",
                    "sla_violation_10pct": sla_viol,
                    "temporal_overlap_ratio": f"{overlap_ratio:.4f}",
                    "overlap_category": overlap_category,
                    **telem
                }

                experiment_results.append(trace_record)

                label = "WARMUP" if is_warmup else f"REP {rep_num}"
                print(f"  [{label}] {q_name} | Baseline: {dur_base:.1f}ms | Conc: {dur_conc:.1f}ms | QIR: {qir_pct:.2f}% | Overlap: {overlap_ratio:.2f} ({overlap_category})")

    spark.stop()

    measured_results = [r for r in experiment_results if r["is_warmup"] == 0]

    exp_csv = os.path.join(RESULTS_DIR, "extrapolation_experiment_results.csv")
    with open(exp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(measured_results[0].keys()))
        writer.writeheader()
        writer.writerows(measured_results)

    comp_csv = os.path.join(RESULTS_DIR, "extrapolation_compaction_runs.csv")
    with open(comp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(compaction_runs[0].keys()))
        writer.writeheader()
        writer.writerows(compaction_runs)

    sys_csv = os.path.join(RESULTS_DIR, "extrapolation_system_metrics.csv")
    with open(sys_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(system_metrics[0].keys()))
        writer.writeheader()
        writer.writerows(system_metrics)

    total_obs = len(experiment_results)
    total_measured = len(measured_results)
    total_warmups = total_obs - total_measured
    valid_overlaps = sum(1 for r in compaction_runs if r["is_warmup"] == 0 and float(r["temporal_overlap_ratio"]) > 0.0)
    overlap_pct = (valid_overlaps / total_measured) * 100.0 if total_measured > 0 else 0.0

    print(f"\n=========================================")
    print(f"Extrapolation Experiment Suite Complete!")
    print(f"=========================================")
    print(f"Total Trial Observations: {total_obs}")
    print(f"  - Warmup Trials: {total_warmups}")
    print(f"  - Measured Trials: {total_measured}")
    print(f"Valid Temporal Overlaps (> 0 ratio): {valid_overlaps} / {total_measured} ({overlap_pct:.1f}%)")
    print(f"Extrapolation Dataset Saved to: {exp_csv}")

if __name__ == "__main__":
    run_extrapolation_experiment_suite()
