# Experiment catalogue

Version: 13 November 2026. Every card below is **planned**, not an executed result. Dependencies are research gates; the machine-readable registry does not grant launch authority. See the main roadmap for branch choice and budget.

| ID | Experiment | Prerequisites |
|---|---|---|
| E00 | Recover and freeze the evidence inventory | None |
| E01 | Repair prospective SQL ownership and terminal evidence | E00 |
| E02 | Measure repeatability with null controls | E01 |
| E03 | Measure the static layout response curve | E02 |
| E04 | Isolate query sensitivity to layout | E03 |
| E05 | Separate transient interference from permanent layout benefit | E02 |
| E06 | Establish a useful start-time decision | E03, E05 |
| E07 | Screen the interactions that can explain timing benefit | E06 |
| E08 | Account for the whole observer and controller overhead | E02 |
| E09 | Build resource accounting before claiming efficiency | E01 |
| E10 | Establish strong cheap policies | E06, E08 |
| E11 | Test whether forecast information changes useful decisions | E10 |
| E12 | Test learned costs against empirical costs | E10 |
| E13 | Decide whether separate A/B models are necessary | E05, E12 |
| E14 | Estimate rewrite duration and layout transition | E03, E09 |
| E15 | Remove unnecessary features and tune within development | E12, E13, E14 |
| E16 | Calibrate uncertainty only with adequate blocks | E12, E14 |
| E17 | Isolate the value of C, learned costs and uncertainty | E11, E12 |
| E18 | Freeze and execute the one-time confirmatory comparison | E17 |
| E19 | Optional CPU or I/O objective study | E09, E10 |
| E20 | Validate scale transfer to SF100 | E18 |
| E21 | Concurrency and query-mix transfer | E18 |
| E22 | Add continuing fragmentation from real writes | E06 |
| E23 | Selective or incremental file-group compaction | E06, E14 |
| E24 | Partition prioritization | E22, E23 |
| E25 | Delete-file maintenance and merge-on-read | E22 |
| E26 | Second environment or engine | E18 |
| E27 | Delta Lake external-validity branch | E18 |
| E28 | Hudi merge-on-read branch | E22 |
| E29 | RocksDB/LSM pivot | E06 |
| E30 | Robustness, drift and unsupported states | E18 |
| E31 | Write and release a reproducible paper artifact | E18, E30 |
| E32 | Boundary or negative-result research branch | E03, E05, E06, E08 |
| E33 | Observer-efficiency engineering branch | E02, E08 |

## E00 — Recover and freeze the evidence inventory

**Question.** Which results, processes, sources and tests actually exist, and which source windows are already consumed?

**Change.** Read current local and worker3 state when available. Inventory input hashes, snapshots, family use, frozen code and every failed/unattempted arm. No SQL or replay.

**Hold fixed.** All historical result statuses and raw bytes. The November 1 failed campaign remains 0 passed / 1 failed / 1 unattempted.

**Required evidence.** Git/process inventory; signed source/consumption map; raw-copy SHA receipts; explicit unknowns.

**Continue when.** Repository state, evidence paths and source roles agree; no competing physical executor.

**Stop or revise when.** Remote state is unknown, evidence is missing, or another scientific executor owns the server. Continue documentation only.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E01 — Repair prospective SQL ownership and terminal evidence

**Question.** Can every completed marked SQL call be linked to its actual SQL execution, jobs, stages and successful task attempts without guessing?

**Change.** Add a versioned SQL REST archive to the prospective collector. Resolve exact marked SQL and explicit success/running/failed job lists; preserve all observed engine jobs for the foreign-work census. Capture before retention loss and before post-run validation SQL.

**Hold fixed.** Existing freshness, telemetry coverage, raw publication, terminal capture, task-attempt, correctness and multiset gates; old failed episodes; verified SF10 source and six SQL templates.

**Required evidence.** Saved genuine 463-call diagnostic as regression evidence; terminal SQL/job/stage/task receipts for one fresh control and one fresh maintenance episode; independent counter-presence audit.

**Continue when.** Both fresh episodes pass every original gate plus direct ownership coverage, input hashes and terminal raw mirroring.

**Stop or revise when.** Any missing or ambiguous link, adverse counter, incomplete task attempt, capture gap or audit failure. Diagnose and register a mechanism change before another physical attempt.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E02 — Measure repeatability with null controls

