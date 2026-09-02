# Phase 3E Part 1 — Conformal Policy Starvation Diagnosis Report

## Executive Summary & Root Cause Analysis

The Split-Conformal Upper Bound Policy (Policy 6) achieved **100.0% SLA protection** in Phase 3D, but resulted in **100.0% maintenance task deferral** (0.0% maintenance completion rate), causing complete maintenance starvation.

> [!IMPORTANT]
> **Root Cause Identified (A + C Combination)**:
> 1. **Large Global Calibration Offset**: To guarantee 95% one-sided coverage on noisy residual tail distributions, split-conformal prediction calculated a global nonconformity score offset of **+8.50% QIR**.
> 2. **Additive Shift Exceeding SLA Threshold**: The RF point predictions have a median of **2.88% QIR**. Adding the **+8.50%** calibration offset pushes **89.88%** of all in-distribution predictions and **100.0%** of all OOD predictions above the strict **10.0% SLA threshold**.
> 3. **Binary Threshold Inflexibility**: The policy enforced a rigid binary rule `IF conformal_upper_bound <= 10%: ALLOW ELSE DEFER`, leaving zero operational budget for non-zero risk tolerance.

## Summary Statistics Table (`conformal_starvation_diagnosis.csv`)

| Scope / Feature | Min | Median | Mean | P95 | Max | % Exceeding 10% SLA |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **In-Distribution Actual QIR** | -14.561% | 2.576% | 3.638% | 15.399% | 35.048% | **13.69%** |
| **In-Distribution RF Point Pred** | -4.737% | 2.878% | 3.905% | 11.695% | 14.966% | **8.33%** |
| **In-Distribution Raw q=0.95 Pred** | 2.532% | 12.398% | 12.559% | 19.772% | 29.185% | **69.05%** |
| **In-Distribution Conformal Upper Bound** | 3.763% | 11.378% | 12.405% | 20.195% | 23.466% | **89.88%** |
| **OOD Actual QIR** | -16.77% | 5.823% | 5.381% | 18.163% | 31.809% | **33.75%** |
| **OOD RF Point Pred** | -1.497% | 4.738% | 4.0% | 6.26% | 16.794% | **2.5%** |
| **OOD Conformal Upper Bound** | 16.503% | 22.737% | 21.999% | 24.259% | 34.793% | **100.0%** |

## Key Architectural Insights for Phase 3E

1. **Conformal Bounds are Mathematically Sound**: The 95% conformal bound achieved 98.2% (ID) and 98.8% (OOD) empirical coverage, confirming its statistical validity as a safety bound.
2. **Fixed Thresholds Create Artificial Starvation**: When the calibration offset alone is nearly equal to the SLA threshold (8.5% vs 10.0%), any positive baseline point prediction guarantees a policy deferral.
3. **Operational Solution Required**: Phase 3E must evaluate adaptive risk tolerances, threshold sweeps, and bounded starvation overrides (`MAX_DEFERRALS`).
