import os
import sys
import argparse
from pyspark.sql import SparkSession

def get_spark_session(workspace_dir):
    os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
    os.environ["SPARK_LOCAL_HOSTNAME"] = "localhost"
    return SparkSession.builder \
        .appName("ValidateState") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", f"file://{workspace_dir}/warehouse") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.warehouse.dir", f"file://{workspace_dir}/spark-warehouse") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()

def validate_table(spark, table_name, expected_rows, expected_files=None, description=""):
    print(f"Validating {description} ({table_name})...")
    
    # Check if table exists
    try:
        # Check rows
        rows = spark.read.table(table_name).count()
        print(f"  Row Count: {rows} (Expected: {expected_rows})")
        if rows != expected_rows:
            print(f"  ERROR: Row count mismatch on {table_name}! Found {rows}, expected {expected_rows}.")
            return False
            
        # Check files
        files_df = spark.read.table(f"{table_name}.files")
        file_count = files_df.count()
        avg_size = files_df.selectExpr("avg(file_size_in_bytes)").collect()[0][0]
        avg_size_kb = (avg_size / 1024.0) if avg_size else 0
        
        print(f"  File Count: {file_count}")
        print(f"  Average File Size: {avg_size_kb:.2f} KB")
        
        if expected_files is not None:
            print(f"  Expected File Count: {expected_files}")
            if file_count != expected_files:
                print(f"  ERROR: File count mismatch on {table_name}! Found {file_count}, expected {expected_files}.")
                return False
                
        return True
    except Exception as e:
        print(f"  ERROR checking table {table_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Validate physical layout states of control and treatment tables")
    parser.add_argument("--mode", choices=["pre", "post"], required=True, help="Validation mode: pre-experiment or post-experiment")
    args = parser.parse_args()
    
    workspace_dir = "/home/shashank/Link to PDocuments/Capstone/implementation"
    spark = get_spark_session(workspace_dir)
    
    success = True
    try:
        # Always validate control table (must remain completely untouched)
        control_ok = validate_table(
            spark, 
            "local.tpch.lineitem", 
            expected_rows=6001215, 
            expected_files=16, 
            description="Control Table"
        )
        if not control_ok:
            success = False
            print("CRITICAL: Control table validation FAILED!")
            
        # Validate experimental table
        if args.mode == "pre":
            treatment_ok = validate_table(
                spark, 
                "local.experiment.interference_treatment", 
                expected_rows=6001215, 
                expected_files=200, 
                description="Treatment Table (Pre-experiment)"
            )
            if not treatment_ok:
                success = False
                print("CRITICAL: Treatment table layout validation FAILED!")
        else:
            print("Treatment Table (Post-experiment final state):")
            validate_table(
                spark, 
                "local.experiment.interference_treatment", 
                expected_rows=6001215, 
                expected_files=None, 
                description="Treatment Table (Post-experiment)"
            )
            
    finally:
        spark.stop()
        
    if not success:
        sys.exit(1)
    else:
        print("Validation completed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
