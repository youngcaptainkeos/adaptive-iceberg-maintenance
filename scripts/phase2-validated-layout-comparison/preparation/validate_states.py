import os
import sys
import argparse
import os
import sys
import argparse
import csv
from pyspark.sql import SparkSession
from pyspark.sql.functions import min as spark_min, max as spark_max, avg as spark_avg, sum as spark_sum

def get_table_metrics(spark, table_name):
    print(f"Inspecting table: {table_name}...")
    
    # 1. Row count
    df = spark.table(table_name)
    row_count = df.count()
    
    # 2. Files metadata
    files_df = spark.read.format("iceberg").load(f"{table_name}.files")
    file_count = files_df.count()
    
    if file_count > 0:
        file_stats = files_df.select(
            spark_sum("file_size_in_bytes").alias("total_size"),
            spark_avg("file_size_in_bytes").alias("avg_size"),
            spark_min("file_size_in_bytes").alias("min_size"),
            spark_max("file_size_in_bytes").alias("max_size")
        ).collect()[0]
        
        total_size = file_stats["total_size"] or 0
        avg_size = file_stats["avg_size"] or 0
        min_size = file_stats["min_size"] or 0
        max_size = file_stats["max_size"] or 0
    else:
        total_size = 0
        avg_size = 0
        min_size = 0
        max_size = 0
        
    # 3. Snapshot metadata
    try:
        snapshots_df = spark.read.format("iceberg").load(f"{table_name}.snapshots")
        snapshot_count = snapshots_df.count()
        if snapshot_count > 0:
            current_snapshot_id = spark.table(table_name).history().filter("is_current_ancestor = true").select("snapshot_id").collect()[0]["snapshot_id"]
        else:
            current_snapshot_id = -1
    except Exception as e:
        print(f"Warning: could not read snapshots for {table_name}: {e}")
        snapshot_count = 0
        current_snapshot_id = -1
        
    return {
        "table_name": table_name,
        "row_count": row_count,
        "file_count": file_count,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "avg_file_size_bytes": round(avg_size, 2),
        "avg_file_size_mb": round(avg_size / (1024 * 1024), 2),
        "min_file_size_bytes": min_size,
        "max_file_size_bytes": max_size,
        "snapshot_count": snapshot_count,
        "current_snapshot_id": str(current_snapshot_id)
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["pre", "post"], required=True, help="Validation phase: pre or post benchmark")
    args = parser.parse_args()

    print(f"Starting state validation phase: {args.phase.upper()}")
    
    spark = SparkSession.builder \
        .appName(f"IcebergTableStateValidation_{args.phase}") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    tables = [
        "local.tpch.lineitem",
        "local.experiment.lineitem_validated_fragmented",
        "local.experiment.lineitem_validated_compacted"
    ]

    metrics_list = []
    for t in tables:
        try:
            m = get_table_metrics(spark, t)
            metrics_list.append(m)
        except Exception as e:
            print(f"Error inspecting table {t}: {e}", file=sys.stderr)
            spark.stop()
            sys.exit(1)

    headers = [
        "table_name", "row_count", "file_count", "total_size_bytes",
        "total_size_mb", "avg_file_size_bytes", "avg_file_size_mb",
        "min_file_size_bytes", "max_file_size_bytes", "snapshot_count",
        "current_snapshot_id"
    ]

    print("\n--- Physical Layout Metrics ---")
    format_str = "{:<48} {:<10} {:<10} {:<16} {:<14} {:<20} {:<18} {:<20} {:<20} {:<14} {:<20}"
    print(format_str.format(*headers))
    for m in metrics_list:
        print(format_str.format(*[str(m[h]) for h in headers]))
    print("--------------------------------\n")

    results_dir = "scripts/phase2-validated-layout-comparison/results"
    os.makedirs(results_dir, exist_ok=True)
    
    if args.phase == "pre":
        metrics_csv_path = os.path.join(results_dir, "physical_state_metrics.csv")
        with open(metrics_csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(metrics_list)
        print(f"Pre-benchmark physical state metrics written to {metrics_csv_path}")
    else:
        # Load pre-benchmark metrics for assertion checks
        pre_csv_path = os.path.join(results_dir, "physical_state_metrics.csv")
        if not os.path.exists(pre_csv_path):
            print(f"Error: Pre-benchmark metrics CSV not found at {pre_csv_path}", file=sys.stderr)
            spark.stop()
            sys.exit(1)
            
        pre_metrics = []
        with open(pre_csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pre_metrics.append(row)
                
        # Save post-benchmark metrics
        post_csv_path = os.path.join(results_dir, "physical_state_metrics_post.csv")
        with open(post_csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(metrics_list)
        print(f"Post-benchmark physical state metrics written to {post_csv_path}")
        
        # Run assertions
        print("Running post-benchmark layout invariants validation...")
        
        for row in metrics_list:
            table_name = row["table_name"]
            pre_row = next((p for p in pre_metrics if p["table_name"] == table_name), None)
            if pre_row is None:
                print(f"Error: Table {table_name} missing from pre-benchmark metrics!", file=sys.stderr)
                spark.stop()
                sys.exit(1)
            
            # Assert row count
            if int(row["row_count"]) != int(pre_row["row_count"]):
                print(f"Error: Table {table_name} row count changed! Pre={pre_row['row_count']}, Post={row['row_count']}", file=sys.stderr)
                spark.stop()
                sys.exit(1)
                
            # Assert file count
            if int(row["file_count"]) != int(pre_row["file_count"]):
                print(f"Error: Table {table_name} file count changed! Pre={pre_row['file_count']}, Post={row['file_count']}", file=sys.stderr)
                spark.stop()
                sys.exit(1)
                
            # Assert snapshot ID
            if str(row["current_snapshot_id"]) != str(pre_row["current_snapshot_id"]):
                print(f"Error: Table {table_name} current snapshot ID changed! Pre={pre_row['current_snapshot_id']}, Post={row['current_snapshot_id']}", file=sys.stderr)
                spark.stop()
                sys.exit(1)
                
        print("Post-benchmark layout invariants checks: PASSED. All tables remained completely read-only and unmodified.")

    spark.stop()

if __name__ == "__main__":
    main()