**Question.** How much do response time and collection overhead drift without compaction or policy changes?

**Change.** Run two fresh-table no-maintenance replicas per development source block, alternating early/late position across a bounded four-block engineering pilot.

**Hold fixed.** Rows, mapped arrivals, SQL sequence, layouts, client concurrency, engine configuration, observer and warmup. No cache flush or service restart.

**Required evidence.** Full-cohort response, service, generator lateness, queue area, CPU/I/O availability, wall time and host context for all eight episodes; paired null differences.

**Continue when.** Complete auditable runs and a measured variance/drift estimate sufficient to choose later precision and meaningful-effect criteria.

**Stop or revise when.** Differences remain dominated by observer stalls or uncontrolled host changes. Fix measurement; do not use four blocks as a publication sample-size guarantee.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E03 — Measure the static layout response curve

**Question.** Does changing file granularity improve the queries we actually execute, and where does reduced parallelism offset file-opening savings?

**Change.** Prepare the same verified SF10 rows into three preregistered physical layouts, provisionally 16/64/256 files, with actual file-size distributions recorded. Execute identical queries without concurrent maintenance.

**Hold fixed.** Data content and ordering recipe, compression, row-group settings, partition/sort rules, query parameters and resource configuration. Rotate layout order; use fresh tables.

**Required evidence.** Per-query and full-cohort response, scan tasks/bytes, planning evidence where available, actual file distributions and logical equality. Record successful achieved counts; never pretend requested count equals actual count.

**Continue when.** A reproducible useful region or a well-measured non-monotonic curve exists; select the layout range on development only.

**Stop or revise when.** No plausible query benefit beyond repeatability, or layouts cannot be matched except for the intended intervention. Avoid training a predictor of a nonexistent benefit.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E04 — Isolate query sensitivity to layout

**Question.** Which query mechanisms are sensitive to file granularity: selective scans, full scans, joins or aggregations?

**Change.** First analyze the registered six real SQL templates separately on the same layout experiment. Add a separately registered richer query suite only after the initial mechanism is understood.

**Hold fixed.** Arrival counts/order within each comparison and exact query parameter sets. Do not simultaneously change data scale, selectivity, join count and concurrency.

**Required evidence.** Query/plan identities; scan, exchange, join and aggregate counts; measured per-template effects and uncertainty across blocks; a workload-weighted effect using a declared mix.

**Continue when.** Specific sensitive and insensitive query classes can be explained with physical evidence, including any slowdowns.

**Stop or revise when.** Only a selected favorable template improves and aggregate effects disappear. Restrict the claim or revise the workload question prospectively.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E05 — Separate transient interference from permanent layout benefit

**Question.** Does maintenance execution overlap actually slow foreground work, separately from the new layout becoming visible?

**Change.** Use fresh matched tables and snapshot-pinned foreground reads of the original layout during control and rewrite episodes. Record actual overlapping task intervals. In a separate phase compare compacted reads without maintenance.

**Hold fixed.** Original read snapshot, query cohort, engine capacity, observer and arrival timing during the interference contrast. Snapshot pinning is diagnostic; production-like latest-snapshot semantics are evaluated separately.

**Required evidence.** Query task overlap, client-pending state, rewrite job CPU/I/O, response decomposition and actual commit/snapshot timestamps. Both no-overlap and overlap observations retained.

**Continue when.** A repeatable transient interference signal exists in a supported regime, or evidence establishes that it is too small to justify a separate interference model.

**Stop or revise when.** A-minus-B estimates merely combine layout/cache/time changes; no direct overlap proof; or observed slowdown is entirely dispatch/evidence overhead.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E06 — Establish a useful start-time decision

**Question.** Can choosing a different compaction start reduce full-cohort response while completing the same maintenance obligation?

**Change.** Compare fixed early, midpoint and post-arrival starts on identical offered cohorts; default proposed offsets 0, H/2 and H, with H=1200s only if a new registration justifies retaining it. All arms must complete one equivalent rewrite and all foreground queries.

**Hold fixed.** Initial physical layout, source window, SQL sequence, target layout rule, resources and observer. Include actual submission lag; intent time is not execution time.

**Required evidence.** Three-way paired response, queue area, p95/p99, drain, CPU/I/O and final maintenance state. A no-maintenance arm may be a separate diagnostic, never an equal-obligation winner.

