#!/usr/bin/env bash
# Exit immediately if any step fails
set -eo pipefail

# Locate directories relative to this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "=== Iceberg Table Health Inspection (Phase 2A) ==="
echo "Project Root: $PROJECT_ROOT"

# Verify Environment Variables
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

# Run inspect_table_state.py
echo "Running inspect_table_state.py..."
python3 "$PROJECT_ROOT/scripts/phase2-table-health/inspect_table_state.py"

echo "  [OK] Table health inspection finished successfully."
