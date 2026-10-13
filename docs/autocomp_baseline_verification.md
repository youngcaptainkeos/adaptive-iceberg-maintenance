# AutoComp baseline correction

The [author-hosted paper](https://www.cs.umd.edu/~abadi/papers/autocomp-sigmod.pdf)
identifies AutoComp as SIGMOD-Companion 2025. Historical project comments calling it
VLDB 2024 are incorrect. Its [candidate-selection description](https://arxiv.org/html/2504.04186v1#S4.SS3)
includes resource-constrained ranking and unconstrained threshold selection;
its framework also handles candidate generation, estimated traits and scheduling.

Our historical `AutoCompPolicy` implements a small-file ratio/count heuristic. It
does not reproduce the full framework or establish faithful parameterization of a
specified scenario. Do not label old comparisons a validated SOTA reproduction.
The evaluator is retired; historical artifacts remain diagnostic evidence.

Before evaluation, identify the precise scenario/algorithm, implement its estimator
and resource constraints, justify parameters from the paper or training-only tuning,
and match useful maintenance progress. Keep a separate honestly named threshold
baseline. Forecast-aware timing remains a candidate contribution, not established
novelty: compare against strong resource-aware scheduling and contemporary work,
then demonstrate added value using held-out physical schedules.

The baseline module now refuses construction through the misleading `AutoCompPolicy`
name. Its separately named threshold/periodic prototypes require explicit parameters
and measured counts; removed default ratio/count/period values and missing-metadata
zero fallbacks. They remain unvalidated prototypes, not publication baselines.
No evaluator is enabled by this interface cleanup. A proposed candidate action
still requires actual rewrite eligibility/results from the physical executor.
