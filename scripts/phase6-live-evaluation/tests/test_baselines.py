#!/usr/bin/env python3
"""
Unit Test Suite: Literature Baselines (Phase 6.1A)
Methodology v2.1

Tests AutoCompPolicy, PeriodicCronPolicy, and TunedThresholdPolicy.
"""

import os
import sys
import unittest

# Ensure module import paths resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE6_DIR = os.path.dirname(CURRENT_DIR)
REPO_ROOT = os.path.dirname(os.path.dirname(PHASE6_DIR))
for path in [PHASE6_DIR, REPO_ROOT]:
    if path not in sys.path:
        sys.path.insert(0, path)

from policies.literature_baselines import (
    BaselinePolicyInterface,
    AutoCompPolicy,
    PeriodicCronPolicy,
    TunedThresholdPolicy,
)


class TestLiteratureBaselines(unittest.TestCase):
    """Test suite for literature and production baseline policies."""

    def test_autocomp_defer_on_clean_table(self):
        """
        State: candidate_small_files: 2, frag_file_count: 35 (ratio = 5.7%).
        Assert decide() returns 'DEFER'.
        """
        policy = AutoCompPolicy(small_file_ratio_threshold=0.20, min_candidate_files=30)
        table_metadata = {
            "candidate_small_files": 2,
            "frag_file_count": 35,
        }
        decision = policy.decide(table_metadata, elapsed_s=100.0)
        self.assertEqual(decision, "DEFER")

    def test_autocomp_run_on_high_ratio(self):
        """
        State: candidate_small_files: 10, frag_file_count: 40 (ratio = 25.0%).
        Assert decide() returns 'RUN'.
        """
        policy = AutoCompPolicy(small_file_ratio_threshold=0.20, min_candidate_files=30)
        table_metadata = {
            "candidate_small_files": 10,
            "frag_file_count": 40,
        }
        decision = policy.decide(table_metadata, elapsed_s=200.0)
        self.assertEqual(decision, "RUN")

    def test_autocomp_run_on_file_count(self):
        """
        State: candidate_small_files: 32, frag_file_count: 200 (ratio = 16.0% but files >= 30).
        Assert decide() returns 'RUN'.
        """
        policy = AutoCompPolicy(small_file_ratio_threshold=0.20, min_candidate_files=30)
        table_metadata = {
            "candidate_small_files": 32,
            "frag_file_count": 200,
        }
        decision = policy.decide(table_metadata, elapsed_s=300.0)
        self.assertEqual(decision, "RUN")

    def test_periodic_cron_timing(self):
        """
        elapsed_s = 1800 (30 min) -> Assert 'DEFER'
        elapsed_s = 3600 (60 min) -> Assert 'RUN'
        elapsed_s = 3660 (61 min) -> Assert 'DEFER'
        elapsed_s = 7200 (120 min) -> Assert 'RUN'
        """
        policy = PeriodicCronPolicy(interval_minutes=60.0)
        table_metadata = {"frag_file_count": 50}

        self.assertEqual(policy.decide(table_metadata, elapsed_s=1800.0), "DEFER")
        self.assertEqual(policy.decide(table_metadata, elapsed_s=3600.0), "RUN")
        self.assertEqual(policy.decide(table_metadata, elapsed_s=3660.0), "DEFER")
        self.assertEqual(policy.decide(table_metadata, elapsed_s=7200.0), "RUN")

    def test_tuned_threshold(self):
        """
        candidate_small_files: 39 -> Assert 'DEFER'
        candidate_small_files: 41 -> Assert 'RUN'
        """
        policy = TunedThresholdPolicy(frag_threshold=40)

        meta_below = {"candidate_small_files": 39}
        self.assertEqual(policy.decide(meta_below, elapsed_s=100.0), "DEFER")

        meta_above = {"candidate_small_files": 41}
        self.assertEqual(policy.decide(meta_above, elapsed_s=200.0), "RUN")

    def test_tuned_threshold_fallback_to_frag_file_count(self):
        """
        Verify TunedThresholdPolicy falls back to frag_file_count if candidate_small_files is omitted.
        """
        policy = TunedThresholdPolicy(frag_threshold=40)

        meta_below = {"frag_file_count": 38}
        self.assertEqual(policy.decide(meta_below, elapsed_s=100.0), "DEFER")

        meta_above = {"frag_file_count": 40}
        self.assertEqual(policy.decide(meta_above, elapsed_s=200.0), "RUN")


if __name__ == "__main__":
    unittest.main()
