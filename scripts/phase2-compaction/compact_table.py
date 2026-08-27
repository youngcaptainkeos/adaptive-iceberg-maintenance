import os
import sys
import time
from datetime import datetime
from pyspark.sql import SparkSession

logs_dir = "scripts/phase2-compaction/logs"

def main():
    print("Initializing Spark Session for Iceberg table compaction...")
    spark = SparkSession.builder \
        .appName("IcebergTableCompaction") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    table_name = "local.experiment.lineitem_fragmented"
    
    print(f"Starting compaction for table: {table_name}")
    os.makedirs(logs_dir, exist_ok=True)

    start_time = time.time()
    start_dt = datetime.now().isoformat()
    print(f"Compaction start time: {start_dt}")

    try:
        # Call the Iceberg rewrite_data_files procedure
        # The syntax for Hadoop catalog is CALL catalog.system.rewrite_data_files(table => 'db.table')
        compaction_query = f"CALL local.system.rewrite_data_files(table => 'experiment.lineitem_fragmented')"
        print(f"Executing: {compaction_query}")
        result_df = spark.sql(compaction_query)
        result_rows = result_df.collect()
        
        end_time = time.time()
        end_dt = datetime.now().isoformat()
        duration = end_time - start_time
        print(f"Compaction finished successfully at: {end_dt}")
        print(f"Compaction duration: {duration:.3f} seconds")
        
        # Display rewrite metrics returned by CALL
        # Typically returns columns: rewritten_data_files_count, added_data_files_count
        if len(result_rows) > 0:
            print("Compaction metrics returned by Iceberg:")
            print(result_rows[0])
            
            # Log metrics to file
            log_path = os.path.join(logs_dir, "compaction_execution.log")
            with open(log_path, 'w') as f:
                f.write(f"Start Time: {start_dt}\n")
                f.write(f"End Time: {end_dt}\n")
                f.write(f"Duration Seconds: {duration:.3f}\n")
                f.write(f"Query executed: {compaction_query}\n")
                f.write(f"Metrics: {str(result_rows[0].asDict())}\n")
                f.write("Status: SUCCESS\n")
            print(f"Wrote execution log to {log_path}")
        else:
            print("No metrics returned by rewrite_data_files CALL.")
            
    except Exception as e:
        print(f"Error during compaction execution: {e}", file=sys.stderr)
        end_time = time.time()
        end_dt = datetime.now().isoformat()
        duration = end_time - start_time
        
        log_path = os.path.join(logs_dir, "compaction_execution.log")
        with open(log_path, 'w') as f:
            f.write(f"Start Time: {start_dt}\n")
            f.write(f"End Time: {end_dt}\n")
            f.write(f"Duration Seconds: {duration:.3f}\n")
            f.write(f"Query: CALL local.system.rewrite_data_files(table => 'experiment.lineitem_fragmented')\n")
            f.write(f"Error: {e}\n")
            f.write("Status: FAILURE\n")
        
        spark.stop()
        sys.exit(1)

    spark.stop()

if __name__ == "__main__":
    main()
