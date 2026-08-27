import sys
import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum

def main():
    print("Initializing Spark Session for table creation and realistic compaction...")
    spark = SparkSession.builder \
        .appName("IcebergTableCompactionCreationPhase2G") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    source_table = "local.tpch.lineitem"
    target_table = "local.experiment.lineitem_validated_compacted"

    print(f"Source Table: {source_table}")
    print(f"Target Table: {target_table} (Realistically Compacted Treatment)")

    # 1. Create Namespace
    print("Creating namespace local.experiment if not exists...")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.experiment")

    # 2. Drop existing table if it exists
    print(f"Dropping existing table {target_table} if exists...")
    spark.sql(f"DROP TABLE IF EXISTS {target_table}")

    # 3. Read control table
    print(f"Reading control data from {source_table}...")
    source_df = spark.table(source_table)

    # 4. Write data with repartitioning to 200 first (to mimic fragmented state)
    print("Writing temporary fragmented layout before compaction...")
    source_df.repartition(200).write \
        .format("iceberg") \
        .option("write.target-file-size-bytes", "524288") \
        .mode("overwrite") \
        .saveAsTable(target_table)

    # Check pre-compaction file count
    pre_file_count = spark.read.format("iceberg").load(f"{target_table}.files").count()
    print(f"Pre-compaction file count: {pre_file_count}")

    # 5. Run the rewrite_data_files procedure with explicit 64 MB target file size
    print("Executing rewrite_data_files compaction with 64 MB target file size...")
    compaction_query = f"CALL local.system.rewrite_data_files(table => 'experiment.lineitem_validated_compacted', options => map('target-file-size-bytes', '67108864'))"
    print(f"Query: {compaction_query}")
    
    start_time = time.time()
    result_df = spark.sql(compaction_query)
    result_rows = result_df.collect()
    duration = time.time() - start_time
    
    print(f"Compaction completed in {duration:.3f} seconds.")
    if len(result_rows) > 0:
        print("Compaction execution metrics:")
        print(result_rows[0])
    
    # 6. Logical Equivalence Verifications
    compacted_df = spark.table(target_table)

    # 6a. Row Count Validation
    source_count = source_df.count()
    compacted_count = compacted_df.count()
    print(f"Row count validation: Source={source_count}, Compacted={compacted_count}")

    if source_count != 6001215:
        print(f"Error: Source table row count {source_count} is incorrect (expected 6001215)", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    if compacted_count != source_count:
        print(f"Error: Compacted row count {compacted_count} does not match source row count {source_count}", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    # 6b. Schema Verification
    schemas_match = (source_df.schema == compacted_df.schema)
    print(f"Schema matching result: {schemas_match}")
    if not schemas_match:
        print("Error: Compacted table schema does not match source table schema!", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    # 6c. Aggregates Checksum Validation (Sum of L_QUANTITY, L_EXTENDEDPRICE, L_DISCOUNT)
    print("Calculating aggregates checksums...")
    source_aggs = source_df.select(
        spark_sum("l_quantity").alias("sum_qty"),
        spark_sum("l_extendedprice").alias("sum_price"),
        spark_sum("l_discount").alias("sum_disc")
    ).collect()[0]

    comp_aggs = compacted_df.select(
        spark_sum("l_quantity").alias("sum_qty"),
        spark_sum("l_extendedprice").alias("sum_price"),
        spark_sum("l_discount").alias("sum_disc")
    ).collect()[0]

    print(f"Source Aggs: Sum Qty={source_aggs['sum_qty']}, Sum Price={source_aggs['sum_price']}, Sum Disc={source_aggs['sum_disc']}")
    print(f"Compacted Aggs: Sum Qty={comp_aggs['sum_qty']}, Sum Price={comp_aggs['sum_price']}, Sum Disc={comp_aggs['sum_disc']}")

    if source_aggs['sum_qty'] != comp_aggs['sum_qty'] or \
       source_aggs['sum_price'] != comp_aggs['sum_price'] or \
       source_aggs['sum_disc'] != comp_aggs['sum_disc']:
        print("Error: Aggregates checksum validation failed!", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    # 6d. File Count Validation (Should be consolidated but not 1 giant file)
    post_file_df = spark.read.format("iceberg").load(f"{target_table}.files")
    post_file_count = post_file_df.count()
    print(f"Compacted File Count: {post_file_count}")
    if post_file_count <= 0:
        print(f"Error: Compacted table has no files!", file=sys.stderr)
        spark.stop()
        sys.exit(1)
        
    if post_file_count == 1:
        print("Warning: Table was compacted into a single file anyway. This will be recorded and analyzed.")

    print("Logical and physical state validation for Compacted table PASSED.")
    spark.stop()

if __name__ == "__main__":
    main()
