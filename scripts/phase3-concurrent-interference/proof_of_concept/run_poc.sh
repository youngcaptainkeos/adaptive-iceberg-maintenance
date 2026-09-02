#!/bin/bash

WORKSPACE_DIR="/home/shashank/Link to PDocuments/Capstone/implementation"
cd "$WORKSPACE_DIR"

echo "=== Milestone 1: Starting Thrift Server in FAIR mode ==="

# Source setup
source setup_env.sh
export SPARK_LOG_DIR="/tmp"
export SPARK_LOCAL_IP="127.0.0.1"
export SPARK_LOCAL_HOSTNAME="localhost"

# Create event logs dir if not exists and clean it
rm -rf /tmp/spark-events
mkdir -p /tmp/spark-events
ABS_EVENTS_DIR="file:///tmp/spark-events"

cleanup() {
    echo "Stopping Spark Thrift Server..."
    "$WORKSPACE_DIR/software/spark-3.3.4/sbin/stop-thriftserver.sh" || true
}
trap cleanup EXIT

# Start server
./software/spark-3.3.4/sbin/start-thriftserver.sh \
  --driver-memory 4g \
  --conf spark.driver.host=127.0.0.1 \
  --conf spark.driver.bindAddress=127.0.0.1 \
  --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
  --conf spark.sql.catalog.local=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.local.type=hadoop \
  --conf "spark.sql.catalog.local.warehouse=file://${WORKSPACE_DIR}/warehouse" \
  --conf spark.eventLog.enabled=true \
  --conf "spark.eventLog.dir=${ABS_EVENTS_DIR}" \
  --conf spark.scheduler.mode=FAIR \
  --conf spark.scheduler.allocation.file=scripts/phase3-concurrent-interference/config/fairscheduler.xml \
  --hiveconf hive.server2.thrift.port=10000 \
  --hiveconf hive.server2.thrift.bind.host=127.0.0.1

echo "Waiting for Spark Thrift Server to bind to port 10000..."
for i in {1..30}; do
    if python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('127.0.0.1', 10000))" 2>/dev/null; then
        echo "Spark Thrift Server is online and responding."
        break
    fi
    sleep 2
done

if ! python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('127.0.0.1', 10000))" 2>/dev/null; then
    echo "Error: Spark Thrift Server failed to bind to port 10000."
    echo "=== Writing Spark Thrift Server Logs to poc_thrift_error.log ==="
    cat /tmp/spark-*.out > poc_thrift_error.log
    exit 1
fi

echo "=== Running verify_scheduler_pools.py (output redirected to poc_output.log) ==="
python3 scripts/phase3-concurrent-interference/proof_of_concept/verify_scheduler_pools.py > scripts/phase3-concurrent-interference/proof_of_concept/poc_output.log 2>&1

echo "=== Milestone 1 Completed ==="
