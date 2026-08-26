#!/usr/bin/env bash
# Run the end-to-end smoke test
set -e

# Get implementation directory
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)
cd "$SCRIPT_DIR"

# Clean up any prior telemetry and warehouse runs to ensure clean state
rm -f smoke_test/telemetry.db
rm -rf smoke_test/warehouse

# Source environment setup
source ./setup_env.sh

echo "Running LST-Bench Smoke Test..."
java -cp "lst-bench/core/target/*:lst-bench/core/target/lib/*:lst-bench/core/target/classes/*:$SPARK_HOME/jars/*" \
  com.microsoft.lst_bench.Driver \
  -c smoke_test/configs/connections.yaml \
  -e smoke_test/configs/experiment.yaml \
  -t smoke_test/configs/telemetry.yaml \
  -l smoke_test/configs/library.yaml \
  -w smoke_test/configs/workload.yaml

echo "Smoke test complete! Querying telemetry to confirm success..."
python3 -c "
import duckdb
con = duckdb.connect('smoke_test/telemetry.db')
con.sql('select event_id, event_type, event_status from experiment_telemetry order by event_start_time').show()
"
