#!/bin/bash
set -e

# Define root workspace path
WORKSPACE_DIR="/home/shashank/Link to PDocuments/Capstone/implementation"
cd "$WORKSPACE_DIR"

echo "=== Phase 2G: Validated Three-State Physical Layout Performance Experiment ==="

# 1. Verify environment and source setup
echo "Step 1: Sourcing environment setup..."
if [ -f "setup_env.sh" ]; then
    source setup_env.sh
else
    echo "Error: setup_env.sh not found!"
    exit 1
fi

# Initialize directories first
mkdir -p scripts/phase2-validated-layout-comparison/logs
mkdir -p scripts/phase2-validated-layout-comparison/telemetry
mkdir -p scripts/phase2-validated-layout-comparison/results

# Define execution env variables
export SPARK_LOG_DIR="/tmp"
export SPARK_LOCAL_IP="127.0.0.1"
export SPARK_LOCAL_HOSTNAME="localhost"
export PYTHONPATH="$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.5-src.zip:$PYTHONPATH"

# Setup lifecycle trap
cleanup() {
    echo "Stopping Spark Thrift Server..."
    "$WORKSPACE_DIR/software/spark-3.3.4/sbin/stop-thriftserver.sh" || true
}
trap cleanup EXIT

# Start Spark Thrift Server
echo "Starting Spark Thrift Server..."
./software/spark-3.3.4/sbin/start-thriftserver.sh \
  --driver-memory 4g \
  --conf spark.driver.host=127.0.0.1 \
  --conf spark.driver.bindAddress=127.0.0.1 \
  --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
  --conf spark.sql.catalog.local=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.local.type=hadoop \
  --conf "spark.sql.catalog.local.warehouse=file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse" \
  --hiveconf hive.server2.thrift.port=10000 \
  --hiveconf hive.server2.thrift.bind.host=127.0.0.1

echo "Waiting for Spark Thrift Server to bind to port 10000..."
for i in {1..30}; do
    if nc -z 127.0.0.1 10000; then
        echo "Spark Thrift Server is online and responding."
        break
    fi
    sleep 2
done

if ! nc -z 127.0.0.1 10000; then
    echo "Error: Spark Thrift Server failed to bind to port 10000."
    LOG_FILE=$(ls "$SPARK_LOG_DIR"/spark-*-org.apache.spark.sql.hive.thriftserver.HiveThriftServer2-1-*.out 2>/dev/null | head -n 1)
    if [ -f "$LOG_FILE" ]; then
        echo "=== Thrift Server logs ==="
        cat "$LOG_FILE" | tail -n 100
    fi
    exit 1
fi


mkdir -p scripts/phase2-validated-layout-comparison/analysis/plots

# Clean old telemetry database if exists
rm -f scripts/phase2-validated-layout-comparison/telemetry/telemetry_validated.db

# 2. Record environment metadata
echo "Step 2: Collecting system environmental metadata..."
python3 scripts/phase2-validated-layout-comparison/preparation/collect_metadata.py

# 3. Create and Validate fragmented State B
echo "Step 3: Creating and validating fragmented State B..."
python3 scripts/phase2-validated-layout-comparison/preparation/create_fragmented_state.py

# 4. Create and Validate compacted State C
echo "Step 4: Creating and validating compacted State C (64 MB Target)..."
python3 scripts/phase2-validated-layout-comparison/preparation/create_compacted_state.py

# 5. Record pre-benchmark physical layout metrics
echo "Step 5: Recording pre-benchmark physical layout metrics..."
python3 scripts/phase2-validated-layout-comparison/preparation/validate_states.py --phase pre

# 6. Generate SQL templates and workload config files dynamically
echo "Step 6: Generating SQL templates, library, and counterbalanced workload..."
python3 scripts/phase2-validated-layout-comparison/preparation/generate_sql_and_configs.py

# 7. Execute benchmark repetitions using LST-Bench
echo "Step 7: Launching LST-Bench for 66 counterbalanced phases (22 repetitions)..."
cd lst-bench
LST_BENCH_CLASSPATH="core/target/*:core/target/lib/*:core/target/classes/*"
java -cp "${LST_BENCH_CLASSPATH}" com.microsoft.lst_bench.Driver \
  -c ../scripts/phase2-validated-layout-comparison/config/connections_config.yaml \
  -e ../scripts/phase2-validated-layout-comparison/config/experiment_config.yaml \
  -t ../scripts/phase2-validated-layout-comparison/config/telemetry_config.yaml \
  -l ../scripts/phase2-validated-layout-comparison/config/library.yaml \
  -w ../scripts/phase2-validated-layout-comparison/config/workload_validated.yaml
cd ..

# 8. Perform descriptive statistics, confidence interval calculations, and plots
echo "Step 8: Executing results extraction and statistical analysis..."
python3 scripts/phase2-validated-layout-comparison/analysis/analyze_results.py

# 9. Reinspect all three tables post-run and assert read-only invariants
echo "Step 9: Performing post-run layout metrics checks and read-only assertions..."
python3 scripts/phase2-validated-layout-comparison/preparation/validate_states.py --phase post

# 10. Verify lst-bench submodule remains unmodified
echo "Step 10: Verifying LST-Bench submodule isolation..."
SUBMODULE_STATUS=$(git -C lst-bench status --porcelain)
if [ -n "$SUBMODULE_STATUS" ]; then
    echo "Error: LST-Bench submodule has been mutated!"
    echo "$SUBMODULE_STATUS"
    exit 1
fi
echo "LST-Bench submodule is completely clean."

echo "=== Phase 2G Experiment Completed Successfully ==="
echo "Raw Results: scripts/phase2-validated-layout-comparison/results/"
echo "Plots: scripts/phase2-validated-layout-comparison/analysis/plots/"
echo "Scientific Report: scripts/phase2-validated-layout-comparison/analysis/validated_layout_report.md"
exit 0
