import os
import sys
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

results_dir = "scripts/phase2-methodology-validation/results"
pre_state_path = os.path.join(results_dir, "pre_assertion_state.json")

def main():
    print("Performing post-benchmark data integrity assertions...")
    
    if not os.path.exists(pre_state_path):
        print(f"Error: Pre-assertion state file not found at {pre_state_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(pre_state_path, "r") as f:
        pre_state = json.load(f)

    spark = SparkSession.builder \
        .appName("PostMetadataVerificationPhase2F") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    try:
        control_df = spark.table("local.tpch.lineitem")
        row_count = control_df.count()

        files_df = spark.read.table("local.tpch.lineitem.files").filter(col("content") == 0)
        file_count = files_df.count()

        snapshots_df = spark.read.table("local.tpch.lineitem.snapshots")
        latest_snapshot = snapshots_df.orderBy(col("committed_at").desc()).first()
        current_snapshot_id = latest_snapshot["snapshot_id"] if latest_snapshot else "None"

        print(f"Post-Benchmark Control Table: Row Count={row_count}, File Count={file_count}, Snapshot ID={current_snapshot_id}")

        assert row_count == pre_state["row_count"], f"Row count changed! Pre: {pre_state['row_count']}, Post: {row_count}"
        assert file_count == pre_state["file_count"], f"File count changed! Pre: {pre_state['file_count']}, Post: {file_count}"
        assert str(current_snapshot_id) == pre_state["snapshot_id"], f"Snapshot ID changed! Pre: {pre_state['snapshot_id']}, Post: {current_snapshot_id}"
        
        print("Data integrity assertions PASSED: control table is completely unchanged.")

    except Exception as e:
        print(f"Error during post-benchmark verification: {e}", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    spark.stop()
    # Clean up pre-state file
    os.remove(pre_state_path)
    print("Post-benchmark verification completed successfully.")

if __name__ == "__main__":
    main()
