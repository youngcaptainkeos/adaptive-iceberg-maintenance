# Models, controller and improvement branches

## 1. Keep the architecture flexible

The architecture is a measured decision loop: **observe the queue and table → estimate the consequence of waiting or starting maintenance → choose among admissible actions → measure the actual outcome**. The research is about better decisions, not preserving a fixed number of models.

The current A/B/C idea can fit within that loop:

| Component | Meaning | Required target and evidence | Keep only if |
|---|---|---|---|
| A | Query client service during the registered maintenance-pending state | Actual service duration with pre-decision features; separately measured engine overlap | Separate modelling improves held-out decisions over a shared model |
| B | Query client service without that pending state | Same target and features with supported state coverage | It adds value beyond query/layout medians |
| C | Future offered request counts or verified query-class counts | Actual future arrivals from complete source trace windows | It improves timing decisions beyond persistence/history rules |
| Rewrite estimator | Duration and layout transition of a specific eligible rewrite | Genuine complete rewrites, input manifest and output evidence | Its error changes decisions enough to matter |
| Planner | Compare admissible start/wait sequences under the same obligation | Frozen action set, queue semantics and validated model inputs | Its net response/resource gain exceeds full controller overhead |

A/B labels currently refer to observed client state. They are not causal labels of physical contention. Forecast request counts are not forecast CPU load. Post-compaction layout benefit and rewrite duration are different targets; do not silently fold them into an A/B service-time prediction.

## 2. Baseline ladder

Compare methods by replacing one component at a time while holding the action set, workload, planner and required maintenance fixed.

1. **Fixed timing:** registered early/middle/late starts. These establish action value and include operationally sensible periodic timing.
2. **Reactive queue rule:** start below a development-selected backlog threshold with hysteresis and bounded deferral. Register the obligation/deadline that prevents indefinite waiting. If no feasible start is available, report the failure or explicit abstention; do not silently change the obligation.
3. **Simple predictive rule:** persistence/history count estimate plus query/layout medians and a measured rewrite-duration baseline, using the same planner as learned variants.
4. **Learned demand only:** replace C; retain median costs.
5. **Learned costs only:** retain the simple demand forecast; replace query/rewrite estimators.
6. **Combined model:** learned demand and costs. Add a calibrated uncertainty variant only after sufficient independent calibration data exists.

No-maintenance is a diagnostic lower-work reference. A future-arrival oracle is an information diagnostic using the actual later arrivals; label it as unavailable online. It is not a deployable baseline and it does not provide unmeasured counterfactual execution costs or a true global optimum.

## 3. Features and leakage boundaries

| Feature family | Candidate inputs available before the action | Excluded or separately treated |
|---|---|---|
| Query | Template, join count/type, aggregation/sort, referenced tables, filter/range shape, planning-time estimates where actually captured | Actual rows scanned, final task duration, resulting plan metrics only known after execution |
| Table/layout | Rows/bytes from verified available metadata, file count, size distribution, partition statistics and eligible rewrite set | Post-rewrite file count or future snapshot chosen from an observed outcome |
| Queue | Actual backlog, oldest pending age, known waiting query classes, recent completed service summaries | Future completion times or future backlog |
| Host | Lagged valid CPU/I/O/memory observations with availability timestamps | Measurements acquired or published after the decision; zero-filled missing windows |
| Demand | Past offered counts, complete recent intervals, time/calendar features supported by the trace | Future counts, mixed train/test history, synthetic replacement traffic |
| Rewrite | Eligible input files/bytes, action/options, current resource state | Actual output bytes/duration used as predictors |

Structural query complexity is useful because the same arrival count can represent different amounts of work. Add it in an ablation: template/layout median → structural features → queue/host history. A large query is not automatically a slow query; measured execution plans, selectivity and cache behaviour matter. Keep a simple template feature so a complex structural representation must justify its overhead.

Our Snowset mapping provides real arrival timing paired with benchmark SQL. It does not recover the original private Snowflake SQL. A known round-robin benchmark mapping may let an experiment predict the next template, but that is a benchmark-specific assumption and must not be presented as general production query forecasting.

## 4. Bounded model search, after data readiness

These are proposed search spaces, not parameters used in a new fit today. Register the chosen grid before fitting and select only on development families.

| Target | First candidates | Bounded development options | Reason to avoid a larger search now |
|---|---|---|---|
| Query service | Query/layout median; log-Ridge; shallow histogram gradient boosting | Ridge alpha `{0.1, 1, 10}`; tree depth `{2, 4}`, minimum leaf rows `{20, 50}`, learning rate `{0.05, 0.1}`, 100 iterations fixed: eight tree configurations | Existing independent state coverage is too small for rich models |
| Shared versus A/B | Same feature set, shared state indicator/interactions versus two fitted estimators | Match total search budget and report total parameter capacity/training cost | Two models can appear better simply because capacity or selection effort doubled |
| Rewrite duration | Overall/size-binned median, simple bytes/file regression | Very small regularized model; bins must be chosen on training support | Four or a few rewrites cannot identify a complex cost surface |
| Request counts C | Persistence, recent-window mean, supported seasonal estimate, then a shallow count regressor | Past-window/horizon choices tied to measured rewrite duration and trace coverage; no unrestricted deep sequence sweep | Better count MAE may not improve a maintenance decision |
| Optional later nonlinear comparator | Extra Trees or another small tree ensemble | One preregistered bounded capacity/search budget | Additional libraries/models are not contribution by themselves |

For all candidates record training source families, complete feature availability, target units, transforms, package versions, random seed, exact grid, selection metric and serialization hashes. Imputation of genuinely unavailable evidence is not allowed; restrict the supported feature contract or fail/abstain explicitly.

