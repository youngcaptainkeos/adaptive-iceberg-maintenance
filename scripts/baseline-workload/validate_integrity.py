import sys
from pyspark.sql import SparkSession

def main():
    print("Initializing Spark session for data integrity validation...")
    spark = SparkSession.builder \
        .appName("IcebergDataIntegrityValidation") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse") \
        .getOrCreate()

    expected = {
        "local.tpch.lineitem": 6001215,
        "local.tpch.orders": 1500000,
        "local.tpch.customer": 150000
    }

    errors = 0
    print("\nVerifying Iceberg table row counts:")
    for table, expected_count in expected.items():
        try:
            actual_count = spark.table(table).count()
            if actual_count == expected_count:
                print(f"  [PASS] {table}: count = {actual_count}")
            else:
                print(f"  [FAIL] {table}: expected {expected_count}, got {actual_count}")
                errors += 1
        except Exception as e:
            print(f"  [FAIL] {table}: exception querying table: {e}")
            errors += 1

    spark.stop()

    if errors > 0:
        print("\nValidation failed with errors.")
        sys.exit(1)
    else:
        print("\nData integrity validation PASSED successfully.")
        sys.exit(0)

if __name__ == '__main__':
    main()
