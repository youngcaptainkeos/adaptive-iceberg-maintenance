#!/bin/bash
# Master Execution Script for Phase 6
# This script runs the entire uncompromised pipeline from start to finish.

set -e # Exit immediately if a command exits with a non-zero status.

export REPO_DIR="/media/ccbd/ab97a8fa-c92f-4b3f-b770-711e278ce987/CAPSTONE_PRAFULATHA_SHASHANKS_DONT_DELETE/implementation"
cd $REPO_DIR

echo "====================================================="
echo "   PHASE 6 MASTER PIPELINE EXECUTION (NO HACKS)"
echo "====================================================="

echo ""
echo "--- STEP 1: PREPARE WORKSPACE ---"
mkdir -p results
mkdir -p scripts/phase6-live-evaluation/models

echo ""
echo "--- STEP 2: PHASE 6A DATA COLLECTION (4 HOURS) ---"
echo "Collecting real temporal telemetry and latency targets..."
python3 scripts/phase6-live-evaluation/collect_training_data.py \
    --duration-hours 4.0 \
    --output results/phase6a_master_training_data.csv

echo ""
echo "--- STEP 3: PHASE 6B TRAIN MODELS ---"
echo "Training Cost-Benefit models on the pristine 4-hour dataset..."
python3 scripts/phase6-live-evaluation/train_cost_benefit_models.py \
    --input results/phase6a_master_training_data.csv \
    --output-dir scripts/phase6-live-evaluation/models

echo ""
echo "--- STEP 4: PHASE 6C A/B EVALUATION ---"
echo "Starting 8-hour Baseline evaluation..."
python3 scripts/phase6-live-evaluation/reset_table_state.py
python3 scripts/phase6-live-evaluation/run_cost_benefit_agent.py \
    --policy SOTAThresholdPolicy \
    --duration-hours 8.0 \
    --output results/phase6c_run_a_baseline.csv

echo "Starting 8-hour Cost-Benefit Optimizer evaluation..."
python3 scripts/phase6-live-evaluation/reset_table_state.py
python3 scripts/phase6-live-evaluation/run_cost_benefit_agent.py \
    --policy CostBenefitPolicy \
    --duration-hours 8.0 \
    --output results/phase6c_run_b_costbenefit.csv

echo ""
echo "====================================================="
echo "   PIPELINE COMPLETE. RESULTS SAVED TO ./results/"
echo "====================================================="
