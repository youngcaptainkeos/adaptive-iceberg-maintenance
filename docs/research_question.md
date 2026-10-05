# Core Research Question
Given that lakehouse maintenance needs to be performed, when should it be executed so that its storage benefits are obtained while minimizing interference with concurrent query workloads?

# Hypotheses
1. A learned predictor can estimate concurrent workload interference (Query Interference Ratio or QIR) better than static heuristics.
2. A model can be calibrated to accurately report its own uncertainty (e.g., via conformal prediction).
3. An uncertainty-aware scheduler that falls back to heuristics on out-of-distribution (OOD) data is safer and more effective than a pure ML scheduler or a pure heuristic scheduler.
