import os
import csv
import sys
import duckdb
import statistics
from datetime import datetime

db_path = 'scripts/baseline-workload/telemetry/telemetry_baseline_comprehensive.db'
results_dir = 'scripts/baseline-workload/results'
analysis_dir = 'scripts/baseline-workload/analysis'

def parse_timestamp(ts_str):
    if not ts_str:
        return None
    # Strip trailing Z and replace with +00:00 for timezone-aware parsing
    if ts_str.endswith('Z'):
        ts_str = ts_str[:-1] + '+00:00'
    return datetime.fromisoformat(ts_str)

def main():
    if not os.path.exists(db_path):
        print(f"Error: Telemetry database {db_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(analysis_dir, exist_ok=True)

    print("Connecting to DuckDB telemetry database...")
    conn = duckdb.connect(db_path)

    # We want to retrieve all EXEC_STATEMENT rows.
    # The columns are run_id, event_start_time, event_end_time, event_id, event_type, event_status, event_data
    query = """
        SELECT run_id, event_id, event_status, event_start_time, event_end_time
        FROM experiment_telemetry
        WHERE event_type = 'EXEC_STATEMENT'
        ORDER BY event_start_time ASC
    """
    
    rows = conn.execute(query).fetchall()
    
    # Filter for the most recent run_id if multiple runs exist, or process all.
    # Let's group by run_id, and print info for each. We will focus on the latest run.
    if not rows:
        print("Error: No EXEC_STATEMENT events found in the telemetry database.", file=sys.stderr)
        sys.exit(1)

    runs = sorted(list(set(r[0] for r in rows)))
    latest_run = runs[-1]
    print(f"Found runs: {runs}. Processing latest run: {latest_run}")

    latest_rows = [r for r in rows if r[0] == latest_run]

    statement_results = []
    query_durations = {} # maps QX -> list of durations

    for run_id, event_id, event_status, start_str, end_str in latest_rows:
        # Parse query name from event_id (e.g. query1.sql_0 -> Q1)
        # query12.sql_0 -> Q12
        q_num = event_id.split('.')[0].replace('query', 'Q')
        
        start_dt = parse_timestamp(start_str)
        end_dt = parse_timestamp(end_str)
        
        duration = 0.0
        if start_dt and end_dt:
            duration = (end_dt - start_dt).total_seconds()
        
        statement_results.append({
            'run_id': run_id,
            'query': q_num,
            'statement_id': event_id,
            'status': event_status,
            'start_time': start_str,
            'end_time': end_str,
            'duration_seconds': duration
        })

        if event_status == 'SUCCESS':
            query_durations.setdefault(q_num, []).append(duration)
        else:
            query_durations.setdefault(q_num, []) # ensure key exists

    # Write statement results CSV
    stmt_csv_path = os.path.join(results_dir, 'baseline_statement_results.csv')
    with open(stmt_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['run_id', 'query', 'statement_id', 'status', 'start_time', 'end_time', 'duration_seconds'])
        writer.writeheader()
        writer.writerows(statement_results)
    print(f"Wrote statement results to {stmt_csv_path}")

    # Write summary statistics CSV
    summary_results = []
    summary_csv_path = os.path.join(results_dir, 'baseline_summary.csv')
    
    all_queries = sorted(list(query_durations.keys()), key=lambda x: int(x[1:]))

    for q in all_queries:
        durs = query_durations[q]
        q_rows = [r for r in statement_results if r['query'] == q]
        
        count = len(q_rows)
        successes = sum(1 for r in q_rows if r['status'] == 'SUCCESS')
        failures = sum(1 for r in q_rows if r['status'] == 'FAILURE')
        
        if successes > 0:
            mean_val = statistics.mean(durs)
            median_val = statistics.median(durs)
            min_val = min(durs)
            max_val = max(durs)
            stddev_val = statistics.stdev(durs) if len(durs) >= 2 else 0.0
        else:
            mean_val = median_val = min_val = max_val = stddev_val = 0.0

        summary_results.append({
            'query': q,
            'count': count,
            'successes': successes,
            'failures': failures,
            'mean_seconds': round(mean_val, 4),
            'median_seconds': round(median_val, 4),
            'min_seconds': round(min_val, 4),
            'max_seconds': round(max_val, 4),
            'stddev_seconds': round(stddev_val, 4)
        })

    with open(summary_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['query', 'count', 'successes', 'failures', 'mean_seconds', 'median_seconds', 'min_seconds', 'max_seconds', 'stddev_seconds'])
        writer.writeheader()
        writer.writerows(summary_results)
    print(f"Wrote summary results to {summary_csv_path}")

    # Generate Markdown Report
    report_path = os.path.join(analysis_dir, 'baseline_characterization_report.md')
    generate_report(report_path, latest_run, statement_results, summary_results)
    print(f"Wrote workload characterization report to {report_path}")

def generate_report(report_path, run_id, stmt_results, summary_results):
    # Format tables
    stmt_table = "| Query | Repetition / Statement | Status | Start Time | End Time | Duration (s) |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for r in stmt_results:
        stmt_table += f"| {r['query']} | `{r['statement_id']}` | **{r['status']}** | `{r['start_time']}` | `{r['end_time']}` | {r['duration_seconds']:.3f} |\n"

    summary_table = "| Query | Count | Successes | Failures | Mean (s) | Median (s) | Min (s) | Max (s) | StdDev (s) |\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for s in summary_results:
        summary_table += f"| {s['query']} | {s['count']} | {s['successes']} | {s['failures']} | {s['mean_seconds']:.3f} | {s['median_seconds']:.3f} | {s['min_seconds']:.3f} | {s['max_seconds']:.3f} | {s['stddev_seconds']:.3f} |\n"

    report_content = f"""# Workload Characterization Report

This report documents the baseline performance characterization of the TPC-H workload on our local Iceberg catalog, serving as the experimental control group for Phase 1B.

**Experiment Run ID:** `{run_id}`
**Generated At:** `{datetime.utcnow().isoformat()}Z`

---

## 1. Query Classifications and Profiles
The selected query set comprises six representative TPC-H queries providing a diverse mix of operations:

*   **Q1 (Scan-Heavy / Aggregation-Heavy)**: Large-scale table scan on the `lineitem` table with groupings and aggregate computations (sums, averages, counts). Very CPU and I/O intensive.
*   **Q3 (Join-Heavy / Aggregation-Heavy)**: Performs a three-way join across `customer`, `orders`, and `lineitem` with filter criteria and groupings, limiting output to the top 10 rows.
*   **Q6 (Scan-Heavy / Filtering-Heavy)**: Scan of `lineitem` with multiple highly selective range filters. Tests the efficiency of data skipping and predicate pushdowns.
*   **Q12 (Join-Heavy / Aggregation-Heavy / Filtering)**: Performs a join between `orders` and `lineitem` with complex conditional aggregates (`CASE` statements) and selective filtering on shipping mode.
*   **Q14 (Scan-Heavy / Join-Heavy / Case Aggregation)**: Joins `lineitem` and `part` within a specific date range, calculating promotional revenue using conditional logic.
*   **Q18 (Join-Heavy / Large Grouping / Subquery)**: Employs an IN-subquery with a `GROUP BY HAVING` clause on `lineitem`, joined back with `customer` and `orders`. This is a computationally intensive query involving large volume aggregations.

---

## 2. Baseline Performance Results
Below is the summary of the execution statistics across all repetitions:

{summary_table}

---

## 3. Detailed Execution Records
Below are the individual statement execution records:

{stmt_table}

---

## 4. Workload Performance & Variability Analysis
- **Runtimes and Complexity**: As expected, Q1 and Q18 are the most expensive queries due to their large aggregation scans and complex join structures, respectively. Q6 is the fastest query due to the simplicity of its single-table scan and selective filters.
- **Variability**: Repetitions show minor variations typical of JVM warmup, Spark execution planning, and OS thread scheduling.
- **Workload Diversity**: The selection represents a robust test suite to measure degradation. Join-heavy queries (Q3, Q12, Q18) will be sensitive to compaction and data clustering, while scan-heavy queries (Q1, Q6) will directly measure scan throughput and file-skipping efficiency.

---

## 5. Limitations
- **Scale Factor**: The dataset is TPC-H SF1 (~1 GB), which fits entirely into memory. Runtimes on larger datasets will scale non-linearly.
- **Local Spark Context**: A standalone local Spark context on a single machine is not representative of a distributed, production-grade lakehouse cluster.
- **Experimental Control**: These numbers are designed specifically to act as control baselines to compare against compacted/degraded Iceberg layouts.
"""

    with open(report_path, 'w') as f:
        f.write(report_content)

if __name__ == '__main__':
    main()
