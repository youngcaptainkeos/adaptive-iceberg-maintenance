#!/usr/bin/env bash
# Exit immediately if any step fails
set -eo pipefail

# Locate directories relative to this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "=== Controlled Iceberg Table Fragmentation (Phase 2B) ==="
echo "Project Root: $PROJECT_ROOT"

# 1. Verify Environment Variables
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

# 2. Run create_fragmented_table.py
echo "Running create_fragmented_table.py..."
python3 "$PROJECT_ROOT/scripts/phase2-fragmentation/create_fragmented_table.py"

# 3. Run inspect_fragmented_table.py
echo "Running inspect_fragmented_table.py..."
python3 "$PROJECT_ROOT/scripts/phase2-fragmentation/inspect_fragmented_table.py"

# 4. Final Row Count Validations
echo "Performing final row count assertions for control and fragmented tables..."
python3 -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName('IcebergFragmentationFinalAssertion') \
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

echo "  [OK] Iceberg table fragmentation completed and verified successfully."
