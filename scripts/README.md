# Local Apache Iceberg Catalog Configuration & Smoke Test

This directory contains a reproducible verification script to configure and test a local, filesystem-backed Apache Iceberg catalog in our Spark/PySpark environment.

## 1. Why a Local Hadoop Iceberg Catalog is Used
For development, research, and reproducibility, we use a local Hadoop-style Iceberg catalog. It relies entirely on the local filesystem without requiring external metadata management services (like Hive Metastore, AWS Glue, or Nessie) or containerized databases. 

*Note: Since the local environment has HDFS configured as the default filesystem, we prepend the `file://` scheme to the warehouse path. This forces the Hadoop filesystem provider to write directly to the local disk instead of HDFS.*

## 2. Catalog & Environment Metadata
- **Catalog Name:** `local`
- **Catalog Type:** `hadoop`
- **Warehouse Location:** `warehouse/` (under the project root `/home/shashank/Link to PDocuments/Capstone/implementation/warehouse`)
- **Spark Version:** 3.3.4
- **Iceberg Spark Runtime Version:** 1.4.3 (Scala 2.12)

## 3. How to Run the Smoke Test

Sourcing the environment variables is required before running the script:

```bash
# 1. Source the project environment variables
source setup_env.sh

# 2. Run the self-contained smoke test script
python3 scripts/iceberg_smoke_test.py
```

## 4. Expected Output & Validation
When executed, the script will:
1. Initialize the `SparkSession` with extensions and catalog options.
2. Confirm the Spark version is `3.3.4`.
3. Create a namespace `local.default` to initialize the directory structure.
4. Create a table `local.smoke_test` with two columns: `id INT`, `name STRING`.
5. Write 3 rows (`Alice`, `Bob`, `Charlie`) to verify write capabilities.
6. Retrieve and print the rows to verify read capabilities.
7. Print the table location (`file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse/smoke_test`).
8. Inspect the local filesystem `warehouse/smoke_test/metadata` folder to list the generated Iceberg metadata files (like `v1.metadata.json`, `v2.metadata.json`, etc.).
9. Drop the table to prevent cluttering the warehouse directory.
10. Exit cleanly with code `0`.
