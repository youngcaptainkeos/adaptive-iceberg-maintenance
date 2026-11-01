# Prospective 48–72-hour feasibility decision

**Status: proposal for review; not authorization to change objectives, source, infrastructure or run physical experiments.** Prepared1November2026 from Main and exploring novelty, the learned-cost implementation plan and actual saved worker3 evidence. Existing negative/failed results remain unchanged. See recovery_and_feasibility_plan_2026-11-01.md for the currently authorized read-only queue.

## Research question and realistic deliverable

Can maintenance timing lower foreground interference or resource expenditure after including controller/feature/observer costs, beyond an inexpensive current-state policy, while completing the same required work and maintenance obligation? Three learned models are a candidate architecture, not a required answer or novelty claim.

A48–72hour effort can deliver an auditable engineering feasibility decision and pilot comparison, not promise statistical generalization or SIGMOD/VLDB acceptance. If only observer improvements are measurable, describe them as measurement engineering rather than learned scheduling.

## What existing evidence establishes

- Four no-maintenance storage-device arms: changing evidence storage reduced paired mean response31.1%/41.9%, principally outside SQL. Useful observer-path engineering evidence; no fitted scheduling comparison.
- Two queue complexity arms25October:3094queries each; mean response852.167s control and853.313s fixed600smaintenance. One15.113srewrite and14pending-layout observations. No clear latency benefit, no independent-block significance/equivalence; terminal layouts differ.
- First A/B SF1 training:335eligible queries,16A/319B, onefamily and confounded maintenance/layout support. Models frozen and exploratory.
- SF10 model campaign26October:0passed1failed5unattempted/no fit. Actual470client queries completed, but job1080 only archivedRUNNING/stage2080ACTIVE/no taskframe. Final joblist omitted1080 after full multiset validation. This is an evidence gap, not proven taskfailure/retry; failed status remains.

## Primary metric choice and guardrails

Do not select a metric because an old result looks favorable. Before new outcome use, choose and freeze one of these alternatives:

1. **Preserve the existing response-time focus:** mean/full-cohort summed arrival-to-result response primary; CPU core-seconds and I/O secondary. Report tails, drain time, completed/offered/failed/residual work and maintenance state separately.
2. **Prospectively change the resource objective:** total attributable CPU core-seconds for a completed workload and required rewrite primary, with a preregistered acceptable foreground-response regression. This is a new experiment objective, never a relabeling of old results.

CPU% is not CPU work; task elapsed time is not CPU time; host CPU is not controller attribution. Track nonoverlapping process/JVM CPU for the total, taskCPU as a breakdown only. Include actual observer/controller/maintenance work in the primary accounting boundary, with audit-only after-run validation charged and reported separately as a distinct phase. Do not add nested taskCPU to the enclosing processCPU. No watt-hour, cloud-price or SLA conversion without actual evidence and agreed units.

I/O secondary outcomes should separate logical scan bytes, physical-device traffic, shuffle/spill, rewrite and evidence-writing bytes. These quantities overlap and are not additive by default. Page-cache/cold-start conditions must be stated; services/cache must not be reset to manufacture a clean contrast.

Every policy must process identical offered queries and honor the same maintenance obligation, deadline and target-layout rule. Full drain or common-horizon/residual-debt semantics must be frozen consistently. A no-maintenance arm ending fragmented remains a diagnostic, not an equal-work efficiency winner. If natural time limits prevent completing maintenance, report failure/debt rather than assign an invented penalty or hide work outside the horizon. Same target-file-size rule need not produce byte-identical files; record actual output layouts and any comparison limitation.

User/research-team review must select the primary objective, minimum practically useful effect and tolerated response/debt regression before results. There is no evidentiary basis to invent these thresholds here. Development repeatability and actual whole-episode duration should determine feasible replication and precision; do not treat14pendingqueries as14trials.

## Gate A: reliable accounting, first 12–24 hours after approval

- Preserve current protocols, raw failures, models and consumed source registry.
- Implement a versioned prospective engine-evidence repair with fresh identities: archive complete terminal query/job/stage/task evidence before expensive final full-multiset scans; bound periodic archival using actual job churn/retention and measured observer cost. Never treat RUNNING/missing as SUCCEEDED, ignore retries, drop query markers or lower coverage/freshness/task gates.
- Keep originals untouched and shared resource locks. Admission requires no competing scientific run, sufficient observed disk/RAM budget and untouched required source/data hashes.
- Complete one real bounded correctness/evidence unit with the actual relevant query mix and source rows. Source windows and any fresh sample identities must be registered before outcomes; do not repeat until favorable. Failure of a new unit stops dependencies and is retained with ntfy.
- Register process/JVM/controller accounting and lifecycle boundaries; verify availability of counters, not assumed energy or cloud metrics.
- Verify genuine SQL-plan binding; retain plan cache/exact snapshot semantics and record cache misses. Query feature counts are not a hand-coded complexity score.

Pass condition: a complete independently auditable physical block with all declared work and measured boundaries. If unavailable after24hours, stop expanding models/scale and reconsider the measurement platform or the short-term scope.

