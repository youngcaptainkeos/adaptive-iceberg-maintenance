#!/usr/bin/env python3
"""
Unit Test Suite for Phase 6.1D Agent Horizon & Action Space
Methodology v2.1

Tests:
- CostBenefitPolicy principled action space: candidate_small_files <= 0 defers immediately.
- CostBenefitPolicy multi-query evaluation across Q0..Q3 with mock models.
- Literature baselines (AutoCompPolicy, PeriodicCronPolicy, TunedThresholdPolicy) integration.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE6_DIR = os.path.dirname(CURRENT_DIR)
REPO_ROOT = os.path.dirname(os.path.dirname(PHASE6_DIR))
for path in [PHASE6_DIR, REPO_ROOT]:
    if path not in sys.path:
        sys.path.insert(0, path)

from run_cost_benefit_agent import CostBenefitPolicy
from policies.literature_baselines import AutoCompPolicy, PeriodicCronPolicy, TunedThresholdPolicy


class TestAgentPoliciesPhase61D(unittest.TestCase):
    """Test suite for Phase 6.1D agent policy integration and action space."""

    def setUp(self):
        self.features = [
            'cpu_util_avg_1min', 'cpu_util_avg_5min', 'cpu_trend',
            'mem_used_pct', 'frag_file_count', 'candidate_small_files',
            'table_size_mb', 'avg_file_size_kb', 'intensity',
            'q_0', 'q_1', 'q_2', 'q_3'
        ]
        self.metadata = {
            "features": self.features,
            "model_a": {"q_hat": 500.0, "test_mae": 200.0, "test_coverage": 92.0},
            "model_b": {"q_hat": 400.0, "test_mae": 150.0, "test_coverage": 91.0}
        }

        # Mock Model A and Model B
        self.mock_model_a = MagicMock()
        self.mock_model_b = MagicMock()

    def test_cost_benefit_defers_when_no_small_files(self):
        """Principled action space: if candidate_small_files <= 0, must return DEFER immediately."""
        policy = CostBenefitPolicy(
            model_a=self.mock_model_a,
            model_b=self.mock_model_b,
            metadata=self.metadata
        )

        # Telemetry with candidate_small_files = 0
        telemetry = {
            "cpu_util_avg_1min": 30.0,
            "cpu_util_avg_5min": 30.0,
            "cpu_trend": 0.0,
            "mem_used_pct": 40.0,
            "frag_file_count": 33,
            "candidate_small_files": 0,
            "table_size_mb": 15000.0,
            "avg_file_size_kb": 450000.0,
            "intensity": 0.2
        }

        decision, c_compact, c_defer = policy.decide(telemetry)
        self.assertEqual(decision, "DEFER")
        self.assertEqual(c_compact, 0.0)
        self.assertEqual(c_defer, 0.0)
        # Models should not even be called when candidate_small_files == 0
        self.mock_model_a.predict.assert_not_called()
        self.mock_model_b.predict.assert_not_called()

    def test_cost_benefit_decide_with_small_files(self):
        """With small files present, evaluate across all 4 queries and compare c_compact vs c_defer."""
        # Setup mock predictions:
        # Case 1: Model A predicts 3,000ms, Model B predicts 4,000ms
        # c_compact = 3000 + 500 = 3500; c_defer = 4000 + 400 = 4400 -> RUN
        self.mock_model_a.predict.return_value = np.array([3000.0])
        self.mock_model_b.predict.return_value = np.array([4000.0])

        policy = CostBenefitPolicy(
            model_a=self.mock_model_a,
            model_b=self.mock_model_b,
            metadata=self.metadata
        )

        telemetry = {
            "cpu_util_avg_1min": 25.0,
            "cpu_util_avg_5min": 25.0,
            "cpu_trend": 0.0,
            "mem_used_pct": 35.0,
            "frag_file_count": 45,
            "candidate_small_files": 12,
            "table_size_mb": 15000.0,
            "avg_file_size_kb": 350000.0,
            "intensity": 0.2
        }

        decision, c_compact, c_defer = policy.decide(telemetry)
        self.assertEqual(decision, "RUN")
        self.assertAlmostEqual(c_compact, 3500.0)
        self.assertAlmostEqual(c_defer, 4400.0)

        # Case 2: Model A predicts 6,000ms, Model B predicts 3,000ms
        # c_compact = 6000 + 500 = 6500; c_defer = 3000 + 400 = 3400 -> DEFER
        self.mock_model_a.predict.return_value = np.array([6000.0])
        self.mock_model_b.predict.return_value = np.array([3000.0])

        decision2, c_compact2, c_defer2 = policy.decide(telemetry)
        self.assertEqual(decision2, "DEFER")
        self.assertAlmostEqual(c_compact2, 6500.0)
        self.assertAlmostEqual(c_defer2, 3400.0)

    def test_literature_baselines_callable(self):
        """Verifies AutoCompPolicy, PeriodicCronPolicy, and TunedThresholdPolicy return RUN or DEFER."""
        table_meta = {"candidate_small_files": 35, "frag_file_count": 50}

        # AutoComp
        autocomp = AutoCompPolicy(small_file_ratio_threshold=0.20, min_candidate_files=30)
        self.assertIn(autocomp.decide(table_meta, elapsed_s=100.0), ["RUN", "DEFER"])

        # PeriodicCron
        cron = PeriodicCronPolicy(interval_minutes=60.0)
        self.assertIn(cron.decide(table_meta, elapsed_s=3600.0), ["RUN", "DEFER"])

        # TunedThreshold
        threshold = TunedThresholdPolicy(frag_threshold=40)
        self.assertIn(threshold.decide(table_meta, elapsed_s=100.0), ["RUN", "DEFER"])


if __name__ == "__main__":
    unittest.main()
