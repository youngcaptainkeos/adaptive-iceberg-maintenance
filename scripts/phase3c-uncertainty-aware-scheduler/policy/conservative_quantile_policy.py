#!/usr/bin/env python3
"""
Policy 5: Conservative / Uncertainty-Aware Policy
Uses 95th-percentile quantile regression upper-bound prediction on pre-decision features.
RUN maintenance only when predicted 95th-percentile QIR upper bound <= 10.0%, otherwise DEFER.
Note: This is a conservative quantile-bound policy, NOT a calibrated exceedance probability model.
"""

class ConservativeQuantilePolicy:
    def __init__(self, q95_threshold=10.0):
        self.name = "Conservative Quantile Policy (q=0.95 Upper Bound)"
        self.policy_id = "policy_5_conservative_quantile"
        self.q95_threshold = q95_threshold

    def decide(self, x_pred, predicted_q95_qir):
        """
        Input: x_pred (dict of pre-decision signals), predicted_q95_qir (float from model)
        Output: "RUN" or "DEFER"
        """
        if predicted_q95_qir <= self.q95_threshold:
            return "RUN"
        return "DEFER"
