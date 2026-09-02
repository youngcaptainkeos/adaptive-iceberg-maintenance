# Phase 3C: Uncertainty-Aware Maintenance Scheduler

This directory contains the experimental evaluation harness for Phase 3C, comparing five maintenance scheduling policies under strict pre-decision signal constraints ($X_{\text{pred}}$).

## Policies Evaluated
1. **Policy 1 (Always Run)**: Baseline maintenance policy. Compaction always runs immediately.
2. **Policy 2 (Always Defer)**: Maintenance never runs during evaluation windows. Serves as interference lower bound while explicitly tracking maintenance starvation.
3. **Policy 3 (Resource Heuristic)**: Rule-based policy using pre-decision system load ($\text{CPU} > 50\%$ or $\text{Disk IOPS} > 500 \implies \text{DEFER}$, else $\text{RUN}$).
4. **Policy 4 (Predictive QIR Policy)**: Continuous Random Forest regressor predicts QIR. ($\widehat{\text{QIR}} \le 10\% \implies \text{RUN}$, else $\text{DEFER}$).
5. **Policy 5 (Conservative Quantile Policy)**: 95th-percentile quantile regression upper bound ($\widehat{\text{QIR}}_{0.95} \le 10\% \implies \text{RUN}$, else $\text{DEFER}$).

## Information Boundaries
- **Input Features ($X_{\text{pred}}$)**: ONLY pre-decision physical layout, system load, baseline reference, and execution context.
- **Evaluation Telemetry ($X_{\text{eval}}$)**: Post-execution durations, actual QIR, and SLA violations are strictly isolated for evaluation.

## Artifacts Generated
- `results/policy_decisions.csv`
- `results/policy_experiment_results.csv`
- `results/policy_statistical_results.csv`
- `results/policy_tradeoff_summary.csv`
- `reports/phase3c_scheduler_report.md`