**Continue when.** Start-time effects exceed development drift and the preregistered practical threshold; the sign/regime is interpretable across development blocks.

**Stop or revise when.** Timing has no resolvable effect, or all timings are equivalent within the stated margin. Stop the forecast/ML chain in this regime.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E07 — Screen the interactions that can explain timing benefit

**Question.** Does the useful timing choice depend jointly on natural demand regime, fragmentation and query mechanism?

**Change.** Run a bounded 2x2x2x2 screen: lower/higher verified fragmentation, lower/higher natural-load source strata, lighter/heavier declared query mix and early/deferred start. Use intact real arrivals; select strata from development source descriptors, not observed winners.

**Hold fixed.** SF10, same engine/resources, one client and fixed target-file rule. Load is a sampled source regime, not a randomized manipulated factor; report its association and interactions accordingly.

**Required evidence.** All 16 planned cells per replication set, actual source-family map and counterbalanced order, effect plots for timing-by-layout, timing-by-load and timing-by-query mix.

**Continue when.** A small number of repeatable interactions support a narrow timing hypothesis and a restricted feature set.

**Stop or revise when.** Interactions are dominated by noise, incomplete cells or unrealistic saturation. Do not expand to an unrestricted Cartesian product.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E08 — Account for the whole observer and controller overhead

**Question.** How much of measured response and CPU comes from feature acquisition, logging, durable publication, model inference and planning?

**Change.** Instrument non-overlapping controller spans and process counters; compare two semantically equivalent implementation paths only where every evidence guarantee is retained. Reuse the completed SF1 inference diagnostic as historical context, not a whole-controller estimate.

**Hold fixed.** Real queries, physical layout, logging durability and cadence, telemetry gates, model outputs and policy decisions in an implementation comparison.

**Required evidence.** Cold load versus warm inference, cache hits/misses, EXPLAIN/metadata calls, serialization/fsync, CPU-core-seconds, bytes and total client/engine time. Report inclusive/exclusive boundaries explicitly.

**Continue when.** End-to-end overhead is measured and small relative to the useful action effect, or an engineering optimization reduces it without changing semantics.

**Stop or revise when.** A claimed gain exists only after subtracting guessed overhead or weakening collection. Keep the gain as observer engineering if policy is unchanged.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E09 — Build resource accounting before claiming efficiency

**Question.** Can total CPU and I/O for the same work be measured without double counting?

**Change.** Capture disjoint process/JVM CPU counters with process start identities, and scoped physical I/O where available, across collection, drain, maintenance and validation phases.

**Hold fixed.** Same hardware, completed requests and rewrite obligation. Task CPU is a breakdown inside JVM CPU, not another quantity to add.

**Required evidence.** Counter availability/reset audit, accounting boundary, host interference log, summed CPU core-seconds, logical scan/rewrite bytes, physical I/O and observer costs in separate columns.

**Continue when.** Counters cover all relevant processes/phases with explicit scope and unchanged workload completion.

**Stop or revise when.** Only CPU percent or unscoped host/device counters are available. Report those as diagnostics and do not infer CPU work, energy or cost savings.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E10 — Establish strong cheap policies

**Question.** How much can a simple current-state rule achieve without any learned prediction?

**Change.** Implement fixed early, fixed deadline and reactive queue/load threshold policies with bounded deferral, hysteresis and identical rewrite eligibility. Tune the reactive threshold on development only.

**Hold fixed.** Same trigger opportunity, action set, target layout, deadline, resource budget and measurement path; enforce natural completion and record misses.

**Required evidence.** Physical paired full-cohort outcomes and overhead versus fixed starts. Report every threshold tried on development and freeze the chosen baseline before test.

**Continue when.** The strongest cheap baseline is selected transparently and reproducibly.

**Stop or revise when.** A baseline is deliberately weak, misses its maintenance obligation, uses a different action set or is tuned on held-out data.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E11 — Test whether forecast information changes useful decisions

**Question.** Does knowing near-future demand help beyond current queue/load state?

**Change.** Use one planner and empirical costs with reactive/no forecast, last-window persistence, historical seasonal rate and a separately labelled perfect-arrival-information diagnostic. The oracle may use only the benchmark arrival future, not unseen physical cost outcomes.

**Hold fixed.** Planner, action set, costs, cadence, overhead accounting and real offered arrivals. No retiming, thinning or stochastic synthetic demand substitution.

