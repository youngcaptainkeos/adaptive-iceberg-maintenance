# Cost-model candidate implementation

The existing physical A/B trainer now accepts an optional preregistered
`model_candidates: ["separate", "shared_action_conditioned"]` in its training
protocol. Absence preserves separate A/B behavior. The shared estimator uses the
same measured features plus measured compaction-active state, training split,
hyperparameters and seed. It estimates query service latency under observed
states; it does not predict the causal consequence of a deferred schedule.

Raw timing/engine labels, independent chronological splits, purge, query coverage,
independent rewrites and finite whole-experiment conformal ranks remain required.
Every separate and shared regime/query cell must pass the existing accuracy,
training-median improvement and empirical coverage gates before any bundle is
published. Output includes comparison metrics and a shared-model artifact; there
is no automatic winner or scheduler deployment. If either candidate fails, the
bundle is refused, and the failure must be retained in the experiment ledger.

No current diagnostic pilot or null-control data is accepted training data.
Common-horizon cost export, valid offered/queue workload accounting, independent
collection and justified acceptance precision are still dependencies. Total
latency, maintenance work and remaining debt require separate measured outcomes;
no arbitrary scalar objective or fixed deferral cost is introduced here.
