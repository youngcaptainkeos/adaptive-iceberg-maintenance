# Research strategy and execution sequence

## 1. The decision we should study

Focus on a fixed maintenance action: rewriting eligible small Iceberg data files into a registered target layout. The controller chooses its start time while real benchmark queries arrive. The foreground cohort and the maintenance obligation are identical across timing policies. The initial question is deliberately smaller than joint tuning of file size, partitioning, query routing, concurrency, ingestion, model architecture and scheduling.

The primary research question is:

> Under which workload and layout conditions can an external Iceberg controller reduce full-cohort query response time by choosing when to compact, after including its own overhead and completing the same maintenance work?

The second question is conditional:

> When does predictive information improve this decision beyond a current-queue rule and empirical costs?

This ordering matters. A highly accurate model cannot create a useful action where the engine has little sensitivity to that action. Conversely, a cheap rule that delivers a clear measured gain is a better project outcome than a complex model with a lower offline error and unchanged query response.

Do not require all A/B/C models to survive. A useful final system could use empirical layout costs, one demand forecast and a small timing rule. A more capable shared latency model can replace separate A/B models if its additional value is demonstrated. Learned rewrite duration is justified separately by real rewrite observations.

## 2. Starting evidence and its implications

These are saved historical results, not live server observations on 13 November.

| Evidence | What it supports | What it does not support |
|---|---|---|
| SF1 cost corpus: 18 episodes, 9,923 query and 12 rewrite labels, three source families | A functioning evidence/export and exploratory cost-comparison path | Large independent calibration, broad generalization or scheduler advantage |
| Reserved SF1 result: query/layout median MAE 20.3430 ms; tree 20.9283; query median 21.2335; log Ridge 21.5426 | A simple estimator was the strongest of these frozen comparators on that reserved family | A reason to retune using that test family, or a universal claim that ML cannot help |
| Later A/B development fit: 335 complete-history rows, 16 A and 319 B, one family | Candidate model artifacts and an explicit support problem | Causal interference, robust A-model accuracy or calibrated uncertainty |
| Eight-arm timing feasibility study, 24,752 queries | An earlier end-to-end timing platform and useful limitations | Reliable scheduling superiority or eight independent workload families |
| Four storage-location arms, 12,376 total queries, two reversed-order pairs | Large observer/client-path sensitivity: historical response reductions about 31–42% | Faster SQL by that amount, learned policy benefit, independent-day significance |
| Separate SF10 capability: 64 files became 4 | Real compaction and verified larger data are available | A beneficial timing policy or a faster full workload |
| Latest archive03 SF10 parent: 0 passed / 1 failed / 1 unattempted | A preserved measurement failure | Accepted SF10 training data |
| Post-hoc diagnostic: 463 exact SQL matches, 308 directly owned rejected-job links | Strong evidence for fixing the attribution mechanism prospectively | Retroactive acceptance or complete task/counter certification |

Pointers: `docs/feasibility_decision_proposal_2026-11-01.md`, `docs/daytime_review_2026-10-14.md`, `docs/learned_cost_model_implementation_plan.md`, `results/queue_storage_sql_20261024/analysis/result.json`, `results/sf10_archive_validation_20261101_03/result.json` and `results/sf10_sql_ownership_diagnostic_20261111_01/result.json`. Exact input pins for the new local accounting regression are recorded separately in its registration.

The strongest current explanation is not yet “our models are too slow.” The evidence identifies observer/client overhead, source saturation, sparse maintenance exposure, layout/time confounding and incomplete SF10 attribution. Each can hide or eliminate a timing effect. They need different experiments.

## 3. Freeze these choices first

Use Spark/Iceberg on worker3 and verified SF10 as the main platform. Keep the existing supported six SQL templates for the first engineering comparison. Use intact verified Snowset arrival windows with an explicit benchmark SQL mapping. Keep one foreground client for the initial mechanism study, then examine concurrency separately. Keep static logical data and one required rewrite before adding continuing writes.

