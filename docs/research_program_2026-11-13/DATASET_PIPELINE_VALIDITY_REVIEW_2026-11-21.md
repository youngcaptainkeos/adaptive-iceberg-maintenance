# Dataset, replay and simulator validity review

Recorded21November2026. Project: **Workload-Aware Scheduling for Data Processing Systems**. Source revision reviewed: a3e48393039cfac6697083ca2d38def564684465.

## Verdict

The dataset and real Spark/Iceberg execution are useful foundations for a controlled study. The current combination is **not sufficient evidence of a generally effective forecast-aware compaction scheduler**, nor a faithful reproduction of the original Snowflake workload. The key gaps are workload construction, host-capacity matching, outcome boundaries, simulator validity and independent evidence—not simply the model architecture.

This is a read-only review of local source, saved configurations and existing terminal summaries. No new scientific test, statistical analysis job, raw-ledger reconstruction, SQL, model fit or remote operation was run. Numerical outcomes below are read from saved result files. Derived arrival-rate arithmetic is explanatory, not a new capacity measurement. Worker3 remains unavailable according to the user; current server/process/filesystem state is unknown. No historical result is promoted or rewritten.

A correction to overly narrow recent progress summaries: older SF1 full-drain timing evidence exists and must not be omitted merely because recent work focused on failed SF10 engineering runs. Its limitations remain material.

## 1. What the pipeline actually contains

| Layer | Actual implementation/evidence | What it supports | What it does not preserve/prove |
|---|---|---|---|
| Benchmark rows | Generated TPC-H-derived SF10, eight tables; typed references and saved logical correctness checks | Repeatable relational queries and an auditable layout intervention | Production business data or official full TPC-H benchmark execution |
| Arrival source | Saved Snowset validation records69,182,074rows,2,051warehouses; selected cohort2,760,971arrivals from one warehouse | Provenance-bound observed timestamps and count-series experiments | Original SQL, table identity/access pattern or source CPU/I/O faithfully represented on worker3 |
| Warehouse selection | Maximum first-seven-day arrival count with numeric-ID tie break; later split boundaries recorded | Training-only selection without selecting on later policy outcomes | Representative workload selection or a rate appropriate for our serial client |
| SQL assignment | Source arrivals assigned to six fixed templates in arrival-order round robin | A precisely specified trace-driven benchmark workload | The original association between query type/cost and arrival time |
| Execution | Real Spark3.3.4 / Iceberg1.4.3, saved local[16] backend and16g driver setting; one foreground query session in SF10 runner | Real local-engine maintenance contention and query measurements | A multi-node cloud Snowflake warehouse or original distributed-storage cost ratios |
| Maintenance | Fresh table created from pinned lineitem snapshot with controlled repartitioning; a bin-pack rewrite; other tables pinned | A bounded one-table, one-rewrite experiment | Continuous ingestion, sustained fragmentation, updates/deletes or long-term debt management |
| Queue measurement | Explicit original arrivals/offers/dispatch/completion and retained debt | Honest queue accounting where complete and audited | A full offered-cohort endpoint in a runner that stops dispatching at the arrival horizon |
| Planner estimates | Empirical conditional durations, seasonal count forecast and FIFO snapshot simulator | Candidate decision estimates, if validated for a specified regime | Observed counterfactual outcomes or accepted physical scheduling benefit |

