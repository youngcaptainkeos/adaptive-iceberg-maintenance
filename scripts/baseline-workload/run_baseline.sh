#!/usr/bin/env bash
# Exit immediately if any step fails
set -eo pipefail

# 1. Locate directories relative to this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "=== Baseline Workload Characterization (Phase 1B) ==="
echo "Project Root: $PROJECT_ROOT"

# 2. Verify Environment Variables
echo "Checking environment variables..."
if [ -z "$JAVA_HOME" ]; then
    echo "Error: JAVA_HOME is not set. Please run 'source ./setup_env.sh' first."
    exit 1
fi
if [ -z "$SPARK_HOME" ]; then
    echo "Error: SPARK_HOME is not set. Please run 'source ./setup_env.sh' first."
    exit 1
fi

echo "  JAVA_HOME=$JAVA_HOME"
echo "  SPARK_HOME=$SPARK_HOME"

# 3. Verify Spark Thrift Server is reachable on port 10000
echo "Verifying Spark Thrift Server connectivity on 127.0.0.1:10000..."
python3 -c "import socket; socket.create_connection(('127.0.0.1', 10000), timeout=3)" >/dev/null 2>&1 || {
    echo "Error: Spark Thrift Server is NOT reachable on 127.0.0.1:10000"
    echo "Please start the Thrift Server daemon first. For example, execute:"
    echo "  export SPARK_LOG_DIR=/tmp/spark-logs"
    echo "  ./software/spark-3.3.4/sbin/start-thriftserver.sh \\"
    echo "    --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \\"
    echo "    --conf spark.sql.catalog.local=org.apache.iceberg.spark.SparkCatalog \\"
    echo "    --conf spark.sql.catalog.local.type=hadoop \\"
    echo "    --conf spark.sql.catalog.local.warehouse=file://\$PROJECT_ROOT/warehouse \\"
    echo "    --hiveconf hive.server2.thrift.port=10000 \\"
    echo "    --hiveconf hive.server2.thrift.bind.host=127.0.0.1"
    exit 1
}
echo "  [OK] Spark Thrift Server is reachable."

# 4. Clean previous baseline run telemetry database if it exists
DB_FILE="$PROJECT_ROOT/scripts/baseline-workload/telemetry/telemetry_baseline_comprehensive.db"
if [ -f "$DB_FILE" ]; then
    echo "Cleaning previous telemetry database at $DB_FILE..."
    rm -f "$DB_FILE"
fi

# 5. Execute LST-Bench Workload
echo "Starting LST-Bench baseline comprehensive workload (18 executions)..."
cd "$PROJECT_ROOT/lst-bench"

./launcher.sh \
  -c ../scripts/baseline-workload/config/connections_config.yaml \
  -e ../scripts/baseline-workload/config/experiment_config.yaml \
  -t ../scripts/baseline-workload/config/telemetry_config.yaml \
  -l ../scripts/baseline-workload/config/library.yaml \
  -w ../scripts/baseline-workload/config/workload_baseline.yaml

echo "  [OK] LST-Bench workload run finished successfully."

# 6. Extract Telemetry and Generate Statistics
echo "Running telemetry results extraction and summary statistics..."
cd "$PROJECT_ROOT"
python3 scripts/baseline-workload/analysis/extract_results.py

# 7. Validate Data Integrity
echo "Validating Iceberg data integrity..."
python3 scripts/baseline-workload/validate_integrity.py

echo "=== Phase 1B Baseline Pilot Done! ==="