Treat file layout as an experimental intervention, not an environmental accident. Requested file counts are preparation targets; only actual verified counts/distributions enter analysis. Do not call controlled fragmentation natural ingestion. Keep encoding, row-group settings, partitioning and sort recipe fixed while changing file granularity, or explicitly acknowledge the bundled intervention if that is not achievable.

Use the faster already supported working-evidence path in the new registration, preserving durability and audit semantics. Record its costs. Do not repeat the old evidence-device comparison merely because it gave an attractive number.

Do not reopen consumed SF1 tests. Existing source windows remain engineering/development material. Before claims about new families, inspect overlap across source timestamps, warehouse identity, feature history, forecast training range and previously consumed outcomes. Repeated runs on the same arrivals can estimate execution noise; they do not add independent demand diversity.

## 4. First 72 hours of actual available work

This is an effort sequence beginning when worker3 is available, not a promise to finish despite failed gates or unavailable hardware. No expired November 2 cutoffs are reused.

| Window | Work | Deliverable | Continue condition |
|---|---|---|---|
| First 2–4 focused hours | E00: inspect active processes/locks, recover exact source/raw/Git state, freeze status and available sources | Evidence/consumption inventory and fresh task registration | No conflicting physical executor; usable input/capacity evidence |
| Remainder of day 1, up to day 2 cap | E01: implement prospective exact SQL/job archival; replay retained genuine evidence; fresh control/maintenance verification | Complete terminal raw block, independently audited | Every old gate plus direct ownership and explicit counters passes |
| Next available collection slots | E02 and E08: small null repeatability pilot and observer accounting | Null drift and overhead budget | Differences can be interpreted; observer path is not the dominant uncontrolled variable |
| By the end of the feasibility window if gates allow | First E03/E05/E06 development contrasts | Layout benefit, transient interference and early/deferred timing evidence | A useful physical effect or a precise, documented reason to narrow/change the hypothesis |

If engineering consumes the whole window, the honest output is an engineering readiness decision. Do not claim model feasibility from it. If two working days cannot establish a trustworthy fresh comparison, stop adding model/scale work and review measurement scope. Do not schedule 30 follow-on experiments while the first required evidence is unavailable.

## 5. Main research path after feasibility

### Phase I — explain the opportunity

Run E03–E07. First vary one factor at a time to identify a mechanism, then use the bounded interaction screen. One-factor studies alone cannot identify timing-by-load or timing-by-layout interactions, so do not stop at a collection of isolated means.

Ask three questions in sequence:

1. Is a compacted layout beneficial for the query population at all? A reduced file count is insufficient.
2. Is maintenance execution itself disruptive, with direct observed overlap and controlled snapshot/layout semantics?
3. Does moving its start time improve the full workload after the same action eventually completes?

Only the third establishes room for a timing controller. If layout improves queries but all start times are equivalent, a simple layout-maintenance rule may be appropriate. If layout does not help but maintenance is mandatory for another evidenced reason, frame the problem as minimizing disturbance subject to that explicit obligation. Do not invent such an obligation to rescue a failed result.

### Phase II — strongest inexpensive method

Run E10. Fixed starts and a bounded reactive queue/load rule are required baselines. Tune on development only, with the same action eligibility, cadence, deadline and target layout as the later model. Include actual decision overhead and submission lag.

A reactive rule must not win by deferring maintenance forever. A deadline policy must not be penalized by ending measurement before its rewrite finishes. The protocol records common offered work, completion, drain and terminal maintenance state.

### Phase III — information and models

Run E11–E17 only if timing is actionable. Use a fixed planner to isolate the forecast and cost estimator. Compare persistence/seasonal prediction with a learned forecaster only if forecast information is useful. Compare medians with a small learned cost model only if prediction differences produce useful action disagreements. Study A/B separation only if both states have adequate independent support at comparable layouts.

Do not evaluate every model family on physical hardware. Use development-only offline elimination, retain a small number of candidates, then physically test the selected method and the strongest inexpensive baseline. Any simulator is a development model with measured discrepancy; it cannot supply physical labels or replace the held-out real comparison.

