#!/usr/bin/env python3
"""
Policy 2: Always Defer
Always issues a DEFER decision for maintenance during the evaluation window.
Serves as an interference lower bound while explicitly tracking maintenance starvation.
"""

class AlwaysDeferPolicy:
    def __init__(self):
        self.name = "Always Defer"
        self.policy_id = "policy_2_always_defer"

    def decide(self, x_pred):
        """
        Input: x_pred (dict of pre-decision signals)
        Output: "RUN" or "DEFER"
        """
        return "DEFER"
