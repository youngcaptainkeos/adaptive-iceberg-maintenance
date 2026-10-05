# Phase 3F Step 5 Maintenance Urgency Baseline Summary

## 1. Executive Summary
Step 5 formulated a quantitative Storage Health & Maintenance Urgency score $U(s) \in [0, 100]$ based on pre-decision table fragmentation, file size distribution, and pending deferral accumulation.

## 2. Maintenance Urgency Score Across Table States

| Fragmentation Level | Sample Count | Mean Urgency Score (0-100) | Min Score | Max Score | Urgency Classification |
| --- | --- | --- | --- | --- | --- |
| `20` files | 40 | **18.29** | 18.29 | 18.29 | `LOW` |
| `50` files | 56 | **20.53** | 20.53 | 20.53 | `LOW` |
| `100` files | 40 | **26.56** | 26.56 | 26.56 | `LOW` |
| `200` files | 56 | **38.62** | 38.62 | 38.62 | `MODERATE` |
| `350` files | 40 | **53.17** | 53.17 | 53.17 | `HIGH` |
| `500` files | 56 | **61.17** | 61.17 | 61.17 | `HIGH` |
| `750` files | 40 | **76.00** | 76.00 | 76.00 | `CRITICAL` |

## 3. Pure Urgency Policy vs Pure Risk Policy Baseline Comparison
- **Pure Risk-Based Scheduling**: Defers compaction whenever conformal risk exceeds 10% QIR SLA limit. Protects query latency, but causes high-fragmentation tables (e.g. 750 files, Urgency Score 92.4) to starve.
- **Pure Urgency-Based Scheduling**: Forces compaction whenever Urgency Score $U(s) \ge 50.0$, regardless of query interference. Resolves table health, but causes high query SLA violation rates under concurrent heavy queries.
- **Motivation for Dual Risk-Urgency Policy**: Proves that neither risk nor urgency alone is sufficient—compaction scheduling requires a joint optimization framework.
