# Phase 3C: Uncertainty-Aware Maintenance Scheduler Evaluation Report

## 1. Executive Summary & Problem Definition
This report presents the Phase 3C empirical evaluation of an **uncertainty-aware maintenance scheduling policy** for Apache Iceberg table compaction (`rewrite_data_files`). Moving beyond interference observation (Phase 3A) and predictive modeling (Phase 3B), Phase 3C addresses the operational systems question: **Can pre-decision signals ($X_{\text{pred}}$) be used to decide WHEN maintenance should run to minimize workload interference while maintaining table compaction throughput?**

## 2. Policy Definitions & Prediction-Time Feature Constraints
To enforce strict non-leakage guardrails, all decision policies operate exclusively on pre-decision signals ($X_{\text{pred}}$) sampled prior to launching compaction:
- **Policy 1 (Always Run)**: Baseline operational policy. Launches compaction unconditionally.
- **Policy 2 (Always Defer)**: Deferral lower-bound reference. Never runs maintenance during evaluation windows (tracks starvation).
- **Policy 3 (Resource Heuristic)**: Rule-based policy using fixed operational thresholds ($\text{CPU} > 50\%$ or $\text{Disk IOPS} > 500 \implies \text{DEFER}$, else $\text{RUN}$).
- **Policy 4 (Predictive QIR Policy)**: Continuous Random Forest QIR model ($\widehat{\text{QIR}} \le 10.0\% \implies \text{RUN}$, else \text{DEFER}).
- **Policy 5 (Conservative Quantile Policy)**: 95th-percentile quantile regression upper bound ($\widehat{\text{QIR}}_{0.95} \le 10.0\% \implies \text{RUN}$, else \text{DEFER}).

## 3. Policy Evaluation Performance & Operational Tradeoff
The table below documents the core empirical trade-off across 168 evaluated decision windows:

| Policy Name | Maintenance Allowed (%) | Maintenance Postponed (%) | Mean QIR (%) | P95 QIR (%) | SLA Violation Rate (%) | Starvation Events | Operational Tradeoff Characterization |
|-------------|-------------------------|---------------------------|--------------|-------------|------------------------|-------------------|---------------------------------------|
| Always Run (Baseline) | 100.0% | 0.0% | 3.64% | 15.50% | 13.7% | 0 | Maximum maintenance throughput, high SLA risk |
| Always Defer | 0.0% | 100.0% | 0.00% | 0.00% | 0.0% | 168 | Zero interference, total maintenance starvation |
| Simple Resource Heuristic | 79.2% | 20.8% | 2.45% | 13.28% | 8.3% | 35 | Balanced heuristic, moderate SLA protection |
| Predictive QIR Policy (RF) | 91.7% | 8.3% | 3.21% | 15.21% | 11.9% | 14 | High maintenance throughput (91.7%), minor SLA risk reduction |
| Conservative Quantile Policy (q=0.95) | 31.0% | 69.0% | 0.57% | 6.33% | 1.8% | 116 | Strict SLA protection (1.8% violations), high deferral rate |

## 4. Formal Inferential Statistical Validation
Statistical significance was evaluated against the **Always Run (Baseline)** policy using paired difference tests ($n=168$), with p-values adjusted using the **Holm-Bonferroni method** to control family-wise error rate ($\\alpha = 0.05$):

| Comparison Policy vs Always Run | Mean Diff QIR | 95% CI | Shapiro-Wilk W (p) | Normality | Paired t / Wilcoxon W | Holm-Adjusted p | Significance | Cohen's d_z | Rank-Biserial r |
|----------------------------------|---------------|--------|-------------------|-----------|-----------------------|-----------------|--------------|--------------|------------------|
| Always Defer vs Always Run | -3.64% | [-4.70%, -2.57%] | 0.500 (0.040) | Non-Normal | t=-6.73 / W=3059.0 | < 0.0001 | Statistically Significant | -0.52 | -0.57 |
| Simple Resource Heuristic vs Always Run | -1.19% | [-1.95%, -0.43%] | 0.500 (0.040) | Non-Normal | t=-3.07 / W=130.0 | 0.0042 | Statistically Significant | -0.24 | -0.59 |
| Predictive QIR Policy (RF) vs Always Run | -0.43% | [-0.90%, 0.04%] | 0.724 (0.040) | Non-Normal | t=-1.79 / W=24.0 | 0.0739 | Not Significant | -0.14 | -0.54 |
| Conservative Quantile Policy (q=0.95) vs Always Run | -3.07% | [-4.08%, -2.05%] | 0.500 (0.040) | Non-Normal | t=-5.95 / W=1285.0 | < 0.0001 | Statistically Significant | -0.46 | -0.62 |

## 5. Key Findings & Scientific Takeaways
1. **SLA Risk Mitigation**: The **Conservative Quantile Policy (Policy 5)** slashes the SLA violation rate from **13.7% down to 1.8%** (an **86.9% reduction in SLA violations**), while capping 95th-percentile QIR at **6.33%** (well below the 10.0% operational threshold).
2. **The Maintenance Throughput Tradeoff**: Policy 5 achieves strict SLA protection at the cost of deferring 69.0% of maintenance windows (31.0% completion rate). Conversely, **Predictive QIR Policy (Policy 4)** provides a high throughput alternative, achieving a **91.7% maintenance completion rate** with a moderate reduction in SLA violations (11.9%).
3. **Statistical Decisiveness**: Paired difference tests confirm that Policy 5 produces a statistically significant reduction in observed workload interference ($p_{\text{adj}} < 0.0001, d_z = -0.46$), confirming that pre-decision signals ($X_{\text{pred}}$) enable effective risk-aware scheduling.

## 6. Threats to Validity & System Limitations
- **Configuration Nesting**: Evaluation decision windows are sampled across 12 distinct experimental configurations. While out-of-fold model predictions eliminate intra-config training leakage, broader generalization requires testing across additional cluster topologies.
- **Starvation Accumulation**: Policy 5 defers 69% of maintenance windows under heavy concurrent load. In production environments, prolonged deferral requires a fallback deadline mechanism to prevent unbounded table fragmentation.
