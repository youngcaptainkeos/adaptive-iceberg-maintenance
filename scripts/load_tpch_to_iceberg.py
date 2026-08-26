#!/usr/bin/env python3
import os
import sys
import time
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, IntegerType, LongType,
    StringType, DecimalType, DateType
)

# Standard TPC-H SF1 cardinalities for validation
EXPECTED_ROW_COUNTS = {
    "customer": 150000,
    "orders": 1500000,
    "lineitem": 6001215,
    "part": 200000,
    "partsupp": 800000,
    "supplier": 10000,
    "nation": 25,
    "region": 5
}

def main():
    project_root = "/home/shashank/Link to PDocuments/Capstone/implementation"
    warehouse_path = os.path.join(project_root, "warehouse")
    warehouse_uri = "file://" + os.path.abspath(warehouse_path)
    
    print("=========================================")
    print("TPC-H SF1 to Apache Iceberg Ingestion")
    print("=========================================")
    print(f"Warehouse URI: {warehouse_uri}")
    print("-----------------------------------------")

    # 1. Initialize Spark Session with Local Iceberg catalog
    print("Step 1: Initializing SparkSession...")
    spark = SparkSession.builder \
        .appName("TPCHToIcebergIngestion") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", warehouse_uri) \
        .getOrCreate()

    print(f"   Spark version: {spark.version}")
    
    # 2. Define Explicit Schemas for the 8 TPC-H tables
    schemas = {
        "customer": StructType([
            StructField("C_CUSTKEY", IntegerType(), False),
            StructField("C_NAME", StringType(), False),
            StructField("C_ADDRESS", StringType(), False),
            StructField("C_NATIONKEY", IntegerType(), False),
            StructField("C_PHONE", StringType(), False),
            StructField("C_ACCTBAL", DecimalType(15, 2), False),
            StructField("C_MKTSEGMENT", StringType(), False),
            StructField("C_COMMENT", StringType(), False)
        ]),
        
        "orders": StructType([
            StructField("O_ORDERKEY", LongType(), False),
            StructField("O_CUSTKEY", IntegerType(), False),
            StructField("O_ORDERSTATUS", StringType(), False),
            StructField("O_TOTALPRICE", DecimalType(15, 2), False),
            StructField("O_ORDERDATE", DateType(), False),
            StructField("O_ORDERPRIORITY", StringType(), False),
            StructField("O_CLERK", StringType(), False),
            StructField("O_SHIPPRIORITY", IntegerType(), False),
            StructField("O_COMMENT", StringType(), False)
        ]),
        
        "lineitem": StructType([
            StructField("L_ORDERKEY", LongType(), False),
            StructField("L_PARTKEY", IntegerType(), False),
            StructField("L_SUPPKEY", IntegerType(), False),
            StructField("L_LINENUMBER", IntegerType(), False),
            StructField("L_QUANTITY", DecimalType(15, 2), False),
            StructField("L_EXTENDEDPRICE", DecimalType(15, 2), False),
            StructField("L_DISCOUNT", DecimalType(15, 2), False),
            StructField("L_TAX", DecimalType(15, 2), False),
            StructField("L_RETURNFLAG", StringType(), False),
            StructField("L_LINESTATUS", StringType(), False),
            StructField("L_SHIPDATE", DateType(), False),
            StructField("L_COMMITDATE", DateType(), False),
            StructField("L_RECEIPTDATE", DateType(), False),
            StructField("L_SHIPINSTRUCT", StringType(), False),
            StructField("L_SHIPMODE", StringType(), False),
            StructField("L_COMMENT", StringType(), False)
        ]),
        
        "part": StructType([
            StructField("P_PARTKEY", IntegerType(), False),
            StructField("P_NAME", StringType(), False),
            StructField("P_MFGR", StringType(), False),
            StructField("P_BRAND", StringType(), False),
            StructField("P_TYPE", StringType(), False),
            StructField("P_SIZE", IntegerType(), False),
            StructField("P_CONTAINER", StringType(), False),
            StructField("P_RETAILPRICE", DecimalType(15, 2), False),
            StructField("P_COMMENT", StringType(), False)
        ]),
        
        "partsupp": StructType([
            StructField("PS_PARTKEY", IntegerType(), False),
            StructField("PS_SUPPKEY", IntegerType(), False),
            StructField("PS_AVAILQTY", IntegerType(), False),
            StructField("PS_SUPPLYCOST", DecimalType(15, 2), False),
            StructField("PS_COMMENT", StringType(), False)
        ]),
        
        "supplier": StructType([
            StructField("S_SUPPKEY", IntegerType(), False),
            StructField("S_NAME", StringType(), False),
            StructField("S_ADDRESS", StringType(), False),
            StructField("S_NATIONKEY", IntegerType(), False),
            StructField("S_PHONE", StringType(), False),
            StructField("S_ACCTBAL", DecimalType(15, 2), False),
            StructField("S_COMMENT", StringType(), False)
        ]),
        
        "nation": StructType([
            StructField("N_NATIONKEY", IntegerType(), False),
            StructField("N_NAME", StringType(), False),
            StructField("N_REGIONKEY", IntegerType(), False),
            StructField("N_COMMENT", StringType(), False)
        ]),
        
        "region": StructType([
            StructField("R_REGIONKEY", IntegerType(), False),
            StructField("R_NAME", StringType(), False),
            StructField("R_COMMENT", StringType(), False)
        ])
    }

    # 3. Create Iceberg namespace
    print("Step 2: Creating local.tpch namespace...")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.tpch")

    # 4. Load each table
    print("Step 3: Loading tables...")
    for table, schema in schemas.items():
        tbl_file_name = f"{table}.tbl"
        tbl_file_path = os.path.join(project_root, "datasets/tpch/sf1", tbl_file_name)
        tbl_uri = "file://" + os.path.abspath(tbl_file_path)
        
        print(f"  - Ingesting table: local.tpch.{table}")
        print(f"    Source: {tbl_uri}")
        
        if not os.path.exists(tbl_file_path):
            print(f"Error: Source file {tbl_file_path} not found!")
            sys.exit(1)
            
        start_time = time.time()
        
        # Read from pipe-delimited .tbl file with explicit schema
        df = spark.read \
            .option("sep", "|") \
            .schema(schema) \
            .csv(tbl_uri)
            
        # Idempotency Strategy: Drop existing table first
        spark.sql(f"DROP TABLE IF EXISTS local.tpch.{table}")
        
        # Write to Iceberg
        df.writeTo(f"local.tpch.{table}").create()
        
        duration = time.time() - start_time
        print(f"    Loaded in {duration:.2f} seconds.")

    # 5. Row Count and Schema Validation
    print("-----------------------------------------")
    print("Step 4: Validating table row counts...")
    validation_failures = 0
    actual_row_counts = {}
    
    for table, expected_count in EXPECTED_ROW_COUNTS.items():
        tbl_name = f"local.tpch.{table}"
        print(f"  - SELECT COUNT(*) FROM {tbl_name}")
        
        # Perform query validation
        actual_count = spark.sql(f"SELECT COUNT(*) FROM {tbl_name}").collect()[0][0]
        actual_row_counts[table] = actual_count
        
        if actual_count == expected_count:
            print(f"    SUCCESS: {actual_count} rows matches expected SF1 count.")
        else:
            print(f"    FAILURE: Got {actual_count} rows, expected {expected_count} rows!")
            validation_failures += 1
            
    if validation_failures > 0:
        print("Error: Schema validation failed! Row counts do not match standard TPC-H SF1 cardinalities.")
        sys.exit(1)
        
    print("All table row counts matched SF1 specifications.")

    # 6. Schema and Details Output
    print("-----------------------------------------")
    print("Step 5: Table details:")
    for table in EXPECTED_ROW_COUNTS.keys():
        tbl_name = f"local.tpch.{table}"
        print(f"\nDetails for {tbl_name}:")
        spark.sql(f"DESCRIBE EXTENDED {tbl_name}").show(truncate=False)

    # 7. Query Validation (joins, aggregations)
    print("-----------------------------------------")
    print("Step 6: Executing sample validation queries...")
    
    # Query 1: Join customer and nation
    print("\nQuery 1: Customer-Nation Join (First 5 rows)")
    query_join_cn = """
        SELECT c.C_CUSTKEY, c.C_NAME, n.N_NAME
        FROM local.tpch.customer c
        JOIN local.tpch.nation n ON c.C_NATIONKEY = n.N_NATIONKEY
        ORDER BY c.C_CUSTKEY
        LIMIT 5
    """
    spark.sql(query_join_cn).show()

    # Query 2: Join orders and customer
    print("Query 2: Orders-Customer Join (First 5 rows)")
    query_join_oc = """
        SELECT o.O_ORDERKEY, c.C_NAME, o.O_ORDERDATE, o.O_TOTALPRICE
        FROM local.tpch.orders o
        JOIN local.tpch.customer c ON o.O_CUSTKEY = c.C_CUSTKEY
        ORDER BY o.O_ORDERKEY
        LIMIT 5
    """
    spark.sql(query_join_oc).show()

    # Query 3: Simple aggregation over lineitem
    print("Query 3: Lineitem aggregation (quantities, discount, tax)")
    query_agg_l = """
        SELECT 
            SUM(L_QUANTITY) AS total_qty,
            AVG(L_EXTENDEDPRICE) AS avg_price,
            AVG(L_DISCOUNT) AS avg_discount,
            AVG(L_TAX) AS avg_tax
        FROM local.tpch.lineitem
    """
    spark.sql(query_agg_l).show()

    # 8. Check filesystem directories and files
    print("-----------------------------------------")
    print("Step 7: Validating local filesystem metadata...")
    for table in EXPECTED_ROW_COUNTS.keys():
        table_dir = os.path.join(warehouse_path, "tpch", table)
        metadata_dir = os.path.join(table_dir, "metadata")
        print(f"  - local.tpch.{table}:")
        print(f"    Table Dir: {table_dir} (Exists: {os.path.exists(table_dir)})")
        print(f"    Metadata Dir: {metadata_dir} (Exists: {os.path.exists(metadata_dir)})")
        if os.path.exists(metadata_dir):
            metadata_files = os.listdir(metadata_dir)
            print(f"    Found {len(metadata_files)} metadata files.")
            assert len(metadata_files) > 0, f"No metadata files found for {table}"
            
    print("-----------------------------------------")
    print("Ingestion and validation completed successfully!")
    print("=========================================")
    
    spark.stop()

if __name__ == "__main__":
    main()
