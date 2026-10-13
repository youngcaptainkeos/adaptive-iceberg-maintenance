# Architecture choice and validation

Status: design recommendation for empirical comparison, not a validated winner.
Updated: 2026-10-13. No scheduler/model implementation changed in this step.

## Keep the research question independent of the number of models

The goal is forecast-aware, uncertainty-aware maintenance timing, not building
three models. Three functional tasks remain necessary: forecast demand, estimate
action consequences, and choose a maintenance schedule. They need not correspond
to three independently trained regressors.

The user's proposed A/B/C design is reasonable. The current A/B cost models must
remain a baseline so we can measure whether future-demand forecasts actually help.
However, separate regressors trained on different system conditions can be poorly
aligned. Their numerical difference is not automatically the effect of maintenance.
RUN_002 inversion and RUN_003 failure make this a concrete project risk.

## Preferred candidate to test

Use a demand forecaster and a shared action-conditioned cost estimator, coupled
to measured table-state transitions and a receding-horizon scheduler.

- Forecaster: future query arrivals, query characteristics/mix, and ingestion,
  conditioned only on past observations. CPU is influenced by maintenance and
  cannot alone represent action-independent demand.
- Cost estimator: query latency/slowdown conditioned on state, offered demand,
  query characteristics, whether maintenance overlaps, and rewrite characteristics.
  A shared model, a baseline plus learned residual, or shared multi-head structure
  are candidates. Do not choose a deep architecture merely for sophistication.
- Transition estimator: rewrite duration, fragmentation growth and post-maintenance
  layout, initially from measured physical events rather than invented constants.
- Scheduler: compare candidate start times over the same horizon; include waiting,
  rewrite, and post-rewrite costs, then execute one action and replan.

This formulation may use two learned models, several heads, or simple empirical
components. Number of artifacts is an implementation detail. Begin with persistence
forecasting and an empirical cost baseline before adding complexity.

## Important limits

A shared model does not cure confounding. Collect matched/counterbalanced physical
conditions with overlap in workload and table state across actions. Otherwise
action-conditioned predictions extrapolate where no comparison was measured.
Do not force predicted interference to be positive to fit a preferred narrative;
physical layout/parallelism can create legitimate heterogeneous effects.

Low latency MAE does not ensure correct ranking of candidate plans. Evaluate
plan-ordering error, decision regret relative to observed alternatives, and
maintenance progress. Do not invent counterfactual outcomes from ground truth.
Uncertainty must cover forecast, state transition, and action-cost errors; a
conformal offset on one latency regressor is not an end-to-end safety guarantee.

## Selection experiment after the measurement gate

Compare, using the same physical data splits and compute budget:

1. Current-state empirical scheduler without future forecasting.
2. Forecast plus separate A/B cost models.
3. Forecast plus a shared action-conditioned cost model.
4. No-uncertainty variants and full uncertainty treatment.
5. Explicit oracle forecast as a reference ceiling, isolated from normal inference.

Selection depends on held-out schedule quality, calibration, overhead, and
maintenance debt, not the smallest training loss. Preserve the simplest model
unless added complexity brings stable practical benefit. RL is not the initial
choice: it introduces exploration and validation demands before the physical
measurement system is reliable. Revisit only if the planning formulation fails
for a demonstrated reason.

## Literature checks still required

Existing research already studies changing workloads and learned cost models.
Neither three models nor MPC alone establishes novelty. The contribution must be
the measured maintenance-timing problem, action consequences, uncertainty handling,
and demonstrated benefit over strong scheduling baselines.

- Modeling Shifting Workloads for Learned Database Systems:
  https://doi.org/10.1145/3639293
- Rethinking Learned Cost Models: Why Start from Scratch?:
  https://doi.org/10.1145/3626769

These are related-work leads checked during inventory, not a complete novelty audit
or proof that the preferred architecture outperforms the three-model alternative.
