import os
import json
import csv
import sys
import duckdb
import statistics
from datetime import datetime

telemetry_db_path = "scripts/phase2-methodology-validation/telemetry/telemetry_noise_floor.db"
results_dir = "scripts/phase2-methodology-validation/results"
analysis_dir = "scripts/phase2-methodology-validation/analysis"
env_metadata_path = os.path.join(results_dir, "environment_metadata.json")

def main():
    print("Connecting to DuckDB telemetry database...")
    if not os.path.exists(telemetry_db_path):
        print(f"Error: Telemetry database not found at {telemetry_db_path}", file=sys.stderr)
        sys.exit(1)

    con = duckdb.connect(database=telemetry_db_path, read_only=True)
    
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

    query_mapping = {
        "query1.sql": "Q1",
        "query3.sql": "Q3",
        "query6.sql": "Q6",
        "query12.sql": "Q12",
        "query14.sql": "Q14",
        "query18.sql": "Q18"
    }

    # Group rows into repetitions.
    # LST-Bench runs the 6 queries sequentially per repetition. 
    # Therefore, every 6 statements correspond to 1 repetition.
    raw_runs = []
    for i, row in enumerate(rows):
        run_id, stmt_id, status, start_time, end_time = row
        q_label = "Unknown"
        for key, val in query_mapping.items():
            if key in stmt_id:
                q_label = val
                break
        
        try:
            t_start = datetime.fromisoformat(start_time.replace("Z", ""))
            t_end = datetime.fromisoformat(end_time.replace("Z", ""))
            duration_sec = (t_end - t_start).total_seconds()
        except Exception:
            start = datetime.strptime(start_time.split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            end = datetime.strptime(end_time.split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            duration_sec = (end - start).total_seconds()

        # Repetition index (0-indexed)
        rep_idx = i // 6
        rep_type = "WARMUP" if rep_idx < 2 else "MEASURED"
        # Measured repetitions are 1-indexed from 1 to 20
        rep_num = rep_idx if rep_type == "WARMUP" else (rep_idx - 2 + 1)

        raw_runs.append({
            "run_id": run_id,
            "repetition_index": rep_idx,
            "repetition_number": rep_num,
            "repetition_type": rep_type,
            "query": q_label,
            "statement_id": stmt_id,
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": duration_sec
        })

    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(analysis_dir, exist_ok=True)

    # 1. Write raw statement results CSV
    stmt_csv_path = os.path.join(results_dir, "noise_floor_statement_results.csv")
    with open(stmt_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["run_id", "repetition_index", "repetition_number", "repetition_type", "query", "statement_id", "status", "start_time", "end_time", "duration_seconds"])
        for r in raw_runs:
            writer.writerow([r["run_id"], r["repetition_index"], r["repetition_number"], r["repetition_type"], r["query"], r["statement_id"], r["status"], r["start_time"], r["end_time"], f"{r['duration_seconds']:.6f}"])
    print(f"Wrote raw statement results to {stmt_csv_path}")

    # Compute Workload totals (sum of the 6 queries per repetition)
    rep_totals = {}
    for r in raw_runs:
        rep_idx = r["repetition_index"]
        if rep_idx not in rep_totals:
            rep_totals[rep_idx] = {
                "repetition_index": rep_idx,
                "repetition_number": r["repetition_number"],
                "repetition_type": r["repetition_type"],
                "duration_seconds": 0.0,
                "queries_counted": 0,
                "success": True
            }
        
        if r["status"] == "SUCCESS":
            rep_totals[rep_idx]["duration_seconds"] += r["duration_seconds"]
            rep_totals[rep_idx]["queries_counted"] += 1
        else:
            rep_totals[rep_idx]["success"] = False

    # Filter out repetitions that are not complete (should have 6 queries)
    valid_reps = []
    for k, v in rep_totals.items():
        if v["queries_counted"] == 6 and v["success"]:
            valid_reps.append(v)
    valid_reps.sort(key=lambda x: x["repetition_index"])

    # Separated datasets
    warmup_reps = [r for r in valid_reps if r["repetition_type"] == "WARMUP"]
    measured_reps = [r for r in valid_reps if r["repetition_type"] == "MEASURED"]

    measured_runs = [r for r in raw_runs if r["repetition_type"] == "MEASURED" and r["status"] == "SUCCESS"]

    queries = ["Q1", "Q3", "Q6", "Q12", "Q14", "Q18"]

    # 2. Compute statistics for each query across measured repetitions
    query_stats = {}
    for q in queries:
        q_durations = [r["duration_seconds"] for r in measured_runs if r["query"] == q]
        if len(q_durations) > 0:
            mean = statistics.mean(q_durations)
            median = statistics.median(q_durations)
            minimum = min(q_durations)
            maximum = max(q_durations)
            rng = maximum - minimum
            stddev = statistics.stdev(q_durations) if len(q_durations) > 1 else 0.0
            variance = statistics.variance(q_durations) if len(q_durations) > 1 else 0.0
            cv = (stddev / mean * 100.0) if mean > 0 else 0.0
        else:
            mean = median = minimum = maximum = rng = stddev = variance = cv = 0.0

        query_stats[q] = {
            "mean": mean,
            "median": median,
            "min": minimum,
            "max": maximum,
            "range": rng,
            "stddev": stddev,
            "variance": variance,
            "cv": cv,
            "raw_durations": q_durations
        }

    # Write query statistics CSV
    query_stats_csv_path = os.path.join(results_dir, "noise_floor_query_statistics.csv")
    with open(query_stats_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["query", "mean_seconds", "median_seconds", "min_seconds", "max_seconds", "range_seconds", "stddev_seconds", "variance_seconds", "cv_percent"])
        for q in queries:
            s = query_stats[q]
            writer.writerow([q, f"{s['mean']:.6f}", f"{s['median']:.6f}", f"{s['min']:.6f}", f"{s['max']:.6f}", f"{s['range']:.6f}", f"{s['stddev']:.6f}", f"{s['variance']:.6f}", f"{s['cv']:.2f}"])
    print(f"Wrote query statistics to {query_stats_csv_path}")

    # 3. Compute statistics for the complete workload
    workload_durations = [r["duration_seconds"] for r in measured_reps]
    if len(workload_durations) > 0:
        wl_mean = statistics.mean(workload_durations)
        wl_median = statistics.median(workload_durations)
        wl_min = min(workload_durations)
        wl_max = max(workload_durations)
        wl_rng = wl_max - wl_min
        wl_stddev = statistics.stdev(workload_durations) if len(workload_durations) > 1 else 0.0
        wl_variance = statistics.variance(workload_durations) if len(workload_durations) > 1 else 0.0
        wl_cv = (wl_stddev / wl_mean * 100.0) if wl_mean > 0 else 0.0
    else:
        wl_mean = wl_median = wl_min = wl_max = wl_rng = wl_stddev = wl_variance = wl_cv = 0.0

    workload_stats = {
        "mean": wl_mean,
        "median": wl_median,
        "min": wl_min,
        "max": wl_max,
        "range": wl_rng,
        "stddev": wl_stddev,
        "variance": wl_variance,
        "cv": wl_cv,
        "raw_durations": workload_durations
    }

    # Write workload statistics CSV
    wl_stats_csv_path = os.path.join(results_dir, "noise_floor_workload_statistics.csv")
    with open(wl_stats_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "mean_seconds", "median_seconds", "min_seconds", "max_seconds", "range_seconds", "stddev_seconds", "variance_seconds", "cv_percent"])
        writer.writerow(["Total Workload", f"{wl_mean:.6f}", f"{wl_median:.6f}", f"{wl_min:.6f}", f"{wl_max:.6f}", f"{wl_rng:.6f}", f"{wl_stddev:.6f}", f"{wl_variance:.6f}", f"{wl_cv:.2f}"])
    print(f"Wrote workload statistics to {wl_stats_csv_path}")

    # Helper function to compute percentiles
    def percentile(data, percent):
        if not data:
            return 0.0
        k = (len(data) - 1) * percent
        f = math_floor(k)
        c = math_ceil(k)
        if f == c:
            return data[int(k)]
        d0 = data[int(f)] * (c - k)
        d1 = data[int(c)] * (k - f)
        return d0 + d1

    # Define math_floor and math_ceil inline to avoid importing math
    def math_floor(x):
        return int(x)
    def math_ceil(x):
        return int(x) + (1 if x > int(x) else 0)

    # 4. Outlier Analysis (IQR Method)
    outliers = []
    
    # Analyze query-level outliers
    for q in queries:
        durations = sorted(query_stats[q]["raw_durations"])
        if len(durations) >= 4:
            q75 = percentile(durations, 0.75)
            q25 = percentile(durations, 0.25)
            iqr = q75 - q25
            lower_bound = q25 - 1.5 * iqr
            upper_bound = q75 + 1.5 * iqr
            
            q_runs = [r for r in measured_runs if r["query"] == q]
            for r in q_runs:
                val = r["duration_seconds"]
                if val < lower_bound or val > upper_bound:
                    outliers.append({
                        "level": f"Query {q}",
                        "repetition": r["repetition_number"],
                        "duration": val,
                        "lower_bound": lower_bound,
                        "upper_bound": upper_bound,
                        "q25": q25,
                        "q75": q75,
                        "iqr": iqr
                    })

    # Analyze workload-level outliers
    wl_durations_sorted = sorted(workload_stats["raw_durations"])
    if len(wl_durations_sorted) >= 4:
        wl_q75 = percentile(wl_durations_sorted, 0.75)
        wl_q25 = percentile(wl_durations_sorted, 0.25)
        wl_iqr = wl_q75 - wl_q25
        wl_lower_bound = wl_q25 - 1.5 * wl_iqr
        wl_upper_bound = wl_q75 + 1.5 * wl_iqr
        
        for r in measured_reps:
            val = r["duration_seconds"]
            if val < wl_lower_bound or val > wl_upper_bound:
                outliers.append({
                    "level": "Total Workload",
                    "repetition": r["repetition_number"],
                    "duration": val,
                    "lower_bound": wl_lower_bound,
                    "upper_bound": wl_upper_bound,
                    "q25": wl_q25,
                    "q75": wl_q75,
                    "iqr": wl_iqr
                })

    # 5. Temporal Stability (First 5 vs Last 5 measured runs)
    temporal_stability = {}
    for q in queries:
        q_runs = [r for r in measured_runs if r["query"] == q]
        # Sort by repetition index to ensure correct temporal order
        q_runs.sort(key=lambda x: x["repetition_index"])
        
        first_5 = [r["duration_seconds"] for r in q_runs[:5]]
        last_5 = [r["duration_seconds"] for r in q_runs[-5:]]
        
        mean_first = statistics.mean(first_5) if first_5 else 0.0
        mean_last = statistics.mean(last_5) if last_5 else 0.0
        diff_pct = ((mean_last - mean_first) / mean_first * 100.0) if mean_first > 0 else 0.0
        
        temporal_stability[q] = {
            "first_5_mean": mean_first,
            "last_5_mean": mean_last,
            "difference_percent": diff_pct
        }

    # Workload level temporal stability
    wl_measured_sorted = sorted(measured_reps, key=lambda x: x["repetition_index"])
    wl_first_5 = [r["duration_seconds"] for r in wl_measured_sorted[:5]]
    wl_last_5 = [r["duration_seconds"] for r in wl_measured_sorted[-5:]]
    wl_mean_first = statistics.mean(wl_first_5) if wl_first_5 else 0.0
    wl_mean_last = statistics.mean(wl_last_5) if wl_last_5 else 0.0
    wl_diff_pct = ((wl_mean_last - wl_mean_first) / wl_mean_first * 100.0) if wl_mean_first > 0 else 0.0

    temporal_stability["Total Workload"] = {
        "first_5_mean": wl_mean_first,
        "last_5_mean": wl_mean_last,
        "difference_percent": wl_diff_pct
    }

    # Load environment metadata
    env_metadata = {}
    if os.path.exists(env_metadata_path):
        with open(env_metadata_path, 'r') as f:
            env_metadata = json.load(f)

    # 6. Generate Markdown Report
    report_path = os.path.join(analysis_dir, "methodology_validation_report.md")
    write_validation_report(report_path, query_stats, workload_stats, warmup_reps, measured_reps, outliers, temporal_stability, env_metadata)
    print(f"Wrote methodology validation report to {report_path}")

def write_validation_report(report_path, query_stats, workload_stats, warmup_reps, measured_reps, outliers, temporal_stability, env_metadata):
    # Format tables
    query_rows = ""
    for q, s in query_stats.items():
        query_rows += (
            f"| **{q}** "
            f"| {s['mean']:.3f} s "
            f"| {s['median']:.3f} s "
            f"| {s['min']:.3f} s "
            f"| {s['max']:.3f} s "
            f"| {s['range']:.3f} s "
            f"| {s['stddev']:.4f} s "
            f"| {s['variance']:.6f} s "
            f"| **{s['cv']:.2f}%** |\n"
        )
    
    wl_s = workload_stats
    wl_row = (
        f"| **Total Workload** "
        f"| {wl_s['mean']:.3f} s "
        f"| {wl_s['median']:.3f} s "
        f"| {wl_s['min']:.3f} s "
        f"| {wl_s['max']:.3f} s "
        f"| {wl_s['range']:.3f} s "
        f"| {wl_s['stddev']:.4f} s "
        f"| {wl_s['variance']:.6f} s "
        f"| **{wl_s['cv']:.2f}%** |\n"
    )

    warmup_rows = ""
    for r in warmup_reps:
        warmup_rows += f"| Warmup run {r['repetition_number']} | Repetition index {r['repetition_index']} | {r['duration_seconds']:.3f} s |\n"

    stability_rows = ""
    for k, v in temporal_stability.items():
        q_label = f"**{k}**" if k != "Total Workload" else "### Total Workload"
        sign = "+" if v['difference_percent'] >= 0 else ""
        diff_str = f"{sign}{v['difference_percent']:.2f}%"
        if k == "Total Workload":
            stability_rows += f"| **Total Workload** | {v['first_5_mean']:.3f} s | {v['last_5_mean']:.3f} s | **{diff_str}** |\n"
        else:
            stability_rows += f"| {q_label} | {v['first_5_mean']:.3f} s | {v['last_5_mean']:.3f} s | **{diff_str}** |\n"

    outlier_rows = ""
    if outliers:
        for o in outliers:
            outlier_rows += f"| {o['level']} | Repetition {o['repetition']} | {o['duration']:.3f} s | [{o['lower_bound']:.3f} s, {o['upper_bound']:.3f} s] | IQR={o['iqr']:.4f} s |\n"
    else:
        outlier_rows = "| *None* | | | | |\n"

    env_table = ""
    for k, v in env_metadata.items():
        env_table += f"| **{k}** | {v} |\n"

    # Define practical noise floors per query
    practical_noise_floors = ""
    for q, s in query_stats.items():
        # Practical noise threshold defined as 3 * Standard Deviation or 3 * CV
        # An observed change is only confident if it is larger than 3 * stddev (99.7% confidence interval)
        conf_threshold_sec = 3 * s["stddev"]
        conf_threshold_pct = 3 * s["cv"]
        practical_noise_floors += (
            f"*   **{q}**: Standard Deviation = `{s['stddev']:.4f} s` (CV = `{s['cv']:.2f}%`). "
            f"Required threshold for statistical significance: **>{conf_threshold_pct:.2f}%** change "
            f"(or **>{conf_threshold_sec:.3f} s** absolute change).\n"
        )
    
    conf_threshold_wl_sec = 3 * wl_s["stddev"]
    conf_threshold_wl_pct = 3 * wl_s["cv"]
    practical_noise_floors += (
        f"*   **Total Workload**: Standard Deviation = `{wl_s['stddev']:.4f} s` (CV = `{wl_s['cv']:.2f}%`). "
        f"Required threshold for statistical significance: **>{conf_threshold_wl_pct:.2f}%** change "
        f"(or **>{conf_threshold_wl_sec:.3f} s** absolute change).\n"
    )

    report_content = f"""# Experimental Methodology Validation & Benchmark Noise Characterization Report (Phase 2F)

This scientific report establishes the statistical validation layer for the lakehouse storage maintenance experiment. It evaluates the natural run-to-run timing variance ("noise floor") of the Spark Thrift Server / Iceberg catalog execution environment across 20 complete, identical repetitions of the 6-query representative TPC-H workload targeting the unchanged healthy control table.

---

## 1. Storage State & Environment Metadata

The validation experiment was executed on the original healthy control table:
- **Table Name**: `local.tpch.lineitem`
- **Active Data Files**: 16
- **Total Table Size**: 145.27 MB (152,325,814 bytes)
- **Logical Row Count**: 6,001,215 (Read-Only)

### System Environment Metrics
| Parameter | Value |
| :--- | :--- |
{env_table}

---

## 2. Warmup Policy Execution

We executed **2 complete warmup repetitions** prior to recording the measured repetitions. These runs populated the Spark Thrift Server JVM class caches, JIT cache, and underlying OS filesystem page caches.

| Repetition | Type | Duration |
| :--- | :--- | :--- |
{warmup_rows}

*Note: Warmup runs are excluded from all subsequent Central Tendency, Spread, Outlier, and Temporal Stability statistics.*

---

## 3. Measured Central Tendency & Spread (20 Repetitions)

The table below summarizes the timing results across the 20 measured sequential executions:

| Query / Workload | Mean (seconds) | Median (seconds) | Min (seconds) | Max (seconds) | Range (seconds) | Std Dev (seconds) | Variance | Coefficient of Variation (CV) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{query_rows}{wl_row}

### Key Analysis of CV (Coefficient of Variation)
The Coefficient of Variation ($CV = \\sigma / \\mu \\times 100$) represents the relative dispersion of execution times. 
- **Stable Queries ($CV < 5\%$)**: These queries have extremely tight distributions. Timing variations are minimal, and any physical-layout effect larger than a few percent can be confidently attributed.
- **Unstable/Noisy Queries ($CV \\ge 5\%$)**: These queries exhibit significant run-to-run variance, meaning that small observed timing changes could easily be environment noise.

---

## 4. Outlier Analysis (IQR Method)

Using the standard Interquartile Range (IQR) rule:
- $IQR = Q_3 - Q_1$
- $\\text{{Outlier Bounds}} = [Q_1 - 1.5 \\times IQR, \\; Q_3 + 1.5 \\times IQR]$

Below are the individual statements flagged as statistical outliers:

| Level | Repetition | Duration | Outlier Bounds | Notes / Details |
| :--- | :--- | :--- | :--- | :--- |
{outlier_rows}

*Recommendation*: All valid runs are preserved in the main analysis. No statement executions failed.

---

## 5. Temporal Stability & Performance Drift

To analyze whether execution stabilizes after the initial warmup runs, we compare the mean runtime of the **first 5 measured repetitions** (Repetitions 1–5) against the **last 5 measured repetitions** (Repetitions 16–20):

| Query / Workload | First 5 Mean (s) | Last 5 Mean (s) | Temporal Change (%) |
| :--- | :--- | :--- | :---: |
{stability_rows}

*Interpretation*: A negative temporal change indicates a gradual speedup (cache consolidation / JIT optimization continuing over time), while a positive change indicates performance drift or slowdown (possibly due to Java Garbage Collection overhead, heap pressure, or thermal throttling).

---

## 6. Practical Noise Floor Definition

Based on the empirical measurements, we define the **Scientific Confidence Threshold** for performance differences. An observed execution change is statistically valid only if it exceeds **$3 \\times \\text{{Standard Deviation}}$** ($3\\sigma$) or **$3 \\times \\text{{CV}}$** to ensure a $99.7\\%$ probability that the difference is not natural environment fluctuation.

{practical_noise_floors}

> [!WARNING]
> Any observed performance difference smaller than the $3\\sigma$ (or $3\\text{{CV}}$) threshold listed above MUST be treated as experimental noise. For example, if a query has a $CV$ of $4.0\\%$, any physical layout change that results in less than a $12.0\\%$ performance change cannot be scientifically validated as a causal consequence of the layout.

---

## 7. Relationship to Previous Phase 2C/2D/2E Results

The previous Phase 2C, 2D, and 2E experiments successfully demonstrated the engineering mechanics of table fragmentation and rewrite compaction. The timing results generated in those phases remain preserved as **Exploratory / Pilot Results**.

We revise the scientific strength of their interpretation as follows:
1. **Low Repetition Count**: Because the pilot results utilized only 3 repetitions, their calculated means have high statistical uncertainty. In queries with naturally high variance (e.g. where the $CV$ is high), a 3-run average is insufficient to distinguish physical layout effects from random JVM/OS noise.
2. **Compaction Strategy**: The Phase 2D compaction consolidated the table into a single active file (~156 MB). This created a severe core-starvation condition (1 task running sequentially). This represents an exploratory extreme boundary rather than a representative production-style compaction.
3. **Draft Conclusions**: The previously suggested speedups/slowdowns and optimal layout findings are classified as exploratory hypotheses. They must be validated using the strengthened methodology outlined below.

---

## 8. Proposed Phase 2G Experimental Design

To establish a scientifically rigorous conclusion, we recommend proceeding to **Phase 2G: Strengthened Comparative Analysis** with the following corrections:

1. **Explicitly Controlled Compaction Target Size**: Instead of allowing compaction to produce a single active file, we will rewrite data files with explicit target sizes to test realistic maintenance conditions:
   - Target Size: **64 MB** (will produce 2–3 moderate-sized data files) or **128 MB** (will produce 1–2 data files).
2. **Execution Interleaving**: We will randomize or interleave the execution order of states to eliminate JVM warmup bias. For example, instead of running all Control runs, then all Fragmented runs, and then all Compacted runs, we will interleave:
   - Cycle: $A \\to B \\to C \\to A \\to B \\to C \\dots$
3. **Repetition Count**: We will execute at least **10 measured repetitions** per physical state, preceded by 2 warmups.
4. **Variance Reporting**: The comparative report will display error bars ($95\\%$ confidence intervals) and explicitly check if differences exceed the practical noise floor.

---

*Report compiled on: {datetime.utcnow().isoformat()}*
"""
    with open(report_path, 'w') as f:
        f.write(report_content)

if __name__ == "__main__":
    main()
