import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum

def main():
    print("Initializing Spark Session for table creation and fragmentation...")
    spark = SparkSession.builder \
        .appName("IcebergTableFragmentationCreationPhase2G") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    source_table = "local.tpch.lineitem"
    target_table = "local.experiment.lineitem_validated_fragmented"

    print(f"Source Table: {source_table}")
    print(f"Target Table: {target_table} (Intentional Small-File Stress Treatment)")

    # 1. Create Namespace
    print("Creating namespace local.experiment if not exists...")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.experiment")

    # 2. Drop existing fragmented table if it exists
    print(f"Dropping existing table {target_table} if exists...")
    spark.sql(f"DROP TABLE IF EXISTS {target_table}")

    # 3. Read control table
    print(f"Reading control data from {source_table}...")
    source_df = spark.table(source_table)
    
    # Check partition count
    print(f"Original logical partitions count: {source_df.rdd.getNumPartitions()}")

    # 4. Write data with repartitioning to 200 and setting target file size to 512 KB
    print("Writing fragmented table (repartitioning to 200 and target size 512KB)...")
    source_df.repartition(200).write \
        .format("iceberg") \
        .option("write.target-file-size-bytes", "524288") \
        .mode("overwrite") \
        .saveAsTable(target_table)

    print("Target table created successfully. Beginning logical validation...")

    # 5. Logical Equivalence Verifications
    fragmented_df = spark.table(target_table)

    # 5a. Row Count Validation
    source_count = source_df.count()
    fragmented_count = fragmented_df.count()
    print(f"Row count validation: Source={source_count}, Fragmented={fragmented_count}")

    if source_count != 6001215:
        print(f"Error: Source table row count {source_count} is incorrect (expected 6001215)", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    if fragmented_count != source_count:
        print(f"Error: Fragmented row count {fragmented_count} does not match source row count {source_count}", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    # 5b. Schema Verification
    schemas_match = (source_df.schema == fragmented_df.schema)
    print(f"Schema matching result: {schemas_match}")
    if not schemas_match:
        print("Error: Fragmented table schema does not match source table schema!", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    # 5c. Aggregates Checksum Validation (Sum of L_QUANTITY, L_EXTENDEDPRICE, L_DISCOUNT)
    print("Calculating aggregates checksums...")
    source_aggs = source_df.select(
        spark_sum("l_quantity").alias("sum_qty"),
        spark_sum("l_extendedprice").alias("sum_price"),
        spark_sum("l_discount").alias("sum_disc")
    ).collect()[0]

    frag_aggs = fragmented_df.select(
        spark_sum("l_quantity").alias("sum_qty"),
        spark_sum("l_extendedprice").alias("sum_price"),
        spark_sum("l_discount").alias("sum_disc")
    ).collect()[0]

    print(f"Source Aggs: Sum Qty={source_aggs['sum_qty']}, Sum Price={source_aggs['sum_price']}, Sum Disc={source_aggs['sum_disc']}")
    print(f"Fragmented Aggs: Sum Qty={frag_aggs['sum_qty']}, Sum Price={frag_aggs['sum_price']}, Sum Disc={frag_aggs['sum_disc']}")

    if source_aggs['sum_qty'] != frag_aggs['sum_qty'] or \
       source_aggs['sum_price'] != frag_aggs['sum_price'] or \
       source_aggs['sum_disc'] != frag_aggs['sum_disc']:
        print("Error: Aggregates checksum validation failed!", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    # 5d. File Count Validation (Expect ~200 files)
    file_df = spark.read.format("iceberg").load("local.experiment.lineitem_validated_fragmented.files")
    file_count = file_df.count()
    print(f"Fragmented File Count: {file_count}")
    if file_count < 180:
        print(f"Error: Fragmented table has too few files: {file_count}", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    print("Logical and physical state validation for Fragmented table PASSED.")
    spark.stop()

if __name__ == "__main__":
    main()