## Gate B: overhead budget and action sensitivity, next 24 hours

Measure separately:

- First library import and model deserialization versus warm supported inference; persist model objects rather than assuming per-query loading.
- Feature acquisition and cache misses: actual metadata/EXPLAIN request lifetime, parsing, publication and availability waiting.
- Forecast and action enumeration/planning CPU and elapsed time at actual invocation frequency.
- Telemetry, logging and archive I/O/CPU, without subtracting guessed overhead from observed response.
- Offline training and refresh, amortized only over an explicit intended deployment volume.

Keep the historical inference microbenchmark scoped to its actual SF1models/development rows; it cannot establish costs of unfitted SF10boosting or the full live controller.

Before learned policy evaluation, establish that different permitted maintenance times have a practically useful effect under comparable initial layout, real source windows and required final maintenance. Use justified matched/reversed order on fresh tables. Candidate high/low-load windows are selected only from permitted development demand history, not after inspecting policy winners. Preserve full arrival spacing and query ledger; do not thin/compress an overloaded trace.

If evaluating a perfect-arrival-information ceiling, label it explicitly as an oracle using future mapped-benchmark arrivals, separate from all runtime inputs/training. It is not original SnowflakeSQL knowledge. An oracle cannot justify invented action-cost labels or bypass physical validation. If perfect arrival information cannot affect useful choices in the tested regime, a more elaborate forecaster is unlikely to rescue that regime.

## Gate C: complete policy comparison by 48–72 hours, if previous gates pass

Freeze strongest simple baselines first:

1. Fixed immediate/periodic timing with the same action eligibility and maintenance obligation.
2. Cheap current-state queue/load rule with development-only thresholds, hysteresis and bounded deferral.
3. Past-only persistence/seasonal forecast plus empirical query/layout costs.
4. The learned candidate in **the same planner/action set/invocation budget** as the empirical-cost comparator.

An information ablation should isolate forecasting from planning and isolate learned costs from medians. Different planners cannot automatically credit a learned estimator. Match compute budgets fairly and disclose greater aggregate capacity of separate A/B fits. Do not label a custom baseline AutoComp, NoisePage or another published system without faithful implementation.

Use whole source-overlap families/episodes with chronological development/evaluation separation; no random row split or reuse of consumed tests as fresh validation. Include supported/unsupported coverage and refusal behavior, target complexity diversity, observed transition costs and actual pending/engine overlap distinctions. One family per split is exploratory. Do not rush SF100 or a new storage format before supported-scale measurement works.

The final decision should report the primary metric, response/resource/debt guardrails, all episodes including failures/unattempted arms, controller overhead and differences relative to development repeatability. Pilot blocks may support a continue/pivot decision, not broad confidence/calibration claims.

## Stop, simplify or pivot

- **Measurement failure:** no complete auditable block by24hours -> prioritize reliable collection or reduce the declared research scope; do not weaken gates.
- **No action effect:** differences within development drift/precision or reversing across blocks -> current workload does not establish a useful timing trade-off.
- **ML has no marginal value:** cheap baseline matches learned candidate after all overhead -> retain simpler controller and drop learned-superiority claim.
- **Resource illusion:** apparent savings require less completed work, missing maintenance, lower quality or unacceptable response -> reject claimed efficiency.
- **Insufficient interference data:** maintenance observations confined to one episode/few rows -> no calibrated A/Binterference claim.
- **Forecast ceiling weak:** good arrival predictions do not change decisions/outcomes -> change the hypothesis rather than just the model.

Potential later branches include useful incremental maintenance, genuine ingestion/delete debt, partition prioritization or cross-format generalization. Each is a separate registered hypothesis with real provenance and engineering cost. Changing to Hudi/LSM merely to obtain a positive number is not a defensible shortcut.

## Novelty limits and sources reviewed by exploring novelty

Forecast-aware maintenance, resource budgets and transition-aware planning already appear in prior work. A plausible narrow hypothesis is an **overhead-budgeted external Iceberg controller with measured net resource savings while preserving foreground performance and maintenance completion**, beyond strong cheap baselines. This is not yet a demonstrated contribution.

- [AutoComp](https://arxiv.org/html/2504.04186v1): automated compaction and workload/resource considerations.
- [NoisePage](https://www.vldb.org/pvldb/vol14/p3211-pavlo.pdf): forecasting, interference modeling and planning.
- [SOPHIA](https://www.usenix.org/conference/atc19/presentation/mahgoub): future workload and reconfiguration/transition cost.
- [Bao](https://rmarcus.info/blog/courses/cis6500/16a_bao.pdf): optimization overhead and contention concerns.
- [Spark3.3.4TaskMetrics source](https://raw.githubusercontent.com/apache/spark/v3.3.4/core/src/main/scala/org/apache/spark/executor/TaskMetrics.scala): executor CPU/elapsed/spill distinction.

Primary sources and exact mechanism overlap need detailed paper review before any originality claim. This proposal does not claim an exhaustive novelty search, an accepted cost model, a scheduler or publication readiness.
