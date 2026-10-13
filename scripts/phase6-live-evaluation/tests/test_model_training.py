#!/usr/bin/env python3
"""
Unit Test Suite for Phase 6.1C Query-Aware Conformal Training
Methodology v2.1

Tests:
- Synthetic training data generation with bimodal query latencies.
- Dual-model training (Model A and Model B) with one-hot query_id features.
- Verification of 13 features in model_metadata.json (q_0..q_3 included).
- Positive conformal bounds q_hat > 0.0.
- Per-query MAE tracking in metadata.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import numpy as np
import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE6_DIR = os.path.dirname(CURRENT_DIR)
REPO_ROOT = os.path.dirname(os.path.dirname(PHASE6_DIR))
for path in [PHASE6_DIR, REPO_ROOT]:
    if path not in sys.path:
        sys.path.insert(0, path)

import train_cost_benefit_models as tcbm


class TestModelTrainingPhase61C(unittest.TestCase):
    """Test suite for Phase 6.1C model training refactoring."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_models_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def generate_synthetic_data(self, n_rows=100) -> pd.DataFrame:
        """Generates realistic synthetic telemetry with bimodal query latencies."""
        np.random.seed(42)
        records = []
        for i in range(n_rows):
            elapsed_s = float(i * 10)
            cpu_1m = float(np.random.uniform(20.0, 80.0))
            cpu_5m = float(cpu_1m + np.random.uniform(-5.0, 5.0))
            cpu_trend = float(cpu_1m - cpu_5m)
            mem_pct = float(np.random.uniform(30.0, 60.0))
            frag_files = int(np.random.uniform(33, 100))
            small_files = int(np.random.uniform(2, 40))
            table_mb = float(15000.0 + i * 2.0)
            avg_kb = float((table_mb * 1024.0) / max(frag_files, 1))
            intensity = float(np.random.uniform(0.1, 1.0))
            
            # Compaction active for 30% of rows
            compaction_active = (i % 3 == 0)

            # Rotate query_id in {0, 1, 2, 3}
            qid = i % 4

            # Bimodal latency: Q1 ~49,000ms, Q0, Q2, Q3 ~3,500ms
            if qid == 1:
                base_lat = float(np.random.normal(49000.0, 1500.0))
            else:
                base_lat = float(np.random.normal(3500.0, 200.0))

            # Add compaction penalty if compaction active
            if compaction_active:
                lat_compaction = base_lat + float(np.random.uniform(2000.0, 5000.0))
                lat_normal = np.nan
            else:
                lat_normal = base_lat
                lat_compaction = np.nan

            records.append({
                "timestamp": f"2026-10-13 12:00:{i:02d}",
                "elapsed_s": elapsed_s,
                "cpu_util_pct": cpu_1m,
                "cpu_util_avg_1min": cpu_1m,
                "cpu_util_avg_5min": cpu_5m,
                "cpu_trend": cpu_trend,
                "mem_used_pct": mem_pct,
                "disk_io_read_bytes": 1000000,
                "disk_io_write_bytes": 500000,
                "frag_file_count": frag_files,
                "candidate_small_files": small_files,
                "table_size_mb": table_mb,
                "avg_file_size_kb": avg_kb,
                "intensity": intensity,
                "compaction_active": compaction_active,
                "query_id": qid,
                "query_latency_ms": lat_normal,
                "query_latency_during_compaction_ms": lat_compaction
            })

        return pd.DataFrame(records)

    def test_train_and_save_models(self):
        """Verifies full training, conformal calibration, and metadata generation."""
        df_synthetic = self.generate_synthetic_data(n_rows=120)

        model_a, model_b, metadata = tcbm.train_and_save_models(
            df_synthetic, self.test_dir, alpha=0.10, is_test_run=True
        )

        # 1. Output directory contains artifacts
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "model_a_compaction.joblib")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "model_b_baseline.joblib")))
        metadata_file = os.path.join(self.test_dir, "model_metadata.json")
        self.assertTrue(os.path.exists(metadata_file))

        # 2. Verify metadata structure
        with open(metadata_file, "r") as f:
            meta = json.load(f)

        features = meta["features"]
        self.assertEqual(len(features), 13)
        expected_features = [
            'cpu_util_avg_1min', 'cpu_util_avg_5min', 'cpu_trend',
            'mem_used_pct', 'frag_file_count', 'candidate_small_files',
            'table_size_mb', 'avg_file_size_kb', 'intensity',
            'q_0', 'q_1', 'q_2', 'q_3'
        ]
        self.assertEqual(features, expected_features)

        # 3. Conformal bounds positive
        self.assertGreater(meta["model_a"]["q_hat"], 0.0)
        self.assertGreater(meta["model_b"]["q_hat"], 0.0)

        # 4. Check per-query MAE
        self.assertIn("per_query_mae", meta["model_a"])
        self.assertIn("per_query_mae", meta["model_b"])
        self.assertTrue(len(meta["model_b"]["per_query_mae"]) > 0)


if __name__ == "__main__":
    unittest.main()
