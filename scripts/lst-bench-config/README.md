# LST-Bench Custom Configuration for local Spark + Iceberg

This directory contains project-specific configurations to integrate Microsoft LST-Bench with our Capstone research environment for the **Lakehouse Storage Maintenance Scheduler**.

## Execution Environment
- **Java**: 11
- **Spark**: 3.3.4
- **Iceberg**: 1.4.3
- **Dataset**: TPC-H SF1 (pre-ingested and validated)
- **Catalog Name**: `local`
- **Catalog Type**: Hadoop filesystem catalog
- **Warehouse Directory**: `file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse`
- **Thrift Server Endpoint**: `jdbc:hive2://127.0.0.1:10000/default`
- **Thrift Server Port**: `10000`

---

## Created Configuration Files
1.  **`config/connections_config.yaml`**: Connects via Hive JDBC driver to the running Spark Thrift Server.
2.  **`config/telemetry_config.yaml`**: Records execution performance metrics into a local DuckDB file database.
3.  **`config/experiment_config.yaml`**: Sets parameter values `catalog=local` and `database=tpch`.
4.  **`config/library.yaml`**: Registers the custom smoke query task.
5.  **`config/workload_queries_only.yaml`**: Defines a workload with a single execution phase, bypassing setup and build scripts.
6.  **`sql/smoke_query.sql`**: Contains the query executed:
    ```sql
    SELECT COUNT(*) FROM ${catalog}.${database}.lineitem;
    ```

---

## Execution Command
To run this smoke test, launch from the `lst-bench` submodule root directory:
```bash
./launcher.sh \
  -c ../scripts/lst-bench-config/config/connections_config.yaml \
  -e ../scripts/lst-bench-config/config/experiment_config.yaml \
  -t ../scripts/lst-bench-config/config/telemetry_config.yaml \
  -l ../scripts/lst-bench-config/config/library.yaml \
  -w ../scripts/lst-bench-config/config/workload_queries_only.yaml
```

---

## Output & Verification
- **Expected result**: Query returns exactly `6001215` (lineitem count).
- **Telemetry Database**: `scripts/lst-bench-config/telemetry_smoke.db`
- **Verification Statement**: No stock files in the `lst-bench/` submodule were created, modified, or deleted during this test. The entire workspace remains clean.
