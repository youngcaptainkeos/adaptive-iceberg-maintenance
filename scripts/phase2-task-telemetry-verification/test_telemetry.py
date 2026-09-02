import os
import sys
from pyspark.sql import SparkSession

def main():
    print("Testing Spark event log generation and plan capture...")
    
    # Define paths
    base_dir = "/home/shashank/Link to PDocuments/Capstone/implementation/scripts/phase2-task-telemetry-verification"
    event_log_dir = os.path.join(base_dir, "spark-events")
    os.makedirs(event_log_dir, exist_ok=True)
    
    # Configure SparkSession
    spark = SparkSession.builder \
        .appName("TestTelemetryVerification") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .config("spark.eventLog.enabled", "true") \
        .config("spark.eventLog.dir", event_log_dir) \
        .getOrCreate()
        
    try:
        states = {
            "Control": "local.tpch.lineitem",
            "Fragmented": "local.experiment.lineitem_validated_fragmented",
            "Compacted": "local.experiment.lineitem_validated_compacted"
        }
        
        for state_name, table_path in states.items():
            query_sql = f"""
            SELECT
                sum(l_extendedprice * l_discount) as revenue
            FROM
                {table_path}
            WHERE
                l_shipdate >= date '1994-01-01'
                AND l_shipdate < date '1994-01-01' + interval '1' year
                AND l_discount between 0.05 and 0.07
                AND l_quantity < 24
            """
            print(f"Running Q6 against {state_name} ({table_path})...")
            
            # Set Job Group
            spark.sparkContext.setJobGroup(f"q6_{state_name.lower()}", f"Q6 {state_name} query")
            
            df = spark.sql(query_sql)
            
            # Capture physical plan
            plan = df._jdf.queryExecution().toString()
            print(f"=== {state_name} Plan ===")
            print(plan[:300] + "\n...")
            
            # Trigger action to generate tasks
            result = df.collect()
            print(f"Result for {state_name}:", result)
        
    finally:
        # Stop Spark Session to flush event logs
        spark.stop()
        
    print("Listing files in event log directory:")
    for f in os.listdir(event_log_dir):
        print("  -", f)

if __name__ == "__main__":
    main()
