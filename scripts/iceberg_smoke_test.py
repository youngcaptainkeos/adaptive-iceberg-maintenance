#!/usr/bin/env python3
import os
import shutil
from pyspark.sql import SparkSession

def main():
    # 1. Define paths
    project_root = "/home/shashank/Link to PDocuments/Capstone/implementation"
    warehouse_path = os.path.join(project_root, "warehouse")
    table_name = "local.smoke_test"
    
    print("=========================================")
    print("Starting Apache Iceberg Smoke Test")
    print("=========================================")
    print(f"Project root: {project_root}")
    print(f"Warehouse path: {warehouse_path}")
    print(f"Table identifier: {table_name}")
    print("-----------------------------------------")

    # 2. Build SparkSession with local Iceberg Hadoop catalog configuration
    print("A. Starting SparkSession and configuring 'local' Iceberg catalog...")
    os.makedirs(warehouse_path, exist_ok=True)
    warehouse_uri = "file://" + os.path.abspath(warehouse_path)
    print(f"   Warehouse URI: {warehouse_uri}")
    
    spark = SparkSession.builder \
        .appName("IcebergLocalHadoopSmokeTest") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", warehouse_uri) \
        .getOrCreate()

    # B. Verify Spark version
    spark_version = spark.version
    print(f"B. Spark version: {spark_version}")
    assert spark_version == "3.3.4", f"Unexpected Spark version: {spark_version}"

    # C. Verify Iceberg Catalog Configuration is recognized
    print("C. Verifying Iceberg catalog configuration...")
    # Create default namespace if not exists to ensure directory structure is initialized for listNamespaces
    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.default")
    # Check if 'local' catalog exists in Spark catalogs list by showing current databases/namespaces
    spark.sql("SHOW NAMESPACES IN local").show()
    print("   'local' catalog is recognized and accessible.")

    try:
        # D. Create a tiny test Iceberg table
        print(f"D. Creating Iceberg table: {table_name}...")
        spark.sql(f"DROP TABLE IF EXISTS {table_name}")
        spark.sql(f"CREATE TABLE {table_name} (id INT, name STRING) USING iceberg")
        print("   Table created successfully.")

        # E. Insert a few rows
        print("E. Inserting test rows into table...")
        spark.sql(f"INSERT INTO {table_name} VALUES (1, 'Alice'), (2, 'Bob'), (3, 'Charlie')")
        print("   Rows inserted successfully.")

        # F. Read the table back
        print("F. Reading rows back from table...")
        df = spark.sql(f"SELECT * FROM {table_name} ORDER BY id")
        rows = df.collect()
        
        # G. Print the resulting rows
        print("G. Rows read back:")
        for row in rows:
            print(f"   - ID: {row['id']}, Name: {row['name']}")
        
        # Validate count
        assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"

        # H. Print the table location and verify metadata creation
        print("H. Inspecting table location and metadata...")
        print("   Table description:")
        spark.sql(f"DESCRIBE EXTENDED {table_name}").show(truncate=False)
        # Since it is a Hadoop catalog, the path in warehouse is: <warehouse>/<database>/<table>
        # Our table identifier is 'local.smoke_test'. Under hadoop catalog 'local', the 'smoke_test' table
        # is placed in the default namespace, i.e. <warehouse>/default/smoke_test or <warehouse>/smoke_test.
        # Let's check both paths.
        table_dir_path = os.path.join(warehouse_path, "default", "smoke_test")
        if not os.path.exists(table_dir_path):
            # Try direct warehouse path
            table_dir_path = os.path.join(warehouse_path, "smoke_test")

        print(f"   Inferred Table directory: {table_dir_path}")
        print(f"   Directory exists: {os.path.exists(table_dir_path)}")
        
        # Verify metadata files exist
        metadata_dir = os.path.join(table_dir_path, "metadata")
        print(f"   Metadata directory: {metadata_dir}")
        print(f"   Metadata directory exists: {os.path.exists(metadata_dir)}")
        
        if os.path.exists(metadata_dir):
            files = os.listdir(metadata_dir)
            print("   Generated metadata files:")
            for f in sorted(files):
                print(f"     - {f}")
            assert len(files) > 0, "No metadata files found in metadata directory!"
        else:
            raise FileNotFoundError("Metadata directory not found in table path!")

        # I. Drop the table
        print(f"I. Dropping Iceberg table: {table_name}...")
        spark.sql(f"DROP TABLE {table_name}")
        print("   Table dropped successfully.")

    finally:
        # Clean up database/namespace directory if empty
        default_ns_path = os.path.join(warehouse_path, "default")
        if os.path.exists(default_ns_path) and not os.listdir(default_ns_path):
            os.rmdir(default_ns_path)
            print("   Cleaned up empty default namespace directory.")
            
        # Stop Spark Session
        spark.stop()
        print("Spark Session stopped.")
        
    print("=========================================")
    print("Smoke Test completed successfully!")
    print("=========================================")

if __name__ == "__main__":
    main()
