# Phase 3D: Validation, Calibration & Out-of-Distribution Generalization

This workspace contains the scientific validation, falsification, quantile calibration, and Out-of-Distribution (OOD) generalization harness for Phase 3.

## Structure
- `validation/`: Dataset audit, LOCO-CV, trivial baselines, quantile calibration (conformal prediction), SLA classifier diagnostics.
- `policies/`: Policy baselines (Random P=0.5, Explicit Resource Heuristic), Pareto & starvation analysis.
- `ood/`: Table fragmentation preparation (100 & 350 files), OOD experimental runner (Q3 single-stream, mixed-order stream), zero-shot evaluation engine.
- `analysis/plots/`: Visualization output directory.
- `results/`: Output CSV data artifacts and calibration summaries.
- `reports/`: Final scientific report (`phase3d_validation_report.md`).