Important modelling detail: exponentiating a prediction trained on log-duration does not automatically estimate arithmetic mean service time. Likewise, a median/MAE-optimal predictor is not necessarily the expected cost needed by a queue planner. Choose the training loss and any training-only back-transform correction for the quantity the planner needs. Report both predictive diagnostics and actual decision outcomes. Do not hide systematic underprediction with an unregistered post-test adjustment.

Minimum leaf rows are numerical regularization, not an independence guarantee. Fifty queries from one episode are still one highly related context. Do not start this grid until there are complete, admissible episodes across the states/layouts of interest and separate development families. Preserve historical frozen models and evaluations; never overwrite them with a new fit.

## 5. Candidate controller contract to implement next

The prospective controller is deliberately small: when a rewrite is eligible, choose **start now** or **wait until the next registered decision time**. A bounded obligation determines whether further waiting is admissible. We do not introduce an invented weighted CPU/SLA reward.

At each decision:

1. Freeze a state record and the availability frontier of every feature. State includes the actual FIFO backlog and verified snapshot/layout.
2. Check that the frozen model bundle supports the observed state. Unsupported input is an explicit abstention with a reason, not a hardcoded prediction or concealed fallback.
3. Evaluate the same bounded action candidates for every compared method. A predicted scenario is labelled as a prediction and can never become an observed training label.
4. Account for predicted rewrite interference, duration, later layout benefit and all already-offered queued work. Forecast demand supplies future work, not a fabricated CPU measurement.
5. Choose the feasible action with the registered response objective and guardrails. Log candidate scores, uncertainty if valid, action, decision time, complete overhead and binding model/protocol hashes.
6. Execute once under the physical runner. Never cancel running queries or maintenance to improve an outcome. Audit the complete cohort and obligation independently.

Before live use, validate queue accounting and snapshot semantics against genuine saved complete episodes. Predictions on an alternative action remain unobserved counterfactuals until a separate matched physical arm actually executes that action. A replay simulation alone cannot prove the new policy's benefit.

There is **no accepted live learned controller in the new research package**. Its current contribution is plan generation and supplementary evidence accounting. Runtime integration is a subsequent gated implementation unit.

## 6. Improvements ordered by likely value

| Route | Why it could improve a real metric | First decisive experiment | Cost/priority | When to drop it |
|---|---|---|---|---|
| Better start time | Avoid contention while real backlog is high | E05–E06 | Highest, after attribution repair | Start times have a precise negligible effect |
| Better file size/layout | Reduce file overhead without destroying parallelism | E03–E04 | High; isolate from timing | No robust query/resource improvement or target already near optimum |
| Cheap predictive scheduling | Use a real quiet interval before backlog grows | E10–E11 | High if timing opportunity exists | Simple reactive timing is as good within useful precision |
| Query complexity awareness | Distinguish few expensive queries from many cheap queries | E04/E12/E15 | Medium | Features add cost but not held-out action value |
| Separate A/B states | Represent different service regimes | E13 | Medium, data dependent | Shared model or medians are equally effective |
| Rewrite estimation | Avoid choosing quiet intervals shorter than the rewrite | E14 | Medium | Simple bytes/duration baseline already makes the same decisions |
| Whole-controller/observer reduction | Reduce actual overhead already visible in historical engineering runs | E08/E33 | High for necessary cleanup, bounded effort | Change is cosmetic or does not affect end-to-end measurements |
| Incremental/file-group compaction | Limit interference by doing smaller beneficial units | E23 | Medium/high implementation effort | More repeated I/O exceeds saved interference or semantics unsupported |
| Partition priority | Spend maintenance work on the partitions queries actually use | E24 | Later, needs relevant partitioned workload | The initial workload scans everything uniformly |
| Continuing writes/debt | Create a genuine ongoing maintenance need | E22 | Later, substantive new contract | Available input has no verified write trace or correctness support |
| Resource-aware admission/budget | Reduce CPU/I/O peaks or total work for the same obligation | E09/E19 | Later after complete counters | Only instantaneous load looks better; total work/response deteriorates |
| SF100 | Test whether a demonstrated mechanism survives larger data | E20 | Expensive transfer, not first rescue | Capacity/time is insufficient or no SF10 mechanism exists |
| Delta/Hudi | Test portability or a different maintenance mechanism | E27/E28 | High, separate adapter and semantics | Migration consumes the project without testing a specific hypothesis |
| RocksDB/LSM | Explore a different compaction setting with stronger ongoing debt | E29 | New research direction | Team cannot afford new baseline/system expertise |

Caching, materialized views, query rewrites, engine settings or storage placement could improve database performance. They are separate interventions. Freeze them during timing comparisons. If one becomes the primary research route, document the new question and baselines instead of attributing its gain to the learned scheduler.

## 7. A clear rule for every future task

Before implementing a component, fill in this sentence:

> This changes **[one mechanism]**, which may improve **[one measured outcome]**, under **[specified conditions]**. We will compare it with **[baseline]**, measure **[complete boundary]**, and stop pursuing it if **[registered result]**.

For correctness infrastructure, the outcome link can be indirect but explicit: “this repairs a known missing ownership link needed to measure response during compaction.” It cannot be “this makes the system more advanced.” Limit infrastructure work to what unlocks the next valid experiment. Do not build a bigger dashboard, add more models or optimize a tiny inference call while the main uncertainty is whether maintenance timing changes the real outcome.

Keep a weekly table of expected metric impact, decisive next evidence, engineering effort and actual outcome. If a task has no plausible impact path or does not reduce a blocking uncertainty, move it out of the active queue.