**Required evidence.** Forecast count errors, exact decision disagreements, supported horizons, physical response/obligation outcomes and oracle scope.

**Continue when.** Forecast information changes decisions and the physical outcomes improve beyond the cheap baseline; then justify learning C.

**Stop or revise when.** Good forecast scores do not change decisions, or even the diagnostic oracle has little useful action margin in the evaluated regime.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E12 — Test learned costs against empirical costs

**Question.** Does a learned latency estimate improve decisions beyond query/layout medians?

**Change.** Compare train-only query median, query/layout median, conditional median, log Ridge and a small boosted-tree candidate under the same whole-family splits. Use the same planner to test the selected candidate against medians.

**Hold fixed.** Training population, feature availability, held-out queries, forecast, planner and per-candidate tuning budget. Saved October models/tests remain consumed.

**Required evidence.** All-row coverage, common-support equal-episode errors, supported decision disagreements, warm/cold overhead and independent physical policy contrasts.

**Continue when.** The candidate contributes a repeatable net policy benefit on fresh families beyond the best inexpensive estimator.

**Stop or revise when.** Prediction MAE improves but decisions or measured outcomes do not; unsupported states dominate; cost exceeds decision value. Retain the simpler estimator.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E13 — Decide whether separate A/B models are necessary

**Question.** Is separate conditional fitting more useful than a shared model with maintenance state?

**Change.** Compare a shared model plus state/interactions against separate A/B models; include shared-model and separate-model variants under matched total tuning/parameter budgets where possible.

**Hold fixed.** Same query/layout overlap support, complete history, source-family roles, outcome definition and cost model family.

**Required evidence.** Counts of independent episodes and overlap exposure per state; conditional and common-support errors; capacity/training time; physical decision contribution.

**Continue when.** Separate models add reproducible supported value, with enough independent maintenance episodes and matched layout support.

**Stop or revise when.** A has only sparse rows from a few episodes or differs systematically in layout. Do not interpret A-minus-B as a causal penalty.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E14 — Estimate rewrite duration and layout transition

**Question.** Can the controller estimate rewrite work and completion time from pre-action state?

**Change.** Collect real isolated rewrites over supported file-count/size layouts, then matched concurrent-load rewrites. Compare empirical medians, bytes/throughput regression and a small learned regressor.

**Hold fixed.** Rewrite algorithm/options, logical rows, hardware and pre-action feature boundary. Separate no-op/failed rewrites from successful useful transitions.

**Required evidence.** Actual client duration, rewritten/added files and bytes, final layout, commit time, CPU/I/O and concurrent demand context.

**Continue when.** Enough independent rewrites support the chosen model and useful duration/transition error bounds.

**Stop or revise when.** Only a handful of repeated rewrites exist or model predicts file reduction as if it were response benefit. Keep empirical support limited.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E15 — Remove unnecessary features and tune within development

**Question.** Which features and model settings earn their acquisition and fitting cost?

**Change.** Nested development comparisons: SQL identity; plus layout; plus observed queue/state; plus plan operators; plus complete host windows. Compare small fixed hyperparameter grids, not unrestricted search.

**Hold fixed.** Whole source-family folds, targets, transformations, scoring/coverage rule and tuning budget. Expensive plan features must be timed/cached with snapshot binding.

**Required evidence.** Per-feature-group incremental predictive and decision value, acquisition time, OOD rate and chosen hyperparameters with trial ledger.

**Continue when.** Retain only groups whose net benefit survives development checks; freeze before final evaluation.

**Stop or revise when.** Feature availability leaks future outcomes; row-wise cross-validation; test-driven tuning; complexity without measurable decision value.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E16 — Calibrate uncertainty only with adequate blocks

**Question.** Do uncertainty estimates support safer timing decisions on genuinely separate calibration blocks?

**Change.** Freeze models; calibrate block-level residual scores on unused calibration families and evaluate once on separate test families. Define whether coverage concerns a block maximum, an episode aggregate or an individual query.

**Hold fixed.** Model fit, calibration definition, decision horizon, target units, source grouping and declared risk. Never apply an individual-query interval to whole-episode guarantees.

**Required evidence.** Finite conformal rank, number of calibration blocks, empirical coverage/width, OOD refusals and dependence/shift limitations.

