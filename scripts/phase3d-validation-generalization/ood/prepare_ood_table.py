#!/usr/bin/env python3
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum

def create_ood_table(spark, num_files, target_table_name):
    source_table = "local.tpch.lineitem"
    print(f"Creating OOD table '{target_table_name}' repartitioned to {num_files} files...")

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.experiment")
    spark.sql(f"DROP TABLE IF EXISTS {target_table_name}")

    source_df = spark.table(source_table)
    source_df.repartition(num_files).write \
        .format("iceberg") \
        .option("write.target-file-size-bytes", "524288") \
        .mode("overwrite") \
        .saveAsTable(target_table_name)

    # Invariant Validations
    frag_df = spark.table(target_table_name)
    src_cnt = source_df.count()
    frag_cnt = frag_df.count()

    print(f"Row count validation: Source={src_cnt}, OOD Table={frag_cnt}")
    if src_cnt != 6001215 or frag_cnt != src_cnt:
        print(f"Error: Row count validation failed for {target_table_name}!", file=sys.stderr)
        sys.exit(1)

    print(f"OOD Table '{target_table_name}' created successfully and verified.")

def main():
    print("Initializing Spark Session for OOD table fragmentation...")
    spark = SparkSession.builder \
        .appName("IcebergOODTableCreation") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    create_ood_table(spark, 100, "local.experiment.lineitem_frag100")
    create_ood_table(spark, 350, "local.experiment.lineitem_frag350")

    spark.stop()

if __name__ == "__main__":
    main()
