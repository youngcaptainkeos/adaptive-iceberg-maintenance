import os
import json
import csv
import sys
import math
import statistics
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum

results_dir = "scripts/phase2-compaction/results"

def main():
    print("Initializing Spark Session for post-compaction inspection...")
    spark = SparkSession.builder \
        .appName("IcebergPostCompactionInspection") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    table_name = "local.experiment.lineitem_fragmented"
    
    print(f"Inspecting post-compaction table: {table_name}")
    os.makedirs(results_dir, exist_ok=True)

    # 1. Row Count and Checksums
    try:
        df = spark.table(table_name)
        row_count = df.count()
        print(f"Row count: {row_count}")
        
        # Calculate checksums
        print("Calculating baseline aggregates checksums...")
        checksums = df.select(
            spark_sum("l_quantity").alias("sum_qty"),
            spark_sum("l_extendedprice").alias("sum_price"),
            spark_sum("l_discount").alias("sum_disc")
        ).collect()[0]
        
        sum_qty = float(checksums["sum_qty"]) if checksums["sum_qty"] is not None else 0.0
        sum_price = float(checksums["sum_price"]) if checksums["sum_price"] is not None else 0.0
        sum_disc = float(checksums["sum_disc"]) if checksums["sum_disc"] is not None else 0.0
        
        print(f"Checksums: Sum Qty={sum_qty}, Sum Price={sum_price}, Sum Disc={sum_disc}")
    except Exception as e:
        print(f"Error: Table {table_name} could not be queried: {e}", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    # 2. Query Files Metadata Table
    print("Reading data files metadata...")
    files_df = spark.read.table(f"{table_name}.files")
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

    current_snapshot_id = None
    if num_snapshots > 0:
        latest_snapshot = snapshots_df.orderBy(col("committed_at").desc()).first()
        current_snapshot_id = latest_snapshot["snapshot_id"]

    print(f"Snapshots: {num_snapshots}, Current Snapshot ID: {current_snapshot_id}")

    # 4. Bucketed File Size Distribution
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
    post_metrics_json = {
        "catalog": "local",
        "database": "experiment",
        "table_name": "lineitem_fragmented",
        "full_identifier": table_name,
        "row_count": row_count,
        "sum_qty": sum_qty,
        "sum_price": sum_price,
        "sum_disc": sum_disc,
        "num_data_files": num_data_files,
        "total_data_size_bytes": total_data_size_bytes,
        "avg_data_file_size_bytes": avg_data_file_size_bytes,
        "median_data_file_size_bytes": median_data_file_size_bytes,
        "min_data_file_size_bytes": min_data_file_size_bytes,
        "max_data_file_size_bytes": max_data_file_size_bytes,
        "num_snapshots": num_snapshots,
        "current_snapshot_id": current_snapshot_id
    }
    
    json_path = os.path.join(results_dir, "post_compaction_metrics.json")
    with open(json_path, 'w') as f:
        json.dump(post_metrics_json, f, indent=2)
    print(f"Wrote post-compaction metrics to {json_path}")

    # CSV: File Metrics
    files_csv_path = os.path.join(results_dir, "post_compaction_file_metrics.csv")
    with open(files_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["file_path", "file_format", "record_count", "file_size_in_bytes"])
        for row in data_files:
            writer.writerow([row["file_path"], row["file_format"], row["record_count"], row["file_size_in_bytes"]])
    print(f"Wrote post-compaction file metrics to {files_csv_path}")

    # CSV: Snapshot History
    snapshots_csv_path = os.path.join(results_dir, "post_compaction_snapshot_history.csv")
    with open(snapshots_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["snapshot_id", "parent_id", "committed_at", "operation", "summary"])
        for row in snapshots:
            writer.writerow([row["snapshot_id"], row["parent_id"], str(row["committed_at"]), row["operation"], str(row["summary"])])
    print(f"Wrote post-compaction snapshot history to {snapshots_csv_path}")

    # CSV: File Size Distribution
    dist_csv_path = os.path.join(results_dir, "post_compaction_file_size_distribution.csv")
    with open(dist_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["bucket", "count", "total_bytes"])
        for b in buckets:
            name = b["name"]
            writer.writerow([name, bucket_counts[name]["count"], bucket_counts[name]["total_bytes"]])
    print(f"Wrote post-compaction file size distribution to {dist_csv_path}")

    spark.stop()

if __name__ == "__main__":
    main()
