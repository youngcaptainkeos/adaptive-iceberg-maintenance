#!/usr/bin/env bash
# Exit immediately if any step fails
set -euo pipefail

# 1. Locate directories relative to this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "=== Phase 2F: Experimental Methodology Validation & Benchmark Noise Characterization ==="
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

# 4. Clear previous telemetry database file if present
mkdir -p "$PROJECT_ROOT/scripts/phase2-methodology-validation/telemetry"
DB_FILE="$PROJECT_ROOT/scripts/phase2-methodology-validation/telemetry/telemetry_noise_floor.db"
if [ -f "$DB_FILE" ]; then
    echo "Cleaning previous telemetry database at $DB_FILE..."
    rm -f "$DB_FILE"
fi

# 5. Collect metadata and assert starting table state
echo "Collecting starting metadata and verifying catalog health..."
python3 "$PROJECT_ROOT/scripts/phase2-methodology-validation/collect_metadata.py"

# 6. Execute LST-Bench Workload (22 repetitions total: 2 warmup, 20 measured)
echo "Starting LST-Bench noise characterization workload (132 statement executions)..."
cd "$PROJECT_ROOT/lst-bench"

./launcher.sh \
  -c ../scripts/phase2-methodology-validation/config/connections_config.yaml \
  -e ../scripts/phase2-methodology-validation/config/experiment_config.yaml \
  -t ../scripts/phase2-methodology-validation/config/telemetry_config.yaml \
  -l ../scripts/phase2-methodology-validation/config/library.yaml \
  -w ../scripts/phase2-methodology-validation/config/workload_noise_floor.yaml

echo "  [OK] LST-Bench workload run finished successfully."

# 7. Execute analyze_results.py
echo "Running statistical variance and noise-floor analysis..."
cd "$PROJECT_ROOT"
python3 scripts/phase2-methodology-validation/analyze_results.py

# 8. Post-benchmark integrity check
echo "Running post-benchmark table data and metadata integrity assertions..."
python3 scripts/phase2-methodology-validation/verify_post_state.py

echo "=== Phase 2F Noise Characterization Completed Successfully ==="
echo "Telemetry location: scripts/phase2-methodology-validation/telemetry/telemetry_noise_floor.db"
echo "Results location: scripts/phase2-methodology-validation/results/"
echo "Validation Report: scripts/phase2-methodology-validation/analysis/methodology_validation_report.md"
