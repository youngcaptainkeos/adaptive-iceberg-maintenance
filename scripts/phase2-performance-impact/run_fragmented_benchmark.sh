#!/usr/bin/env bash
# Exit immediately if any step fails
set -euo pipefail

# 1. Locate directories relative to this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "=== Fragmented Table Performance Benchmark (Phase 2C) ==="
echo "Project Root: $PROJECT_ROOT"

# 2. Verify Environment Variables
echo "Checking environment variables..."
if [ -z "${JAVA_HOME:-}" ]; then
    echo "Error: JAVA_HOME is not set. Please run 'source ./setup_env.sh' first."
    exit 1
fi
if [ -z "${SPARK_HOME:-}" ]; then
    echo "Error: SPARK_HOME is not set. Please run 'source ./setup_env.sh' first."
    exit 1
fi

echo "  JAVA_HOME=$JAVA_HOME"
echo "  SPARK_HOME=$SPARK_HOME"

# 3. Verify Spark Thrift Server is reachable on port 10000
echo "Verifying Spark Thrift Server connectivity on 127.0.0.1:10000..."
python3 -c "import socket; socket.create_connection(('127.0.0.1', 10000), timeout=3)" >/dev/null 2>&1 || {
    echo "Error: Spark Thrift Server is NOT reachable on 127.0.0.1:10000"
    echo "Please start the Thrift Server daemon first."
    exit 1
}
echo "  [OK] Spark Thrift Server is reachable."

# 4. Verify Fragmented Table exists and has correct row counts
echo "Verifying tables and row counts before benchmark..."
python3 -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName('IcebergVerificationBeforeBenchmark') \
    .config('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions') \
    .config('spark.sql.catalog.local', 'org.apache.iceberg.spark.SparkCatalog') \
    .config('spark.sql.catalog.local.type', 'hadoop') \
    .config('spark.sql.catalog.local.warehouse', 'file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse') \
    .getOrCreate()
c_control = spark.table('local.tpch.lineitem').count()
c_frag = spark.table('local.experiment.lineitem_fragmented').count()
print(f'Verification counts: Control rows={c_control}, Fragmented rows={c_frag}')
assert c_control == 6001215, f'Control row count {c_control} != 6001215'
assert c_frag == 6001215, f'Fragmented row count {c_frag} != 6001215'
spark.stop()
"
echo "  [OK] Table verifications passed."

# 5. Clear previous telemetry database file if present
DB_FILE="$PROJECT_ROOT/scripts/phase2-performance-impact/telemetry/telemetry_fragmented.db"
if [ -f "$DB_FILE" ]; then
    echo "Cleaning previous telemetry database at $DB_FILE..."
    rm -f "$DB_FILE"
fi

# 6. Execute LST-Bench Workload
echo "Starting LST-Bench fragmented performance workload (18 executions)..."
cd "$PROJECT_ROOT/lst-bench"

./launcher.sh \
  -c ../scripts/phase2-performance-impact/config/connections_config.yaml \
  -e ../scripts/phase2-performance-impact/config/experiment_config.yaml \
  -t ../scripts/phase2-performance-impact/config/telemetry_config.yaml \
  -l ../scripts/phase2-performance-impact/config/library.yaml \
  -w ../scripts/phase2-performance-impact/config/workload_fragmented.yaml

echo "  [OK] LST-Bench workload run finished successfully."

# 7. Execute analyze_results.py
echo "Running results analysis and baseline comparison..."
cd "$PROJECT_ROOT"
python3 scripts/phase2-performance-impact/analyze_results.py

# 8. Post-benchmark integrity check
echo "Performing final row count assertions for control and fragmented tables..."
python3 -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName('IcebergVerificationAfterBenchmark') \
    .config('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions') \
    .config('spark.sql.catalog.local', 'org.apache.iceberg.spark.SparkCatalog') \
    .config('spark.sql.catalog.local.type', 'hadoop') \
    .config('spark.sql.catalog.local.warehouse', 'file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse') \
    .getOrCreate()

c1 = spark.table('local.tpch.lineitem').count()
c2 = spark.table('local.experiment.lineitem_fragmented').count()
print(f'Verification Results: Control={c1}, Fragmented={c2}')
assert c1 == 6001215, f'Assertion failed: Control row count {c1} != 6001215'
assert c2 == 6001215, f'Assertion failed: Fragmented row count {c2} != 6001215'
spark.stop()
"

echo "=== Phase 2C Benchmark Completed Successfully ==="
echo "Telemetry location: scripts/phase2-performance-impact/telemetry/telemetry_fragmented.db"
echo "Results location: scripts/phase2-performance-impact/results/"