**Continue when.** The mathematical rank is finite and the independently chosen statistical/precision requirements are met; physical benefit of the uncertainty rule is demonstrated.

**Stop or revise when.** Too few blocks, dependence, shifted support or calibration/test reuse. Keep outputs explicitly uncalibrated; nine blocks for 90% is a rank minimum, not adequate power.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E17 — Isolate the value of C, learned costs and uncertainty

**Question.** Which component causes the policy improvement?

**Change.** Use a fixed planner in a 2x2 ablation: persistence versus selected forecast, empirical versus selected learned costs. Add uncertainty on/off only after E16. Keep the strongest reactive policy outside this 2x2 as a required comparator.

**Hold fixed.** Action set, invocation cadence, training source, terminal obligation, physical layouts, workload and resource budget.

**Required evidence.** Four-cell paired physical comparison on fresh development blocks; marginal and interaction effects; total overhead. Later optional eight-cell uncertainty extension.

**Continue when.** At least one justified component adds useful outcome value with stable support and accounting.

**Stop or revise when.** A better result is attributable to a different planner/action set or ignored overhead. Simplify components that do not add value.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E18 — Freeze and execute the one-time confirmatory comparison

**Question.** Does the frozen selected method beat the frozen strongest baseline in the declared target population?

**Change.** Preregister primary metric, practical effect, precision/sample size, family split/purge, arm order, failure policy and guardrails from development. Run complete matched physical blocks on untouched families once.

**Hold fixed.** All model artifacts, baseline thresholds, feature code, planner, hardware definition, action rule and analysis script. No test feedback into model choice.

**Required evidence.** All attempts, full raw/audit manifests, equal-work contrasts, family-level intervals, raw distributions, response/resource/debt guardrails and sensitivity analyses marked secondary.

**Continue when.** The preregistered superiority/equivalence criterion and all safety/correctness/obligation gates are satisfied.

**Stop or revise when.** Failure, imprecision, effect below practical threshold or guardrail violation. Report inconclusive/negative; consume test and design a genuinely new study if needed.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E19 — Optional CPU or I/O objective study

**Question.** Can maintenance reduce resource work for the same completed workload without an unacceptable response regression?

**Change.** Before new outcomes, register a distinct resource-first protocol: choose CPU core-seconds OR a well-scoped I/O metric as primary and a justified response constraint. Do not rename old response experiments.

**Hold fixed.** Same offered/cohort work, full drain, successful rewrite and final-state criterion; all observer/controller cost included.

**Required evidence.** Resource-response Pareto plots with a fixed selected operating point, resource provenance and both positive and negative outcomes.

**Continue when.** Net savings survive equal-work accounting and the response constraint on fresh data.

**Stop or revise when.** Savings arise from omitted requests/maintenance, lower quality, unmeasured processes or moving work outside the horizon.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E20 — Validate scale transfer to SF100

**Question.** Does the mechanism survive a larger verified dataset?

**Change.** Audit the actual SF100 source/generator and capacity, then repeat the smallest decisive comparison at SF100. First test frozen SF10 models; report retraining as a different adaptation experiment.

**Hold fixed.** Query semantics, controlled layout treatment, policy interfaces and complete evidence gates. Do not change scale and engine/resources simultaneously.

**Required evidence.** All-table row/type/provenance checks, actual data bytes, full correctness, support coverage, resource/admission receipts and physical outcomes.

**Continue when.** Capacity and verification pass and the mechanism transfers or its failure is interpretable.

**Stop or revise when.** Insufficient RAM/disk/evidence budget or no supported predictions. SF100 is an external-validity branch, not a cure for broken SF10 evidence.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E21 — Concurrency and query-mix transfer

**Question.** Does the result hold beyond one serial client and a narrow mapped query mix?

**Change.** Change client concurrency in one series (proposed 1 then 4); change query mix in a separate series. Use real mapped SQL and audit per-session queue/task ownership.

**Hold fixed.** Everything except the one named factor. Preserve intact real arrival timing and expose over/underload rather than compressing the trace.

**Required evidence.** Aggregate and per-query response, per-session ledgers, engine overlap and logical results; policy support/refusals and utilization.

**Continue when.** Mechanism persists or a clear saturation boundary can be reported.

**Stop or revise when.** Concurrent request ownership/accounting cannot be proved or experiment mixes multiple interventions.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E22 — Add continuing fragmentation from real writes

