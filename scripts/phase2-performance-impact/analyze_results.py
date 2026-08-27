import os
import json
import csv
import sys
import duckdb
import statistics
from datetime import datetime

telemetry_db_path = "scripts/phase2-performance-impact/telemetry/telemetry_fragmented.db"
baseline_summary_path = "scripts/baseline-workload/results/baseline_summary.csv"
results_dir = "scripts/phase2-performance-impact/results"
analysis_dir = "scripts/phase2-performance-impact/analysis"

def main():
    print("Connecting to DuckDB telemetry database...")
    if not os.path.exists(telemetry_db_path):
        print(f"Error: Telemetry database not found at {telemetry_db_path}", file=sys.stderr)
        sys.exit(1)

    con = duckdb.connect(database=telemetry_db_path, read_only=True)
    
    # Query execution details
    # We want to identify the run_id, task_id (which identifies the query), and duration
    try:
        rows = con.execute("""
            SELECT run_id, event_id AS statement_id, event_status AS status, event_start_time AS start_time, event_end_time AS end_time
            FROM experiment_telemetry
            WHERE event_type = 'EXEC_STATEMENT'
            ORDER BY event_start_time ASC
        """).fetchall()
    except Exception as e:
        print(f"Error querying DuckDB: {e}", file=sys.stderr)
        con.close()
        sys.exit(1)
    
    con.close()

    if not rows:
        print("Error: No statement execution events found in telemetry database.", file=sys.stderr)
        sys.exit(1)

    # Map statement_id to TPC-H query labels
    # statement_id looks like: query1_fragmented.sql_0, query3_fragmented.sql_0, etc.
    query_mapping = {
        "query1_fragmented.sql": "Q1",
        "query3_fragmented.sql": "Q3",
        "query6_fragmented.sql": "Q6",
        "query12_fragmented.sql": "Q12",
        "query14_fragmented.sql": "Q14",
        "query18_fragmented.sql": "Q18"
    }

    results = []
    # Calculate duration and map query names
    for row in rows:
        run_id, stmt_id, status, start_time, end_time = row
        # Find which query it matches
        q_label = "Unknown"
        for key, val in query_mapping.items():
            if key in stmt_id:
                q_label = val
                break
        
        # Calculate duration in seconds
        start = datetime.strptime(start_time.split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime(end_time.split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        
        # We need precise duration. If start/end times in DB have fractional seconds, let's parse them
        try:
            # DuckDB timestamps might have microseconds
            t_start = datetime.fromisoformat(start_time.replace("Z", ""))
            t_end = datetime.fromisoformat(end_time.replace("Z", ""))
            duration_sec = (t_end - t_start).total_seconds()
        except Exception:
            duration_sec = (end - start).total_seconds()

        results.append({
            "run_id": run_id,
            "query": q_label,
            "statement_id": stmt_id,
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": duration_sec
        })

    # Ensure results folder exists
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(analysis_dir, exist_ok=True)

    # 1. Write detailed statement results
    stmt_csv_path = os.path.join(results_dir, "fragmented_statement_results.csv")
    with open(stmt_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["run_id", "query", "statement_id", "status", "start_time", "end_time", "duration_seconds"])
        for r in results:
            writer.writerow([r["run_id"], r["query"], r["statement_id"], r["status"], r["start_time"], r["end_time"], r["duration_seconds"]])
    print(f"Wrote statement results to {stmt_csv_path}")

    # 2. Compute Summary Statistics for Fragmented Workload
    queries = ["Q1", "Q3", "Q6", "Q12", "Q14", "Q18"]
    summary_stats = {}

    for q in queries:
        q_runs = [r for r in results if r["query"] == q]
        count = len(q_runs)
        successes = len([r for r in q_runs if r["status"] == "SUCCESS"])
        failures = len([r for r in q_runs if r["status"] != "SUCCESS"])
        durations = [r["duration_seconds"] for r in q_runs if r["status"] == "SUCCESS"]

        if len(durations) > 0:
            mean = statistics.mean(durations)
            median = statistics.median(durations)
            minimum = min(durations)
            maximum = max(durations)
            stddev = statistics.stdev(durations) if len(durations) > 1 else 0.0
        else:
            mean = median = minimum = maximum = stddev = 0.0

        summary_stats[q] = {
            "count": count,
            "successes": successes,
            "failures": failures,
            "mean": mean,
            "median": median,
            "min": minimum,
            "max": maximum,
            "stddev": stddev
        }

    summary_csv_path = os.path.join(results_dir, "fragmented_summary.csv")
    with open(summary_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["query", "count", "successes", "failures", "mean_seconds", "median_seconds", "min_seconds", "max_seconds", "stddev_seconds"])
        for q in queries:
            s = summary_stats[q]
            writer.writerow([q, s["count"], s["successes"], s["failures"], f"{s['mean']:.6f}", f"{s['median']:.6f}", f"{s['min']:.6f}", f"{s['max']:.6f}", f"{s['stddev']:.6f}"])
    print(f"Wrote summary results to {summary_csv_path}")

    # 3. Load Baseline summary and compute comparison
    if not os.path.exists(baseline_summary_path):
        print(f"Warning: Baseline summary not found at {baseline_summary_path}. Comparison skipped.", file=sys.stderr)
        return

    baseline_data = {}
    with open(baseline_summary_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            baseline_data[row["query"]] = float(row["mean_seconds"])

    comparison_results = []
    for q in queries:
        b_mean = baseline_data[q]
        f_mean = summary_stats[q]["mean"]
        
        diff = f_mean - b_mean
        slowdown = f_mean / b_mean
        pct_change = (diff / b_mean) * 100.0

        comparison_results.append({
            "query": q,
            "baseline_mean_seconds": b_mean,
            "fragmented_mean_seconds": f_mean,
            "absolute_difference_seconds": diff,
            "slowdown_factor": slowdown,
            "percentage_change": pct_change
        })

    comp_csv_path = os.path.join(results_dir, "performance_comparison.csv")
    with open(comp_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["query", "baseline_mean_seconds", "fragmented_mean_seconds", "absolute_difference_seconds", "slowdown_factor", "percentage_change"])
        for c in comparison_results:
            writer.writerow([
                c["query"],
                f"{c['baseline_mean_seconds']:.6f}",
                f"{c['fragmented_mean_seconds']:.6f}",
                f"{c['absolute_difference_seconds']:.6f}",
                f"{c['slowdown_factor']:.6f}",
                f"{c['percentage_change']:.6f}"
            ])
    print(f"Wrote performance comparison to {comp_csv_path}")

    # 4. Generate report
    report_path = os.path.join(analysis_dir, "fragmentation_impact_report.md")
    generate_markdown_report(report_path, comparison_results, results, summary_stats)
    print(f"Wrote markdown report to {report_path}")

def generate_markdown_report(report_path, comparison_results, results, summary_stats):
    # Format comparison table rows
    comp_rows = ""
    for c in comparison_results:
        pct_sign = "+" if c["percentage_change"] >= 0 else ""
        comp_rows += (
            f"| **{c['query']}** "
            f"| {c['baseline_mean_seconds']:.3f} s "
            f"| {c['fragmented_mean_seconds']:.3f} s "
            f"| {c['absolute_difference_seconds']:.3f} s "
            f"| {c['slowdown_factor']:.2f}x "
            f"| {pct_sign}{c['percentage_change']:.2f}% |\n"
        )

    # Raw statement results table rows
    stmt_rows = ""
    for r in results:
        stmt_rows += f"| `{r['run_id']}` | **{r['query']}** | `{r['statement_id']}` | {r['status']} | {r['duration_seconds']:.3f} s |\n"

    # Analyze performance changes
    total_baseline = sum(c["baseline_mean_seconds"] for c in comparison_results)
    total_frag = sum(c["fragmented_mean_seconds"] for c in comparison_results)
    overall_slowdown = total_frag / total_baseline
    overall_pct = ((total_frag - total_baseline) / total_baseline) * 100.0

    interpretation = ""
    if overall_slowdown > 1.05:
        interpretation = (
            f"The experimental data demonstrates a **clear performance degradation** caused by Iceberg file fragmentation. "
            f"The total mean execution time for the 6 queries increased from **{total_baseline:.3f} seconds** (baseline) "
            f"to **{total_frag:.3f} seconds** (fragmented), representing an overall slowdown of **{overall_slowdown:.2f}x** "
            f"({overall_pct:+.2f}% increase in runtime). This degradation is primarily driven by metadata scan overhead "
            f"and high task-scheduling latency associated with processing 200 small files instead of 16 consolidated files."
        )
    elif overall_slowdown < 0.95:
        interpretation = (
            f"Surprisingly, the experimental data shows a **performance improvement** after fragmentation. "
            f"The total mean execution time decreased from **{total_baseline:.3f} seconds** (baseline) "
            f"to **{total_frag:.3f} seconds** (fragmented), a speedup of **{1/overall_slowdown:.2f}x**. "
            "This could be due to increased query parallelism on the repartitioned dataset, or local caching effects."
        )
    else:
        interpretation = (
            f"The experimental data shows **negligible performance difference** between the control and fragmented states. "
            f"The overall runtime changed by only **{overall_pct:+.2f}%** (slowdown factor of **{overall_slowdown:.2f}x**). "
            "This indicates that at SF1, Spark's query execution overhead, catalog caching, or OS cache buffers "
            "largely absorb the physical layout differences."
        )

    report_content = f"""# Apache Iceberg Small-File Fragmentation Performance Impact Report

This report evaluates the performance difference between the healthy control table (`local.tpch.lineitem`) and the deliberately fragmented table (`local.experiment.lineitem_fragmented`).

**Control Table:** `local.tpch.lineitem` (16 consolidated data files, ~9.08 MB average)
**Fragmented Table:** `local.experiment.lineitem_fragmented` (200 fragmented data files, ~842 KB average)
**Analysis Time:** `{datetime.utcnow().isoformat()}Z`

---

## 1. Executive Summary
{interpretation}

---

## 2. Workload Performance Comparison
Below is the comparison of average runtimes (seconds) for each query:

| Query | Baseline Mean Time | Fragmented Mean Time | Absolute Difference | Slowdown Factor | Percentage Change |
| :--- | :--- | :--- | :--- | :---: | :--- |
{comp_rows}

---

## 3. Storage Layout Comparison
- **Control Table Data Files:** 16 files (Average size: 9.08 MB)
- **Fragmented Table Data Files:** 200 files (Average size: 842.34 KB)
- **Fragmentation Factor:** **12.50x** increase in file count.

---

## 4. Run Details
Below are the individual statement runtimes for all 3 repetitions:

| Run ID | Query | Statement ID | Status | Duration |
| :--- | :--- | :--- | :--- | :--- |
{stmt_rows}

---

## 5. Factors Influencing Measurements
When interpreting these results, several environmental factors should be considered:
1. **JVM Warm-up**: The initial executions (Repetition 1) typically incur JIT compilation and metadata class loading overhead.
2. **Spark Catalyst Planning**: Spark caches catalog metadata and logical query plans, which speeds up subsequent repetitions.
3. **OS Filesystem Cache**: The local OS caches recently read Parquet file footers and dictionary pages in memory, reducing physical disk I/O.
4. **Local Hardware Jitter**: CPU throttling and background processes on the local machine can lead to run-to-run variability.

This performance baseline provides the treatment reference (Phase 2C) to contrast against subsequent compaction and maintenance phases.
"""
    # Replace inline datetime with dynamic string
    report_content = report_content.replace("datetime.utcnow().isoformat()", datetime.utcnow().isoformat())

    with open(report_path, 'w') as f:
        f.write(report_content)

if __name__ == "__main__":
    main()
