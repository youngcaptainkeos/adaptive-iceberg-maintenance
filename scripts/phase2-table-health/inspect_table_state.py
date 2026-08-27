import os
import json
import csv
import sys
import math
import statistics
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, min as spark_min, max as spark_max, sum as spark_sum, avg as spark_avg

results_dir = "scripts/phase2-table-health/results"

def main():
    print("Initializing Spark Session...")
    spark = SparkSession.builder \
        .appName("IcebergTableHealthInspection") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    table_name = "local.tpch.lineitem"
    
    print(f"Inspecting table: {table_name}")
    os.makedirs(results_dir, exist_ok=True)

    # 1. Row Count
    try:
        row_count = spark.table(table_name).count()
        print(f"Row count: {row_count}")
    except Exception as e:
        print(f"Error: Table {table_name} could not be queried: {e}", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    # 2. Query Files Metadata Table
    print("Reading data files metadata...")
    files_df = spark.read.table(f"{table_name}.files")
    # Columns: content, file_path, file_format, record_count, file_size_in_bytes
    # Filter for data files only (content == 0)
    data_files_df = files_df.filter(col("content") == 0)
    
    data_files = data_files_df.select("file_path", "file_format", "record_count", "file_size_in_bytes").collect()
    
    num_data_files = len(data_files)
    file_sizes = [row["file_size_in_bytes"] for row in data_files]
    total_data_size_bytes = sum(file_sizes)
    
    if num_data_files > 0:
        avg_data_file_size_bytes = total_data_size_bytes / num_data_files
        min_data_file_size_bytes = min(file_sizes)
        max_data_file_size_bytes = max(file_sizes)
        median_data_file_size_bytes = statistics.median(file_sizes)
    else:
        avg_data_file_size_bytes = 0.0
        min_data_file_size_bytes = 0
        max_data_file_size_bytes = 0
        median_data_file_size_bytes = 0.0

    print(f"Data files: {num_data_files}, Total size: {total_data_size_bytes} bytes")

    # 3. Query Snapshots Metadata Table
    print("Reading snapshot history metadata...")
    snapshots_df = spark.read.table(f"{table_name}.snapshots")
    snapshots = snapshots_df.select("snapshot_id", "parent_id", "committed_at", "operation", "summary").collect()
    num_snapshots = len(snapshots)

    # Determine current snapshot (latest committed_at)
    current_snapshot_id = None
    if num_snapshots > 0:
        latest_snapshot = snapshots_df.orderBy(col("committed_at").desc()).first()
        current_snapshot_id = latest_snapshot["snapshot_id"]

    print(f"Snapshots: {num_snapshots}, Current Snapshot ID: {current_snapshot_id}")

    # 4. Bucketed File Size Distribution
    # Buckets:
    # < 1 MB
    # 1-10 MB
    # 10-50 MB
    # 50-100 MB
    # 100-250 MB
    # 250 MB-1 GB
    # > 1 GB
    buckets = [
        {"name": "< 1 MB", "min": 0, "max": 1 * 1024 * 1024 - 1},
        {"name": "1-10 MB", "min": 1 * 1024 * 1024, "max": 10 * 1024 * 1024 - 1},
        {"name": "10-50 MB", "min": 10 * 1024 * 1024, "max": 50 * 1024 * 1024 - 1},
        {"name": "50-100 MB", "min": 50 * 1024 * 1024, "max": 100 * 1024 * 1024 - 1},
        {"name": "100-250 MB", "min": 100 * 1024 * 1024, "max": 250 * 1024 * 1024 - 1},
        {"name": "250 MB-1 GB", "min": 250 * 1024 * 1024, "max": 1024 * 1024 * 1024 - 1},
        {"name": "> 1 GB", "min": 1024 * 1024 * 1024, "max": math.inf}
    ]

    bucket_counts = {b["name"]: {"count": 0, "total_bytes": 0} for b in buckets}
    for size in file_sizes:
        for b in buckets:
            if b["min"] <= size <= b["max"]:
                bucket_counts[b["name"]]["count"] += 1
                bucket_counts[b["name"]]["total_bytes"] += size
                break

    # 5. Output Files Generation
    # JSON Summary
    baseline_json = {
        "catalog": "local",
        "database": "tpch",
        "table_name": "lineitem",
        "full_identifier": table_name,
        "row_count": row_count,
        "num_data_files": num_data_files,
        "total_data_size_bytes": total_data_size_bytes,
        "avg_data_file_size_bytes": avg_data_file_size_bytes,
        "median_data_file_size_bytes": median_data_file_size_bytes,
        "min_data_file_size_bytes": min_data_file_size_bytes,
        "max_data_file_size_bytes": max_data_file_size_bytes,
        "num_snapshots": num_snapshots,
        "current_snapshot_id": current_snapshot_id
    }
    
    json_path = os.path.join(results_dir, "table_health_baseline.json")
    with open(json_path, 'w') as f:
        json.dump(baseline_json, f, indent=2)
    print(f"Wrote summary to {json_path}")

    # CSV: File Metrics
    files_csv_path = os.path.join(results_dir, "file_metrics.csv")
    with open(files_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["file_path", "file_format", "record_count", "file_size_in_bytes"])
        for row in data_files:
            writer.writerow([row["file_path"], row["file_format"], row["record_count"], row["file_size_in_bytes"]])
    print(f"Wrote file metrics to {files_csv_path}")

    # CSV: Snapshot History
    snapshots_csv_path = os.path.join(results_dir, "snapshot_history.csv")
    with open(snapshots_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["snapshot_id", "parent_id", "committed_at", "operation", "summary"])
        for row in snapshots:
            writer.writerow([row["snapshot_id"], row["parent_id"], str(row["committed_at"]), row["operation"], str(row["summary"])])
    print(f"Wrote snapshot history to {snapshots_csv_path}")

    # CSV: File Size Distribution
    dist_csv_path = os.path.join(results_dir, "file_size_distribution.csv")
    with open(dist_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["bucket", "count", "total_bytes"])
        for b in buckets:
            name = b["name"]
            writer.writerow([name, bucket_counts[name]["count"], bucket_counts[name]["total_bytes"]])
    print(f"Wrote file size distribution to {dist_csv_path}")

    # 6. Generate Human-Readable Markdown Report
    report_path = os.path.join(results_dir, "table_health_report.md")
    generate_markdown_report(report_path, baseline_json, bucket_counts, data_files, snapshots)
    print(f"Wrote health report to {report_path}")

    spark.stop()

def generate_markdown_report(report_path, summary, bucket_counts, data_files, snapshots):
    # Format size helper
    def format_bytes(b):
        if b >= 1024*1024*1024:
            return f"{b / (1024*1024*1024):.2f} GB"
        elif b >= 1024*1024:
            return f"{b / (1024*1024):.2f} MB"
        elif b >= 1024:
            return f"{b / 1024:.2f} KB"
        else:
            return f"{b} Bytes"

    # Distribution Table
    dist_rows = ""
    for bucket_name, stats in bucket_counts.items():
        dist_rows += f"| {bucket_name} | {stats['count']} | {format_bytes(stats['total_bytes'])} |\n"

    # Snapshot Table
    snapshot_rows = ""
    for s in snapshots:
        parent_str = s["parent_id"] if s["parent_id"] is not None else "None"
        snapshot_rows += f"| `{s['snapshot_id']}` | `{parent_str}` | `{s['committed_at']}` | **{s['operation']}** |\n"

    # Files Table (truncate if too long, let's show all since it is 16)
    files_rows = ""
    for f in data_files:
        basename = os.path.basename(f["file_path"])
        files_rows += f"| `{basename}` | {f['record_count']:,} | {format_bytes(f['file_size_in_bytes'])} |\n"

    # Storage analysis interpretation
    interpretation = ""
    avg_size_mb = summary['avg_data_file_size_bytes'] / (1024*1024)
    if summary['num_data_files'] > 0 and avg_size_mb >= 8.0:
        interpretation = (
            f"The table is currently in a **healthy, consolidated physical storage state**. "
            f"It consists of {summary['num_data_files']} relatively large data files with an average size of {avg_size_mb:.2f} MB. "
            "This layout is optimal for scan-heavy analytical queries because it avoids the overhead of managing millions of tiny files."
        )
    else:
        interpretation = (
            f"The table is currently in a **fragmented or small-file storage state**. "
            f"It consists of {summary['num_data_files']} data files with a small average size of {avg_size_mb:.2f} MB. "
            "This will likely result in higher metadata scan latency and degraded analytical query execution times."
        )

    report_content = f"""# Apache Iceberg Table Health Report (Baseline)

This report documents the physical storage characteristics of the `local.tpch.lineitem` Iceberg table before any fragmentation experiments.

**Table Full Identifier:** `{summary['full_identifier']}`
**Analysis Time:** `{datetime.utcnow().isoformat()}Z`

---

## 1. Summary Statistics
- **Logical Row Count:** {summary['row_count']:,}
- **Number of Data Files:** {summary['num_data_files']}
- **Total Data Size:** {format_bytes(summary['total_data_size_bytes'])}
- **Average Data File Size:** {format_bytes(summary['avg_data_file_size_bytes'])}
- **Median Data File Size:** {format_bytes(summary['median_data_file_size_bytes'])}
- **Smallest Data File:** {format_bytes(summary['min_data_file_size_bytes'])}
- **Largest Data File:** {format_bytes(summary['max_data_file_size_bytes'])}
- **Number of Snapshots:** {summary['num_snapshots']}
- **Current Snapshot ID:** `{summary['current_snapshot_id']}`

---

## 2. File Size Distribution
Below is the breakdown of files classified by size buckets:

| Size Bucket | File Count | Total Size |
| :--- | :---: | :--- |
{dist_rows}

---

## 3. Snapshot History
Below is the historical lineage of committed snapshots:

| Snapshot ID | Parent Snapshot ID | Committed Time | Operation |
| :--- | :--- | :--- | :--- |
{snapshot_rows}

---

## 4. List of Data Files
Below are the individual data files comprising the active table state:

| File Name | Record Count | File Size |
| :--- | :---: | :--- |
{files_rows}

---

## 5. Storage State Interpretation
{interpretation}

These measurements will serve as the exact baseline (Phase 2A) to compare against future layout degradation (small-file insertions) and subsequent compaction/maintenance phases.
"""
    # Replace inline datetime with dynamic string
    report_content = report_content.replace("datetime.utcnow().isoformat()", datetime.utcnow().isoformat())

    with open(report_path, 'w') as f:
        f.write(report_content)

if __name__ == "__main__":
    from datetime import datetime
    main()