**Question.** Does timing matter more when a real table continues accumulating small files?

**Change.** Register an actual write source with data lineage and ingestion timestamps. If using benchmark-generated inserts, label them explicitly as controlled benchmark writes, subject to user approval; they cannot be called production trace writes.

**Hold fixed.** Equal committed writes, queries and maintenance debt across arms; consistent snapshot/visibility semantics.

**Required evidence.** Committed row/version history, write latency, query response, file/debt trajectory, rewrite work and conflict outcomes.

**Continue when.** A real supported write source and complete correctness boundary exist; ongoing debt creates a useful timing tradeoff.

**Stop or revise when.** No authorized write provenance or missing data. Do not invent ingestion from Snowset arrival timestamps.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E23 — Selective or incremental file-group compaction

**Question.** Can bounded useful work reduce the disturbance of a monolithic rewrite?

**Change.** Compare whole eligible rewrite with a registered subset/file-group strategy through supported Iceberg options; preserve identical long-run obligation and record every commit.

**Hold fixed.** Same data, workload, final maintenance obligation and target size; no preemption/cancellation of active jobs.

**Required evidence.** Per-action duration/work, interference episodes, accumulated debt, total CPU/I/O and final layout.

**Continue when.** Smaller actions improve the declared objective after total-work accounting and repeated action overhead.

**Stop or revise when.** Partial compaction wins only by leaving debt, changing target quality or hiding extra commits/rewrite amplification.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E24 — Partition prioritization

**Question.** Which partition should receive a fixed maintenance budget first?

**Change.** Register multiple real partitions and measured query access frequencies; compare round-robin, file-count priority, workload-aware empirical priority and a supported learned ranking.

**Hold fixed.** Total budget, eligible partition set, action implementation and final obligation rule; isolate selection from timing.

**Required evidence.** Partition-level response exposure, maintenance bytes, fairness/debt and end-to-end performance.

**Continue when.** Selection causes useful effects beyond a strong cheap ranking with no starvation.

**Stop or revise when.** Only one unpartitioned table exists, missing access provenance or comparison conflates a larger budget with smarter selection.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E25 — Delete-file maintenance and merge-on-read

**Question.** Does a different, real maintenance debt produce a stronger measurable read/write tradeoff?

**Change.** Register actual deletes/updates and supported Iceberg delete semantics in fresh isolated tables. Compare appropriate delete/data maintenance actions; this is a new hypothesis.

**Hold fixed.** Identical logical changes and snapshot correctness, action eligibility and final deletion semantics.

**Required evidence.** Delete-file inventory, row/result equality, read amplification, commit/conflict work and response/resource accounting.

**Continue when.** Debt and outcomes are directly evidenced with complete correctness.

**Stop or revise when.** Deletes are fabricated, semantics differ between arms or the implementation cannot attribute merge work.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E26 — Second environment or engine

**Question.** How much of the result depends on one machine or Spark implementation?

**Change.** Replicate the minimal decisive experiment on a second available resource configuration or engine. Change one environment dimension per registered study.

**Hold fixed.** Logical dataset, query semantics, workload family selection and maintenance objective; disclose unavoidable engine semantic differences.

**Required evidence.** Hardware/software configuration, version pins, compatibility/correctness checks and paired effects within each environment.

**Continue when.** Result transfers, or a clear engine/resource limitation is established.

**Stop or revise when.** A new environment is unavailable or changes so many factors that the study cannot explain the difference.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E27 — Delta Lake external-validity branch

**Question.** Does the same timing principle extend to another table format?

**Change.** Implement a separate Delta adapter for native bin-packing OPTIMIZE, using verified logical rows and equivalent queries; retain its format-specific snapshots and metrics.

**Hold fixed.** Within-format resource and workload comparison; same high-level question. Never treat OPTIMIZE and Iceberg rewrite as identical implementations.

**Required evidence.** Correctness/provenance, adapter audit, native maintenance output and equal-obligation comparisons.

**Continue when.** The mechanism is already credible on Iceberg and extra engineering can answer a specific transfer question.

**Stop or revise when.** Switching formats is only an attempt to find a favorable number or required native instrumentation is absent.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E28 — Hudi merge-on-read branch

**Question.** Does the timing hypothesis apply to log-to-base-file merging under continuing updates?

