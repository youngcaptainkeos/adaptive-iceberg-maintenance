"""
Literature Baselines for Lakehouse Table Maintenance (Phase 6.1A)
Methodology v2.1

This module implements peer-reviewed and industry-standard competitor baselines:
1. AutoCompPolicy: Storage-metadata-driven heuristic based on small file ratio & accumulation
   (Gruenheid et al., VLDB 2024 / Microsoft & LinkedIn).
2. PeriodicCronPolicy: Fixed-interval scheduled maintenance (AWS EMR / Databricks Operational Standard).
3. TunedThresholdPolicy: Active auto-optimize threshold (40 small files, replacing inert 200 barrier).
"""

from typing import Dict, Any


class BaselinePolicyInterface:
    """Standard interface for lakehouse maintenance baseline policies."""

    def decide(self, table_metadata: Dict[str, Any], elapsed_s: float = 0.0) -> str:
        """
        Decides whether to trigger table compaction or defer.

        Args:
            table_metadata: Dictionary containing storage metadata
                            (e.g., 'candidate_small_files', 'frag_file_count', 'table_size_mb').
            elapsed_s: Elapsed simulation / evaluation time in seconds.

        Returns:
            'RUN' to execute compaction, 'DEFER' to wait.
        """
        raise NotImplementedError


class AutoCompPolicy(BaselinePolicyInterface):
    """
    AutoComp Policy (Gruenheid et al., VLDB 2024 / Microsoft & LinkedIn).

    AutoComp evaluates table storage traits to trigger compaction proactively
    based on the uncompacted small-file reduction ratio:
        Delta F_c = N_small_files / N_total_files
    AutoComp decides purely on storage metadata and is blind to concurrent query traffic and CPU load.
    """

    def __init__(self, small_file_ratio_threshold: float = 0.20, min_candidate_files: int = 30):
        self.small_file_ratio_threshold = float(small_file_ratio_threshold)
        self.min_candidate_files = int(min_candidate_files)

    def decide(self, table_metadata: Dict[str, Any], elapsed_s: float = 0.0) -> str:
        small_files = table_metadata.get('candidate_small_files', 0)
        total_files = table_metadata.get('frag_file_count', max(small_files, 1))
        ratio = small_files / max(total_files, 1)

        if small_files >= self.min_candidate_files or ratio >= self.small_file_ratio_threshold:
            return 'RUN'
        return 'DEFER'


class PeriodicCronPolicy(BaselinePolicyInterface):
    """
    Periodic Cron Policy (AWS EMR / Databricks Recommended Operational Baseline).

    Industry production standard: schedules maintenance on a fixed deterministic timer,
    regardless of query load or table state.
    """

    def __init__(self, interval_minutes: float = 60.0):
        self.interval_minutes = float(interval_minutes)
        self.interval_s = self.interval_minutes * 60.0
        self.last_run_s = 0.0

    def decide(self, table_metadata: Dict[str, Any], elapsed_s: float = 0.0) -> str:
        if (elapsed_s - self.last_run_s) >= self.interval_s:
            self.last_run_s = elapsed_s
            return 'RUN'
        return 'DEFER'


class TunedThresholdPolicy(BaselinePolicyInterface):
    """
    Tuned Threshold Policy (Active Auto-Optimize Baseline).

    A properly-tuned auto-optimize threshold (replacing the inert 200-file barrier).
    """

    def __init__(self, frag_threshold: int = 40):
        self.frag_threshold = int(frag_threshold)

    def decide(self, table_metadata: Dict[str, Any], elapsed_s: float = 0.0) -> str:
        small_files = table_metadata.get('candidate_small_files', table_metadata.get('frag_file_count', 0))
        if small_files >= self.frag_threshold:
            return 'RUN'
        return 'DEFER'
