# Phase 3A: Post-Run Validation & Data Integrity Report

## 1. Executive Summary & Completion Status
- **Mode FAIR**: COMPLETE (22/22 repetitions, 264/264 query runs, 22/22 compaction runs)
- **Mode FIFO**: COMPLETE (22/22 repetitions, 264/264 query runs, 22/22 compaction runs)

## 2. Table State & Physical Layout Verification
- **Control Table (`local.tpch.lineitem`)**: 6,001,215 records across 16 files (Unchanged control state).
- **Treatment Table (`local.experiment.interference_treatment`)**: Verified 200-partition fragmented state (avg size ~842 KB) prior to each compaction run.

## 3. Temporal Overlap Classification
- **No Overlap (ratio = 0.0)**: 0 runs
- **Partial Overlap (0.0 < ratio < 0.95)**: 0 runs
- **Full Overlap (ratio >= 0.95)**: 264 runs

Detailed per-run overlap metrics written to: `results/overlap_validation.csv`
