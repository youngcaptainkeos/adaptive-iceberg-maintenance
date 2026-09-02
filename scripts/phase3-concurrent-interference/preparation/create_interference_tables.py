import os
import sys
from pyspark.sql import SparkSession

def main():
    print("Initializing Spark Session to reset experimental tables...")
    
    # We must set the environment variables SPARK_LOCAL_IP and SPARK_LOCAL_HOSTNAME
    # in python to ensure Spark connects correctly.
    os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
    os.environ["SPARK_LOCAL_HOSTNAME"] = "localhost"
    
    workspace_dir = "/home/shashank/Link to PDocuments/Capstone/implementation"
    
    spark = SparkSession.builder \
        .appName("ResetInterferenceTables") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", f"file://{workspace_dir}/warehouse") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.warehouse.dir", f"file://{workspace_dir}/spark-warehouse") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
        
    try:
        table_name = "local.experiment.interference_treatment"
        print(f"Dropping and recreating experimental table: {table_name}")
        
        # Drop the table if it exists
        spark.sql(f"DROP TABLE IF EXISTS {table_name}")
        
        # Read from control table
        print("Reading data from control table local.tpch.lineitem...")
        lineitem_df = spark.read.table("local.tpch.lineitem")
        
        # Write to experimental table in a 200-file fragmented state
        print("Writing data with 200-way repartitioning to create a fragmented layout...")
        lineitem_df.repartition(200).write \
            .format("iceberg") \
            .mode("overwrite") \
            .saveAsTable(table_name)
            
        print(f"Successfully created experimental table {table_name}.")
        
    except Exception as e:
        print(f"Error resetting experimental tables: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
