# Local Apache Iceberg Catalog Configuration & Ingestion Scripts

This directory contains reproducible verification and data loading scripts to configure and test a local, filesystem-backed Apache Iceberg catalog in our Spark/PySpark environment.

---

## 1. Why a Local Hadoop Iceberg Catalog is Used
For development, research, and reproducibility, we use a local Hadoop-style Iceberg catalog. It relies entirely on the local filesystem without requiring external metadata management services (like Hive Metastore, AWS Glue, or Nessie) or containerized databases. 

*Note: Since the local environment has HDFS configured as the default filesystem, we prepend the `file://` scheme to the warehouse path. This forces the Hadoop filesystem provider to write directly to the local disk instead of HDFS.*

## 2. Catalog & Environment Metadata
- **Catalog Name:** `local`
- **Catalog Type:** `hadoop`
- **Warehouse Location:** `warehouse/` (under the project root `/home/shashank/Link to PDocuments/Capstone/implementation/warehouse`)
- **Warehouse URI:** `file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse`
- **Spark Version:** 3.3.4
- **Iceberg Spark Runtime Version:** 1.4.3 (Scala 2.12)

---

## 3. Iceberg Catalog Smoke Test

Sourcing the environment variables is required before running the script:

```bash
# 1. Source the project environment variables
source setup_env.sh

# 2. Run the self-contained smoke test script
python3 scripts/iceberg_smoke_test.py
```

### Expected Output & Validation
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

---

## 4. TPC-H SF1 Data Ingestion

The script `scripts/load_tpch_to_iceberg.py` loads the validated TPC-H SF1 pipe-delimited `.tbl` files into properly typed Apache Iceberg tables under the namespace `local.tpch`.

### How to Run Ingestion

```bash
# 1. Source the project environment variables
source setup_env.sh

# 2. Run the ingestion and validation script
python3 scripts/load_tpch_to_iceberg.py
```

### Ingestion Details

#### Source TPC-H Location
* `datasets/tpch/sf1/` (containing `.tbl` files)

#### Created Table Names
* `local.tpch.customer`
* `local.tpch.orders`
* `local.tpch.lineitem`
* `local.tpch.part`
* `local.tpch.partsupp`
* `local.tpch.supplier`
* `local.tpch.nation`
* `local.tpch.region`

#### Explicit Schema Approach
Automatic schema inference is bypassed. Schemas are explicitly defined to use precise SQL types:
* **Keys/IDs:** `LongType` for `O_ORDERKEY` and `L_ORDERKEY` to support larger scales; `IntegerType` for other keys/ids.
* **Monetary fields:** `DecimalType(15, 2)` instead of floating-point representation.
* **Dates:** `DateType` for `yyyy-MM-dd` fields.
* **Text/Others:** `StringType` and `IntegerType` where appropriate.

*Trailing pipe handling:* TPC-H `.tbl` files have a trailing `|` character. When parsed with `sep=|` and an explicit schema matching the standard column count, Spark automatically reads the correct columns and discards the empty trailing field.

#### Idempotency Behavior
The script is safe to run multiple times. Before writing each table, it explicitly drops any existing table using `DROP TABLE IF EXISTS local.tpch.<table_name>` and then creates a fresh one via `df.writeTo(...).create()`. This guarantees that rows are never duplicated or appended multiple times.

#### Validation & Expected Row Counts
After loading, the script verifies each Iceberg table's cardinality against standard TPC-H SF1 specifications using `SELECT COUNT(*)`:

| Table | Expected Row Count |
| :--- | :--- |
| `customer` | 150,000 |
| `orders` | 1,500,000 |
| `lineitem` | 6,001,215 |
| `part` | 200,000 |
| `partsupp` | 800,000 |
| `supplier` | 10,000 |
| `nation` | 25 |
| `region` | 5 |

#### Query Validation
The script executes the following queries to prove correctness of relationships, joins, and types:
1. **Customer-Nation Join**: Verifies relationship mappings and simple joins.
2. **Orders-Customer Join**: Verifies larger primary/foreign key joins.
3. **Lineitem Aggregation**: Verifies arithmetic aggregations on decimal columns (`L_QUANTITY`, `L_EXTENDEDPRICE`, `L_DISCOUNT`, `L_TAX`).

#### Metadata Verification
Verifies that the `warehouse/tpch/<table_name>/metadata` directories contain the generated Iceberg metadata files (like `v1.metadata.json`, version hints, snapshots, and manifest files).
