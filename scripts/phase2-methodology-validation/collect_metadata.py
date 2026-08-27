import os
import sys
import json
import socket
import platform
import subprocess
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

results_dir = "scripts/phase2-methodology-validation/results"
metadata_path = os.path.join(results_dir, "environment_metadata.json")

def get_cpu_model():
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        return platform.processor()
    except Exception:
        return "Unknown"

def get_total_memory():
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        mem_kb = int(line.split(":")[1].strip().split()[0])
                        return f"{mem_kb / (1024 * 1024):.2f} GB"
        return "Unknown"
    except Exception:
        return "Unknown"

def get_java_version():
    try:
        res = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # java -version outputs to stderr
        first_line = (res.stderr or res.stdout or "").split("\n")[0]
        return first_line.strip()
    except Exception:
        return "Unknown"

def main():
    print("Collecting system environment metadata...")
    os.makedirs(results_dir, exist_ok=True)

    # 1. Start Spark Session to inspect Iceberg table and catalog configs
    spark = SparkSession.builder \
        .appName("MetadataCollectionPhase2F") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    try:
        # 2. Query table properties & metrics
        control_df = spark.table("local.tpch.lineitem")
        row_count = control_df.count()

        files_df = spark.read.table("local.tpch.lineitem.files").filter(col("content") == 0)
        file_count = files_df.count()

        snapshots_df = spark.read.table("local.tpch.lineitem.snapshots")
        snapshot_count = snapshots_df.count()
        
        latest_snapshot = snapshots_df.orderBy(col("committed_at").desc()).first()
        current_snapshot_id = latest_snapshot["snapshot_id"] if latest_snapshot else "None"

        print(f"Control Table: Row Count={row_count}, File Count={file_count}, Snapshot ID={current_snapshot_id}")

        # Assert initial state is healthy
        assert row_count == 6001215, f"Expected 6,001,215 rows in tpch.lineitem, found {row_count}"
        assert file_count == 16, f"Expected 16 data files in tpch.lineitem, found {file_count}"

        # 3. Retrieve system hardware / configurations
        metadata = {
            "timestamp": platform.node(),  # Will overwrite below with current time
            "hostname": socket.gethostname(),
            "os_name": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "cpu_model": get_cpu_model(),
            "logical_cpu_cores": os.cpu_count(),
            "total_physical_memory": get_total_memory(),
            "spark_version": spark.version,
            "java_version": get_java_version(),
            "iceberg_version": "1.4.3 (from POM)",
            "warehouse_location": "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse",
            "catalog_name": "local",
            "catalog_type": "hadoop",
            "control_table": "local.tpch.lineitem",
            "control_table_rows": row_count,
            "control_table_files": file_count,
            "control_table_snapshot_id": str(current_snapshot_id),
            "control_table_snapshot_count": snapshot_count
        }

        # Format timestamp
        from datetime import datetime
        metadata["timestamp"] = datetime.now().isoformat()

        # Write to JSON
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)
        
        print(f"Successfully wrote environment metadata to {metadata_path}")

        # Save snapshot ID and file count for post-assertions
        with open(os.path.join(results_dir, "pre_assertion_state.json"), "w") as f:
            json.dump({
                "row_count": row_count,
                "snapshot_id": str(current_snapshot_id),
                "file_count": file_count
            }, f, indent=4)

    except Exception as e:
        print(f"Error during metadata collection / verification: {e}", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    spark.stop()
    print("Metadata collection completed successfully.")

if __name__ == "__main__":
    main()