TPC-H uses benchmark-generated data by design. That is legitimate benchmark input; it is distinct from inventing query labels or pretending generated rows are production records. The official benchmark includes its own workload and measurement rules; ours is a custom workload over its schema. [TPC-H](https://www.tpc.org/tpch/).

Snowset publishes query statistics rather than a replayable database. Its schema distinguishes query creation, execution and total duration and includes warehouse-size and resource fields. We currently extract only queryId,warehouseId,createdTime for the arrival cohort. Timestamp fidelity therefore establishes only arrival fidelity. [Snowset repository](https://github.com/resource-disaggregation/snowset), [schema](https://raw.githubusercontent.com/resource-disaggregation/snowset/master/schema.md).

The saved source validation also explicitly retains a publisher-authenticity/recovered-receipt limitation. Its checksums and decoding establish consistency of acquired bytes, not independently verified publisher cryptographic authenticity. Do not silently drop that qualifier.

## 2. Data scale and query coverage

The SF10 source configuration records:

| Table | Rows | Source data files |
|---|---:|---:|
| region | 5 | 1 |
| nation | 25 | 1 |
| supplier | 100,000 | 4 |
| customer | 1,500,000 | 16 |
| part | 2,000,000 | 16 |
| partsupp | 8,000,000 | 16 |
| orders | 15,000,000 | 16 |
| lineitem | 59,986,052 | 4 |

These are saved source-state observations, not a fresh remote inventory. The SF10 campaign copies lineitem to a separate **64-file** intervention table; the source's four files and the intervention's64files are different states. The source lineitem data_bytes is1,713,414,510. SF10 denotes generation scale, not10GB of compressed Iceberg files or a guarantee that the working set exceeds RAM. With the recorded16g driver and OS caching, cache fit is a serious question requiring measurements, not an established explanation.

The actual query suite is six fixed custom statements: filtered revenue, grouped lineitem, orders/lineitem join, customer/orders/lineitem join, grouped/sorted top parts, and a five-table supply join. It is not the complete official22-query workload. Dates/predicates are fixed in this engineering suite.

The sixth query reads partsupp/part/supplier/nation/region and **does not read the rewritten lineitem table**. It can serve as a useful negative-control query for shared-resource interference, but its lineitem file-count feature is intervention context, not the query's scan layout. It cannot demonstrate direct post-compaction lineitem scan benefit. Report its outcomes separately as well as within the preregistered mixed workload; do not remove it post hoc to increase a headline improvement.

Eight plan-operator counts are available, but estimated rows/bytes are deliberately not admitted as predictors. Operator counts are real structural features, not complete runtime complexity. With six fixed SQL templates, the features are heavily tied to template identity; there is insufficient evidence that they generalize to unseen selectivities, cardinalities or SQL shapes. More model features cannot create missing query diversity.

## 3. Arrival fidelity is not workload fidelity

The registered SF10 engineering window is22February2018 20:00:00.286–20:20:00.286UTC: **3,131arrivals in1,200seconds**, about2.61requests/second. Exact arrival spacings are preserved. The cohort was deliberately selected for high training volume, not demonstrated suitability for the worker.

The mapper assigns `query_suite[i % len(query_suite)]`. This enforces a nearly uniform six-template mixture and periodic query order. It removes the original relationship between burst periods and expensive/cheap queries, the source's query concurrency, hot tables and read/write mix. A source interval with many cheap operations can become a queue of expensive joins. Keeping its timestamps does not make that transformed workload representative of the original warehouse.

The14November one-shot query capability measured0.66–6.15seconds of client service on pinned existing source snapshots. These are not matched64-file service-capacity estimates, and must not be used to calculate a definitive utilization for the old campaign. Nevertheless, their scale plus one serial foreground session makes the transferred arrival intensity a major overload risk. Confirm the operating regime physically before assigning any forecast benefit. High backlog can dominate response and make arrival-count quiet periods irrelevant while the server keeps draining existing work.

Selecting a high-volume warehouse is not in itself test leakage: selection used the training interval. It is a representativeness/capacity issue. Repeating the same source window estimates execution variability; it does not add independent workload diversity.

## 4. Physical replay and the numerical simulator are separate

### Physical SF10 replay

`three_model_maintenance/runtime/sf10_collect.py` executes actual SQL on actual Iceberg tables. It is not merely a timing simulator. The engineering configuration explicitly sets `client_count:1` and `boundary_rule:no_dispatch_after_horizon_natural_inflight_completion`. Its loop stops submitting queries at the end of the1,200-second arrival horizon, lets current work finish naturally and retains queued requests.

Retaining that debt is honest and useful for engineering. It does **not** make completed-only service or response an estimate of the complete offered population. The same configuration explicitly says it is not a full-drain policy comparison. Its no-maintenance and compact-later arms also end with different maintenance work and layouts. The pair is a capability/mechanism comparison, not an equal-completed-maintenance resource comparison. Archive03 failed its original attribution gate, and the dependent maintenance arm was never attempted.

### Older and repaired planner simulators

`queue_aware_maintenance/models/simulator.py` changes the simulated work rate/layout at a rewrite boundary even when the same query is still executing. The saved19October semantics audit found61inconsistent boundary cases out of61examined. Historical query labels were whole calls on pinned snapshots; they did not identify fractional progress rates. That old model is unsuitable as evidence of a correct schedule prediction.

`models/snapshot_simulator.py` fixes the important snapshot error: layout and conditional whole-call duration are chosen at dispatch. The saved reconstruction passed, but explicitly records `physical_validation_passed:false`. This is a semantics correction, not demonstrated predictive accuracy. The controller factory versions both models; later protocols explicitly select the snapshot version. Do not assume every historical run used the same model.

The snapshot model still has important simplifications:

- Maintenance pending is checked at query dispatch. A query that starts before compaction and later overlaps it keeps its no-pending whole-call estimate. This cannot express the effect of a rewrite beginning during an in-flight query.
- A query starting near rewrite completion receives the same pending-state conditional duration as one starting near its beginning. Actual overlap fraction and changing contention are not represented.
- Rewrite duration is an empirical median indexed by initial file count, not a jointly evolving function of foreground work and resource pressure. Reciprocal slowdown of queries and compaction is not modelled.
- New layout availability is assumed at estimated rewrite completion. The recorded snapshot-model limitation already notes that metadata publication delay is unmodelled.
- One median busy-client turnaround is used. Its validity across observer versions, evidence storage and query types has not been demonstrated.
- Candidate schedules include `None` (no rewrite). That was explicit in the older one-rewrite-allowance contract, but is not an equal-obligation action set for the current research target. A policy cannot win by avoiding required maintenance.
- `estimated_drain_seconds` is computed as last predicted finish minus decision-now, rather than excess beyond the arrival-horizon end. It is a remaining-completion-time estimate under that name; do not compare it directly with horizon-relative drain.

The seasonal forecaster averages prior-day bin counts, rounds them and places predicted requests uniformly inside the bin with the benchmark's round-robin query mix. These are explicitly labelled forecast events, not fabricated observed arrivals. Nevertheless, they smooth within-bin bursts and preserve no empirical demand-cost correlation. Count accuracy alone does not validate these scheduling inputs.

Use simulations only to propose actions until predicted candidate rankings and physical schedule outcomes agree on separate development blocks. Do not repair the simulator by fitting to final-test errors.

## 5. Existing complete timing evidence must remain visible

`results/queue_aware_timing_20261021/repeated_window0/result.json` records8passed/0failed/0unattempted physical SF1 timing arms. The saved analysis reconstructed full-drain results for two repeats of one known development window. This is more than a process screenshot or a capability run, but it remains narrow exploratory evidence.

| Delay relative to immediate | Repeat0 reported response reduction | Repeat1 reported response reduction |
|---|---:|---:|
| First opportunity at/after60s | 0.4877% | 0.2007% |
| First opportunity at/after600s | 7.3710% | -0.9811% |
| No action, diagnostic unequal work | 10.2373% | -1.3396% |

These percentages are read from the existing saved contrasts; no new statistical test or ledger reconstruction was executed here. The short-delay effect was small, and the longer-delay result changed direction. No-action has a different final layout and does less maintenance; it cannot serve as a fair equal-maintenance winner. Forward/reverse order cannot eliminate cache/host drift, and two repeats of one window cannot support broad uncertainty or generalization claims. Instrumentation remains part of response.

Thus the evidence is not “we have never run any timing comparison,” nor “we already proved forecasting works.” It is “a limited earlier timing study produced weak/mixed exploratory effects; the more diverse SF10 pipeline still lacks accepted matched performance comparisons.” This supersedes overly narrow summaries that omitted the earlier study without changing any historical outcome.

## 6. Can this setup support a paper claim?

| Claim | Current support |
|---|---|
| Real benchmark data, SQL execution and a physical compaction capability exist | Supported by saved evidence within recorded provenance limitations |
| Original Snowset warehouse workload is faithfully reproduced | Unsupported: only arrival timing/identity are transferred |
| The new evidence auditor works on worker3 | Pending;21November code was built locally only |
| The snapshot planner has correct pinned-layout bookkeeping | Saved reconstruction supports that narrow property |
| The planner accurately predicts the best physical maintenance start | Not established |
| Compaction timing can affect our instrumented SF1 workload | Exploratory mixed/small timing contrasts exist |
| Forecast-aware learned timing beats strong cheap rules generally | Not established |
| CPU/I/O savings for equal completed work | Not established |

The setup can become a defensible **trace-driven controlled Iceberg study**. It cannot currently prove a production-representative or general learned-scheduler benefit. A single-machine mechanism paper also needs a clearly limited claim or a credible later transfer dimension.

## 7. Revised priority: fix the experiment before expanding models

1. **Complete one bounded measurement gate.** Validate the prepared raw auditor once on worker3, preserving missing dependency states and all old failures. A pass is a prerequisite only. Do not let more instrumentation iterations substitute for testing the hypothesis.
2. **Characterize the actual workload-capacity relationship.** Measure the same six templates under registered matched conditions, with complete observer/turnaround accounting. Report foreground client queue pressure separately from CPU saturation. Choose intact additional real source windows/warehouses across declared operating regimes using training-only arrival evidence and development capacity measurements, before seeing policy outcomes. Keep the original maximum-volume window as an overload boundary case. Do not thin/compress its arrivals or silently invent fallback demand.
3. **Implement full-drain, equal-obligation comparisons.** Every policy receives the same offered cohort and initial logical/layout state, completes the same specified rewrite, and is measured through both completions. No post-horizon dispatch prohibition may be silently removed from the old runner; create a versioned action/drain adapter. Track response, waiting, service, offered/failed/unfinished counts, final state, overhead and resource coverage.
4. **Demonstrate mechanisms physically.** Separate same-query fragmented-versus-compacted effects from same-snapshot overlap interference, then measure timing. Preserve the no-lineitem query as a declared control. Record actual layout distribution, plan and cache context rather than equating a requested file count with all layout properties.
5. **Audit predictions against physical actions.** Use the cheap model to predict registered schedules on development blocks, then compare its ordering with actual matched schedule outcomes. Check transition/overlap cases, rewrite duration and publication lag explicitly. Reject unsupported states. If ranking is unreliable, retain empirical/fixed/reactive policy comparisons while revising the model prospectively.
6. **Add query diversity only for a stated claim.** Register additional real benchmark templates/parameter ranges and verify results independently. Keep template/parameter families held out when testing complexity generalization. Do not equate an eight-count vector with a learned concept of complexity.
7. **Freeze a small test with independent source roles.** Compare fixed timing, a bounded queue rule and a simple past-only predictive rule first. Add learned demand/cost components one at a time under the same planner/action set only if timing headroom survives noise and overhead. Reserve source families and show coverage; larger scale alone is not independent evidence.

Do not jump directly to SF100: larger scans can worsen an already mismatched offered load. Study a meaningful working-set/cache and parallelism boundary after a mechanism is measured. Continuing writes and additional engines are later separately registered studies, not ways to obscure a null result.

## 8. Evidence pointers and review boundaries

- Source acquisition/selection: `scripts/validate_snowset_source.py`, `scripts/extract_snowset_arrivals.py`; `datasets/snowset/validated_source_metadata_20261014/validation_record.json`; `datasets/snowset/arrival_cohort_export_repair_20261014/cohort_record.json`.
- Mapping: `three_model_maintenance/experiments/sf10_campaign.py` (`window`, `mapping`); actual `results/sf10_archive_validation_20261101_03/mapping/mapping_record.json` and `mapped_arrivals.csv`.
- Actual SF10 configuration/query suite/row states: `results/sf10_archive_validation_20261101_03_recovered_raw/sf10_archive_validation_20261101_03_no_maintenance/config.json`; source proof `results/sf10_archive_validation_20261101_03/sf10_source.json`.
- Physical execution and feature publication: `three_model_maintenance/runtime/sf10_collect.py`, `sf10_contract.py`, `collector_bridge.py`; `three_model_maintenance/preparation/query_plan.py` and `sf10_candidates.py`.
- Model and simulator: `queue_aware_maintenance/models/{simulator,snapshot_simulator,costs,forecast}.py`; `queue_aware_maintenance/policies/controller_factory.py`.
- Actual semantics results: `results/queue_aware_maintenance_20261019/simulator_semantics_audit/result.json` and `snapshot_model_reconstruction/result.json`.
- Actual complete timing study: `results/queue_aware_timing_20261021/repeated_window0/{result.json,analysis/result.json}`.
- Current SF10 failure: `results/sf10_archive_validation_20261101_03/result.json`, recovered `failure.json`; ownership diagnostic `results/sf10_sql_ownership_diagnostic_20261111_01/result.json`.
- New capability/capture measurements: `results/live_direct_capture_20261114_01/result.json`, `results/live_baseline_export_20261114_01/result.json`.

Historical completion records are not freshly revalidated raw experiments. Offline source review can establish what the code assumes and what saved reports say; only remote detached tests and physical comparisons can close the remaining gates. There is no PID or experiment log for this review because nothing was launched.