### Phase IV — confirmation and publication

Before E18, freeze the claim, primary metric, practical margin, power/precision design, folds, model artifacts, baseline settings, policy, source families, arm order, accounting boundary and analysis code. Score the reserved physical comparison once. Failure and inconclusive findings are valid outcomes. A test-set revision consumes that test; future confirmation needs a new source/data role.

Then choose the smallest external-validity extension that challenges the central mechanism: SF100, higher concurrency, a richer SQL mix, a second environment, or real continuing writes. Do not change all of these together. A paper usually needs one or two meaningful extensions, not a catalogue of incomparable demonstrations.

## 6. Practical schedule and workload limits

A plausible planning range is **one week for a credible feasibility decision**, followed by **several weeks for a defensible study**, assuming server availability and passing gates. A top-tier submission is a research objective, not something this schedule guarantees.

| Phase | Planning effort | End condition |
|---|---:|---|
| Reliable measurement and diagnostic comparisons | 2–5 working days | Complete auditable physical blocks and measured action sensitivity |
| Regime isolation and strong baseline | 3–5 days plus collection | Narrow mechanism, fixed baseline and measured repeatability |
| Candidate fitting and component ablation | 3–7 days plus collection | Supported marginal value, or a deliberate simplification |
| Fresh confirmatory collection and analysis | 1–2 weeks, precision dependent | Frozen test completed and all attempts accounted for |
| External validity, writing and artifact | 1–2 weeks | Reproducible claim, limitations and team/guide review |

These ranges overlap only where work is independent. One physical executor owns worker3. Other team members can write literature/analysis, inspect retained code, and prepare figures; competing load changes the experiment.

Calculate wall time from measured episode duration, preparation, validation, copy and failure rate. For illustration only, 48 episodes at 60 minutes each require 48 serial machine-hours before setup; those are arithmetic planning inputs, not observations or a promise. The CLI accepts your actual measured duration. Full drain can be much longer than the arrival horizon under saturation.

A broad ten-factor Cartesian product in the registry contains **29,160 cells before repetitions**. At one hour per cell and three repetitions it would exceed 87,000 machine-hours. That is why the programme explicitly documents the possibilities but executes only gated small designs. “Every combination” is a map of the search space, not a sensible experimental schedule.

## 7. Metric-driven stopping rules

Every proposed code change must answer: which metric, which mechanism, which experiment, what baseline, and what observation would make us stop?

- Measurement repairs unblock trustworthy comparisons. Once requirements pass, stop redesigning instrumentation unless a measured overhead/correctness issue affects the objective.
- If the timing effect is smaller than the achievable precision/practical margin, do not add a larger neural model.
- If a learned component improves MAE but not decisions or physical outcomes, keep the inexpensive component.
- If overhead costs more response than a timing choice saves, reduce invocation/feature cost in a new controlled unit or drop that component. Never subtract guessed overhead from an observed result.
- If the only gain comes from less completed work or missing maintenance, reject it.
- If CPU/I/O is a stronger hypothesis, preregister E19 before collecting its confirmatory outcomes. Historical exploratory observations can motivate it, not confirm it.
- If the mechanism varies by layout/query/load, narrow the claim to a useful supported region and test that region on fresh sources. Do not select test winners after the fact.
- If neither timing nor a justified new action has a useful effect, pursue E32 only if adequate precision and explanatory novelty are achievable. Otherwise report that the current hypothesis is unsupported and revise the project with the guide.

## 8. Team ownership

Suggested work split, to be agreed internally: one owner for collector/correctness and physical execution; one for workload/source registry and metrics/statistics; one for forecasts/costs and offline ablations; one for literature, result visualization and reproducibility. All four should be able to explain the primary metric and the current failed/unaccepted state. The physical owner alone starts experiments. The Git/methodology owner integrates reviewed changes and records exact hashes. Read-only review can proceed in parallel, but no competing collection or silent source-window reuse is allowed.
