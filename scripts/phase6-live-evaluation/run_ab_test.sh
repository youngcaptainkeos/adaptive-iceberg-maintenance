#!/usr/bin/env bash

# Configure Environment
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
cd "$ROOT_DIR" || exit 1

source setup_env.sh

echo "=========================================================="
echo "   Phase 6: Live Online A/B Evaluation (Google Borg Trace)"
echo "   Target Table: local.tpch_sf100.lineitem (SF100 - 600M Rows)"
echo "=========================================================="
echo ""

POLICY=${1:-"TemporalConformalPolicy"}

echo "Starting Live Agent Daemon with Policy: $POLICY..."
python3 scripts/phase6-live-evaluation/run_live_agent.py --policy "$POLICY" --table "local.tpch_sf100.lineitem" --interval 60
