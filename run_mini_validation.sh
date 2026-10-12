#!/bin/bash
# MINI VALIDATION SCRIPT
# This script runs a hyper-compressed 45-minute version of the pipeline to prove the plumbing works.

set -e # Exit immediately if a command exits with a non-zero status.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "====================================================="
echo "   MINI VALIDATION: 45-MINUTE PIPELINE TEST"
echo "====================================================="

# Ensure Spark Thrift Server is running
echo "Checking Spark Thrift Server status on port 10000..."
if ! python3 -c 'import socket; s=socket.socket(); s.settimeout(1); s.connect(("127.0.0.1", 10000)); s.close()' 2>/dev/null; then
    echo "Spark Thrift Server is not running. Starting Spark Thrift Server..."
    export SPARK_LOCAL_IP=127.0.0.1
    "$REPO_DIR/software/spark-3.3.4/sbin/start-thriftserver.sh" \
        --master "local[16]" \
        --driver-memory 16g \
        --conf spark.sql.catalog.local=org.apache.iceberg.spark.SparkCatalog \
        --conf spark.sql.catalog.local.type=hadoop \
        --conf "spark.sql.catalog.local.warehouse=$REPO_DIR/warehouse" \
        --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
        --conf spark.eventLog.enabled=false

    echo "Waiting for Spark Thrift Server to bind to port 10000..."
    for i in {1..30}; do
        if python3 -c 'import socket; s=socket.socket(); s.settimeout(1); s.connect(("127.0.0.1", 10000)); s.close()' 2>/dev/null; then
            echo "Spark Thrift Server is successfully running on port 10000."
            break
        fi
        sleep 2
    done
else
    echo "Spark Thrift Server is already running on port 10000."
fi

# Initialize isolated run directory
eval $(python3 scripts/run_manager.py init --type "mini_validation" --desc "45-Minute Mini Validation Dry Run" --bash)
echo "-----------------------------------------------------"
echo "  Executing Run:       $RUN_ID"
echo "  Artifact Directory:  $RUN_DIR"
echo "-----------------------------------------------------"

echo ""
echo "--- STEP 1: MINI DATA COLLECTION (15 MINS) ---"
# 0.25 hours = 15 minutes
python3 scripts/phase6-live-evaluation/collect_training_data.py \
    --duration-hours 0.25 \
    --output "$TRAINING_DATA"

echo ""
echo "--- STEP 2: TRAIN MINI MODELS ---"
python3 scripts/phase6-live-evaluation/train_cost_benefit_models.py \
    --input "$TRAINING_DATA" \
    --output-dir "$MODELS_DIR"

echo ""
echo "--- STEP 3: MINI A/B EVALUATION ---"
echo "Starting 15-min Baseline evaluation..."
python3 scripts/phase6-live-evaluation/reset_table_state.py
python3 scripts/phase6-live-evaluation/run_cost_benefit_agent.py \
    --policy SOTAThresholdPolicy \
    --model-dir "$MODELS_DIR" \
    --duration-hours 0.25 \
    --output "$RUN_A_CSV"

echo "Starting 15-min Cost-Benefit Optimizer evaluation..."
python3 scripts/phase6-live-evaluation/reset_table_state.py
python3 scripts/phase6-live-evaluation/run_cost_benefit_agent.py \
    --policy CostBenefitPolicy \
    --model-dir "$MODELS_DIR" \
    --duration-hours 0.25 \
    --output "$RUN_B_CSV"

# Also update legacy/root pointers for backward compatibility
cp "$TRAINING_DATA" results/phase6a_mini_training_data.csv 2>/dev/null || true
cp "$RUN_A_CSV" results/phase6c_mini_run_a_baseline.csv 2>/dev/null || true
cp "$RUN_B_CSV" results/phase6c_mini_run_b_costbenefit.csv 2>/dev/null || true
cp "$MODELS_DIR"/* scripts/phase6-live-evaluation/models/ 2>/dev/null || true

python3 scripts/run_manager.py complete "$RUN_ID" --status "completed"

echo ""
echo "====================================================="
echo "   MINI VALIDATION COMPLETE! RUN SAVED TO $RUN_DIR"
echo "====================================================="
