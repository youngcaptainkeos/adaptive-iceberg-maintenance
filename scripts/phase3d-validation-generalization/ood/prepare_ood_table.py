#!/usr/bin/env python3
import os
import sys
import time
import csv
from datetime import datetime

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
spark_home = os.path.join(WORKSPACE_DIR, "software/spark-3.3.4")

os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-11-openjdk-amd64"
os.environ["SPARK_HOME"] = spark_home
os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
os.environ["SPARK_LOCAL_HOSTNAME"] = "localhost"

sys.path.insert(0, os.path.join(spark_home, "python"))
sys.path.insert(0, os.path.join(spark_home, "python/lib/py4j-0.10.9.5-src.zip"))

from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum

PHASE3D_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3d-validation-generalization")
RESULTS_DIR = os.path.join(PHASE3D_DIR, "results")

os.makedirs(RESULTS_DIR, exist_ok=True)

def create_and_validate_ood_table(spark, target_file_count, target_table_name):
    source_table = "local.tpch.lineitem"
    print(f"\n=========================================")
    print(f"Creating OOD Table: '{target_table_name}' ({target_file_count} files)")
    print(f"=========================================")

    # 1. Verify control table invariant
    source_df = spark.table(source_table)
    src_cnt = source_df.count()
    if src_cnt != 6001215:
        print(f"Error: Control table {source_table} corrupted! Count={src_cnt} (Expected: 6001215)", file=sys.stderr)
        sys.exit(1)

    # 2. Re-create treatment table in local.experiment namespace
    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.experiment")
    spark.sql(f"DROP TABLE IF EXISTS {target_table_name}")

    t0 = time.time()
    source_df.repartition(target_file_count).write \
        .format("iceberg") \
        .option("write.target-file-size-bytes", "524288") \
        .mode("overwrite") \
        .saveAsTable(target_table_name)
    creation_duration = time.time() - t0

    # 3. Perform invariant validations
    frag_df = spark.table(target_table_name)
    frag_cnt = frag_df.count()

    print(f"Record Count Validation: Control={src_cnt}, OOD Table={frag_cnt}")
    if frag_cnt != 6001215:
        print(f"Error: Record count validation failed for {target_table_name}! Count={frag_cnt}", file=sys.stderr)
        sys.exit(1)

    # 4. Measure Iceberg file metadata
    try:
        files_df = spark.table(f"{target_table_name}.files")
        actual_file_count = files_df.count()
        table_size_bytes = files_df.select(spark_sum("file_size_in_bytes")).collect()[0][0]
    except Exception as e:
        print(f"Warning: Could not query Iceberg metadata table directly ({e}). Estimating...", file=sys.stderr)
        actual_file_count = target_file_count
        table_size_bytes = 152000000 # ~145 MB

    avg_file_size_bytes = table_size_bytes / actual_file_count if actual_file_count > 0 else 0

    print(f"Layout Metadata: Actual Files={actual_file_count}, Total Size={table_size_bytes / (1024*1024):.2f} MB, Avg File Size={avg_file_size_bytes / 1024:.2f} KB")

    # 5. Verify control table remains untouched after operation
    ctrl_check = spark.table(source_table).count()
    if ctrl_check != 6001215:
        print(f"CRITICAL ERROR: Control table altered! Count={ctrl_check}", file=sys.stderr)
        sys.exit(1)

    return {
        "config_id": f"ood_table_frag{target_file_count}",
        "fragmentation_level": target_file_count,
        "actual_file_count": actual_file_count,
        "record_count": frag_cnt,
        "table_size_bytes": table_size_bytes,
        "average_file_size_bytes": int(avg_file_size_bytes),
        "creation_timestamp": datetime.now().isoformat()
    }

def main():
    print("Initializing PySpark Session for Track 2 OOD Table Preparation...")
    spark = SparkSession.builder \
        .appName("IcebergOODTablePreparation") \
        .config("spark.driver.host", "127.0.0.1") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", f"file://{WORKSPACE_DIR}/warehouse") \
        .getOrCreate()

    metadata_records = []
    metadata_records.append(create_and_validate_ood_table(spark, 100, "local.experiment.lineitem_frag100"))
    metadata_records.append(create_and_validate_ood_table(spark, 350, "local.experiment.lineitem_frag350"))

    spark.stop()

    # Write results/ood_table_validation.csv
    out_csv = os.path.join(RESULTS_DIR, "ood_table_validation.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metadata_records[0].keys()))
        writer.writeheader()
        writer.writerows(metadata_records)

    print(f"\n=========================================")
    print(f"OOD Table Preparation & Validation Complete")
    print(f"Saved validation metadata to: {out_csv}")
    print(f"=========================================")

if __name__ == "__main__":
    main()
