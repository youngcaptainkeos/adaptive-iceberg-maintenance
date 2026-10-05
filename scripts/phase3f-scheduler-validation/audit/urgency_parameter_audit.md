# Phase 3F Audit 2: Maintenance Urgency Formula Provenance & Leakage Audit

## 1. Executive Provenance Summary
This audit inspects the mathematical formula, component weights, normalization methods, and parameter provenance of the Storage Health & Maintenance Urgency metric $U(s)$.

## 2. Mathematical Definition of Urgency Metric $U(s)$
$$U(s) = 100.0 \times \left[ 0.40 \cdot \min\left(1.0, \frac{N_{\text{files}}}{750}\right) + 0.20 \cdot \min\left(1.0, \frac{S_{\text{table}}}{200}\right) + 0.20 \cdot \min\left(1.0, \frac{500}{\text{AvgFileSize} + 1}\right) + 0.20 \cdot \min\left(1.0, \frac{k}{5}\right) \right]$$

## 3. Parameter Audit Matrix

| Parameter | Expression | Assigned Value | Provenance & Selection Method | Leakage Classification |
| --- | --- | --- | --- | --- |
| `w1 (Fragmentation Ratio Weight)` | `w1 * min(1.0, frag_files / 750.0)` | **0.40** | Domain heuristic choice (File count is primary driver of scan amplification) | `Pre-specified domain rule` |
| `w2 (Table Size Weight)` | `w2 * min(1.0, table_mb / 200.0)` | **0.20** | Domain heuristic choice (Table metadata overhead scale) | `Pre-specified domain rule` |
| `w3 (Inverse File Size Weight)` | `w3 * min(1.0, 500.0 / (avg_file_kb + 1.0))` | **0.20** | Domain heuristic choice (Small file penalty factor) | `Pre-specified domain rule` |
| `w4 (Pending Deferral Weight)` | `w4 * min(1.0, pending_slots / 5.0)` | **0.20** | Domain heuristic choice (Starvation prevention counter) | `Pre-specified domain rule` |
| `U_critical (Max Urgency Threshold)` | `Urgency >= U_critical` | **70.0** | Domain heuristic cutoff for mandatory compaction override | `Partially heuristic / domain-guided` |

## 4. Scientific Classification & Evaluation Leakage Verdict
- **Policy Classification**: **`Partially heuristic`**
- **Leakage Analysis**: The weights $w = [0.40, 0.20, 0.20, 0.20]$ were **not** fitted via mathematical hyperparameter optimization on test set SLA metrics. However, because $U_{\text{critical}} = 70.0$ was selected after observing 750-file table fragmentation, the policy is partially heuristic and must be reported as such in paper publications.
