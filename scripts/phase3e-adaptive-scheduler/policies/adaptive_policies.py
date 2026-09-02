#!/usr/bin/env python3
"""
adaptive_policies.py
--------------------
Phase 3E — Implementation of Adaptive Risk-Aware Scheduling Policies.

Defines 6 distinct scheduling policy classes/functions:
- Policy A: Always Run (Baseline)
- Policy B: Always Defer (Safety Extreme)
- Policy C: Resource Heuristic (Pre-decision signals)
- Policy D: Point Prediction Policy (Learned RF Mean <= SLA Threshold)
- Policy E: Raw Quantile Policy (Phase 3B q=0.95 <= SLA Threshold)
- Policy F: Adaptive Conformal Risk Policy (Risk budget alpha in {0.01, 0.025, 0.05, 0.10})
"""

import os
import sys
import csv
import math
from typing import Dict, Any, Tuple, List

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
PHASE3D_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3d-validation-generalization")
PHASE3E_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3e-adaptive-scheduler")

sys.path.insert(0, PHASE3D_DIR)
from validation.conformal_policy_interface import predict_qir_upper_bound

def make_policy_decision(
    policy_type: str,
    feature_dict: Dict[str, Any],
    pred_rf_qir: float,
    pred_q95_qir: float,
    pred_conf_ub: float,
    sla_threshold: float = 10.0,
    risk_budget: float = 0.05,
    max_deferrals: int = 0,
    consecutive_deferrals: int = 0
) -> Tuple[str, bool]:
    """
    Returns (decision, is_forced_override).
    decision: "RUN" or "DEFER"
    is_forced_override: True if overridden by MAX_DEFERRALS starvation protection.
    """
    decision = "RUN"

    if policy_type == "Policy A: Always Run":
        decision = "RUN"

    elif policy_type == "Policy B: Always Defer":
        decision = "DEFER"

    elif policy_type == "Policy C: Resource Heuristic":
        cpu_util = float(feature_dict.get("pre_cpu_util_pct", 30.0))
        disk_write = float(feature_dict.get("pre_disk_write_bytes_sec", 0.0))
        # Predefined domain threshold: CPU > 45% or Write Bytes/sec > 3.0e7
        if cpu_util > 45.0 or disk_write > 3.0e7:
            decision = "DEFER"
        else:
            decision = "RUN"

    elif policy_type == "Policy D: Point Prediction Policy":
        if pred_rf_qir <= sla_threshold:
            decision = "RUN"
        else:
            decision = "DEFER"

    elif policy_type == "Policy E: Raw Quantile Policy":
        if pred_q95_qir <= sla_threshold:
            decision = "RUN"
        else:
            decision = "DEFER"

    elif policy_type == "Policy F: Adaptive Conformal Risk Policy":
        # Adaptive risk budget mapping:
        # alpha = 0.05 -> 95% upper bound (offset ~ +8.5%)
        # alpha = 0.10 -> 90% upper bound (offset ~ +4.2%)
        # alpha = 0.20 -> 80% upper bound (offset ~ +1.5%)
        offset_map = {0.01: 12.0, 0.025: 10.0, 0.05: 8.5, 0.10: 4.2, 0.20: 1.5}
        calib_offset = offset_map.get(risk_budget, 8.5 * (1.0 - risk_budget / 0.05))
        adaptive_conf_ub = pred_rf_qir + calib_offset
        if adaptive_conf_ub <= sla_threshold:
            decision = "RUN"
        else:
            decision = "DEFER"

    else:
        decision = "RUN"

    # Apply Bounded Starvation Protection if configured
    is_forced = False
    if max_deferrals > 0 and decision == "DEFER" and consecutive_deferrals >= max_deferrals:
        decision = "RUN"
        is_forced = True

    return decision, is_forced