**Change.** Build a separate Hudi MOR experiment with actual updates and read/write visibility checks. Hudi compaction merges log updates; it is not the same as file-size bin packing.

**Hold fixed.** Equal real update streams, read semantics, base/log debt and completed maintenance.

**Required evidence.** Log/base inventories, read amplification, update latency, merge work and full workload outcomes.

**Continue when.** A supported MOR workload and a distinct research question justify the larger adapter effort.

**Stop or revise when.** No update source or no equivalent work/semantics; this is a project pivot, not an immediate fallback.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E29 — RocksDB/LSM pivot

**Question.** Is a fundamentally different maintenance architecture necessary for a new hypothesis?

**Change.** Only after an explicit project decision, move to a fresh LSM research problem and compare appropriate native baselines such as workload-aware compaction methods.

**Hold fixed.** New scope, actual supported key/value workload provenance and native latency/debt metrics; do not transfer lakehouse claims automatically.

**Required evidence.** New literature review, workload, correctness/accounting adapter and baseline reproductions.

**Continue when.** The new mechanism and available time justify a separate project trajectory.

**Stop or revise when.** The motivation is simply that Iceberg had a null result. Existing strong LSM literature makes this an expensive pivot.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E30 — Robustness, drift and unsupported states

**Question.** When does the controller lose support, miss a deadline or make a harmful decision?

**Change.** Evaluate preregistered real workload shifts, unseen layouts and model age on separate data. Measure natural failures; do not deliberately corrupt evidence or kill jobs.

**Hold fixed.** Frozen model/decision policy and transparent refusal contract.

**Required evidence.** Coverage/refusal rates, worst blocks, deadline/debt violations and a failure taxonomy with raw receipts.

**Continue when.** Scope and operating limits are explicit; conclusions survive stated robustness checks.

**Stop or revise when.** Unsupported predictions silently fall back, metrics exclude failed arms or drift triggers test-set retuning.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E31 — Write and release a reproducible paper artifact

**Question.** Can a reader reconstruct every figure and verify the central claim?

**Change.** Freeze the claim ledger, source versions, all attempts, analysis commands and raw manifests; write methods/results/limitations and package a bounded reproducible artifact.

**Hold fixed.** Primary outcome and failure history; no selective removal of null or contradictory experiments.

**Required evidence.** Paper tables/figures with source SHA links, environment/seed records, costs, data-license notes and next-agent instructions.

**Continue when.** The central claim is supported, baseline comparison is fair, artifact reproduces and the team/guide review the venue fit.

**Stop or revise when.** Only screenshots, prediction accuracy or a single favorable run support the claim. Target acceptance is never guaranteed.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E32 — Boundary or negative-result research branch

**Question.** Under what conditions is compaction timing or a learned controller not worth its cost?

**Change.** Preregister a bounded regime map and equivalence/practical-effect analysis on fresh blocks, retaining layout/parallelism and overhead mechanisms.

**Hold fixed.** Fair baselines, equal completed work, sufficient precision and the same evidence quality as a positive claim.

**Required evidence.** Timing-effect intervals, useful-region boundaries, overhead-to-effect ratios and independent reproduction.

**Continue when.** A generalizable explanatory boundary with sufficiently precise evidence distinguishes the work from prior findings.

**Stop or revise when.** Failure to reject zero is presented as equivalence, or a failed measurement pipeline is presented as a negative scientific finding.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.

## E33 — Observer-efficiency engineering branch

**Question.** Can durable evidence collection be made cheaper without changing the measured system contract?

**Change.** Study publication/serialization/storage placement through semantically equivalent implementations; quantify the effect on an external control loop and workload.

**Hold fixed.** Every required record, timestamp, durability, coverage, checksum and failure gate. Freeze policy outputs for implementation comparisons.

**Required evidence.** Raw-equivalence proofs, latency/CPU/write costs, drift controls, end-to-end effects and independent workloads.

**Continue when.** A distinct transferable mechanism and independent evidence support more than a one-machine storage-location observation.

**Stop or revise when.** Claims rely only on the historical 31–42% observer-path contrast, omitted durability or assumed GIL causality.

**Record after the unit.** Actual protocol/code/source hashes, source-family role, all assigned and completed arms, PIDs/logs/receipts, measured results with units, failures and unattempted counts, limitations, next gate, and intended-file synchronization. Append both methodology documents. A failed unit never becomes training data or a quiet retry.
