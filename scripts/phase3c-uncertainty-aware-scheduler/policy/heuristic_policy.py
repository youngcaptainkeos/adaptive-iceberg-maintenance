#!/usr/bin/env python3
"""
Policy 3: Simple Resource Heuristic
Rule-based policy using pre-decision CPU utilization and disk IOPS.
Defers maintenance when pre-decision CPU > 50% or Disk IOPS > 500.
"""

class HeuristicPolicy:
    def __init__(self, cpu_threshold=50.0, iops_threshold=500.0):
        self.name = "Simple Resource Heuristic"
        self.policy_id = "policy_3_heuristic"
        self.cpu_threshold = cpu_threshold
        self.iops_threshold = iops_threshold

    def decide(self, x_pred):
        """
        Input: x_pred (dict of pre-decision signals)
        Output: "RUN" or "DEFER"
        """
        cpu_util = float(x_pred.get("pre_cpu_util_pct", 0.0))
        read_iops = float(x_pred.get("pre_disk_read_iops", 0.0))
        write_iops = float(x_pred.get("pre_disk_write_iops", 0.0))
        total_iops = read_iops + write_iops

        if cpu_util > self.cpu_threshold or total_iops > self.iops_threshold:
            return "DEFER"
        return "RUN"
