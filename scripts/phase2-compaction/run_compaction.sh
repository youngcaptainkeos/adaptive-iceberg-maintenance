#!/usr/bin/env bash
# Exit immediately if any step fails
set -euo pipefail

# 1. Locate directories relative to this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "=== Iceberg Table Compaction & Storage Recovery (Phase 2D) ==="
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

# 3. Create results and logs directories
mkdir -p "$SCRIPT_DIR/results"
mkdir -p "$SCRIPT_DIR/logs"

# 4. Step 1: Pre-Compaction Inspection & Integrity Baseline
echo "Step 1: Running pre-compaction inspection on local.experiment.lineitem_fragmented..."
python3 "$SCRIPT_DIR/inspect_pre_compaction.py"

# Verify pre-compaction metrics were created
if [ ! -f "$SCRIPT_DIR/results/pre_compaction_metrics.json" ]; then
    echo "Error: Pre-compaction metrics were not generated."
    exit 1
fi

# 5. Step 2: Perform Iceberg Compaction (rewrite_data_files)
echo "Step 2: Performing Iceberg data-file compaction..."
python3 "$SCRIPT_DIR/compact_table.py"

# Verify compaction log exists
if [ ! -f "$SCRIPT_DIR/logs/compaction_execution.log" ]; then
    echo "Error: Compaction execution log was not found."
    exit 1
fi

# 6. Step 3: Post-Compaction Inspection
echo "Step 3: Running post-compaction inspection..."
python3 "$SCRIPT_DIR/inspect_post_compaction.py"

# Verify post-compaction metrics were created
if [ ! -f "$SCRIPT_DIR/results/post_compaction_metrics.json" ]; then
    echo "Error: Post-compaction metrics were not generated."
    exit 1
fi

# 7. Step 4: Data Integrity and Control Table Verification
echo "Step 4: Running data integrity validation and control table check..."
python3 "$SCRIPT_DIR/validate_compaction.py"

# 8. Step 5: Check Submodule Status
echo "Step 5: Verifying LST-Bench submodule status remains clean..."
cd "$PROJECT_ROOT"
git -C lst-bench status

echo "=== Phase 2D Compaction & Recovery Successful! ==="
