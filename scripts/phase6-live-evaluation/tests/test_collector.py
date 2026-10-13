#!/usr/bin/env python3
"""
Unit Test Suite for Phase 6.1B Data Collector
Tests:
- fetch_table_metadata dictionary schema (frag_file_count, candidate_small_files, table_size_mb)
- WorkloadDriver pop_latency return shape (qid, latency_ms)
- Header column count (18 columns)
- CLI argument parsing
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE6_DIR = os.path.dirname(CURRENT_DIR)
REPO_ROOT = os.path.dirname(os.path.dirname(PHASE6_DIR))
for path in [PHASE6_DIR, REPO_ROOT]:
    if path not in sys.path:
        sys.path.insert(0, path)

import collect_training_data as ctd


class TestCollectorPhase61B(unittest.TestCase):
    """Test suite for Phase 6.1B telemetry and data collection refactoring."""

    def test_fetch_table_metadata_schema(self):
        """Verifies fetch_table_metadata queries and returns expected dictionary keys."""
        mock_cursor = MagicMock()
        # First call: (count, sum_bytes) -> (35, 15728640000)
        # Second call: (small_count,) -> (12,)
        mock_cursor.fetchall.side_effect = [
            [(35, 15728640000)],
            [(12,)]
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("collect_training_data.PYHIVE_AVAILABLE", True):
            with patch("collect_training_data.hive.Connection", return_value=mock_conn):
                meta = ctd.fetch_table_metadata("127.0.0.1", 10000, "local.tpch_sf100.lineitem")

                self.assertIn("frag_file_count", meta)
                self.assertIn("candidate_small_files", meta)
                self.assertIn("table_size_mb", meta)
                self.assertEqual(meta["frag_file_count"], 35)
                self.assertEqual(meta["candidate_small_files"], 12)
                self.assertAlmostEqual(meta["table_size_mb"], 15728640000 / (1024.0 * 1024.0))

    def test_fetch_table_metadata_fallback(self):
        """Verifies fetch_table_metadata returns zeroed dict if PyHive fails or errors out."""
        with patch("collect_training_data.PYHIVE_AVAILABLE", False):
            meta = ctd.fetch_table_metadata("127.0.0.1", 10000, "local.tpch_sf100.lineitem")
            self.assertEqual(meta["frag_file_count"], 0)
            self.assertEqual(meta["candidate_small_files"], 0)
            self.assertEqual(meta["table_size_mb"], 0.0)

    def test_workload_driver_pop_latency_tuple(self):
        """Verifies WorkloadDriver.pop_latency returns (qid, latency_ms) or (nan, nan)."""
        driver = ctd.WorkloadDriver(host="127.0.0.1", port=10000, table="test_table")
        
        # When empty
        empty_res = driver.pop_latency()
        self.assertIsInstance(empty_res, tuple)
        self.assertEqual(len(empty_res), 2)
        self.assertTrue(np.isnan(empty_res[0]))
        self.assertTrue(np.isnan(empty_res[1]))

        # When populated with query 1 (group-by query)
        driver.completed_queries.append((1, 48920.5))
        qid, lat_ms = driver.pop_latency()
        self.assertEqual(qid, 1)
        self.assertAlmostEqual(lat_ms, 48920.5)

        # Queue should be empty now
        empty_res2 = driver.pop_latency()
        self.assertTrue(np.isnan(empty_res2[0]))
        self.assertTrue(np.isnan(empty_res2[1]))

    def test_header_column_count(self):
        """Verifies the CSV header contains exactly 18 columns including query_id and candidate_small_files."""
        expected_cols = [
            "timestamp", "elapsed_s", "cpu_util_pct", "cpu_util_avg_1min", "cpu_util_avg_5min", "cpu_trend",
            "mem_used_pct", "disk_io_read_bytes", "disk_io_write_bytes", "frag_file_count", "candidate_small_files",
            "table_size_mb", "avg_file_size_kb", "intensity", "compaction_active", "query_id",
            "query_latency_ms", "query_latency_during_compaction_ms"
        ]
        self.assertEqual(len(expected_cols), 18)

    def test_parse_args_defaults(self):
        """Verifies argument parser defaults, including compaction interval."""
        with patch("sys.argv", ["collect_training_data.py"]):
            args = ctd.parse_args()
            self.assertEqual(args.compaction_interval_minutes, 45.0)
            self.assertEqual(args.duration_hours, 4.0)
            self.assertEqual(args.port, 10000)


if __name__ == "__main__":
    unittest.main()
