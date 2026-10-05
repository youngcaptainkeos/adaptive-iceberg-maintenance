# Current State
## Current Research Phase
Transitioning from Phase 3B (Predictive modeling) to Phase 3C (Uncertainty-Aware Scheduling Policies).

## Completed Experiments
- Phase 0: Infrastructure validation (LST-Bench + Spark + Iceberg + DuckDB)
- Phases 2F-2H: Validated Physical-Layout Experiment
- Phase 3A: Concurrent Workload Interference (FIFO vs FAIR)
- Phase 3B: Predictive modeling of interference (Random Forest MAE 5.38%)

## Active Experiment
None currently executing. System initialization complete. Awaiting human approval to begin Phase 3C OOD Stress Test design.

## Pending Experiments
1. Phase 3C Out-of-Distribution (OOD) Stress Test (SF1)
2. Phase 3C Uncertainty Calibration Check
3. Phase 3C LOCO-CV Evaluation
4. Generalization/Scalability validation at SF10 (after SF1 validation)

## Important Findings
- Iceberg file layout significantly impacts concurrent query performance (parallelism vs overhead tradeoff).
- Random Forest model achieves MAE 5.38% on QIR prediction within the training distribution (12 configurations).

## Known Problems
- SLA violation classifier (ROC-AUC 0.531) is near-random and retained as an explicit negative result.

## Open Questions & Methodological Conflicts
- **Continuous Workload Trace:** The temporal trace audit recommendation is unresolved. The Research Director must establish whether temporal $X_{t-k:t} \rightarrow Y_{t+h}$ modeling is required by the thesis before accepting or rejecting this recommendation.

## Current Recommended Next Action
The Experiment Designer must formulate the exact specifications for the Phase 3C OOD Stress Test (SF1), lock in configurations, seeds, and metrics, and await human approval.
