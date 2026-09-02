#!/usr/bin/env python3
"""
Policy 1: Always Run
Always issues a RUN decision for maintenance regardless of workload or system state.
"""

class AlwaysRunPolicy:
    def __init__(self):
        self.name = "Always Run (Baseline)"
        self.policy_id = "policy_1_always_run"

    def decide(self, x_pred):
        """
        Input: x_pred (dict of pre-decision signals)
        Output: "RUN" or "DEFER"
        """
        return "RUN"
