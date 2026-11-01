# Project models, datasets and research directions

Saved on 1 November 2026 from the preceding chat rundown. Evidence discussed below was inspected locally on 27 October; this document does not establish current worker3 status or new experiment results.

**The project is feasible, but we have not yet demonstrated that ML improves compaction timing. Our biggest gap is experimental evidence that timing matters predictably—not a shortage of model types.**

The last local inspection found that the synchronization relay had recorded an SSH disconnection and stopped. The saved SF10 progress still showed the first episode collecting, with training not performed. That copy was stale and could not establish whether the remote experiment eventually passed or failed.

## 1. Why ML has not demonstrated a meaningful advantage

There are three separate research questions:

1. Does compaction improve subsequent query performance?
2. Does performing it during busy periods cause enough interference to matter?
3. Can predicting future demand choose a better time than a simple rule?

Evidence for one does not automatically answer the others.

| Issue | Consequence |
|---|---|
| Earlier SF1 queries were relatively short | Query identity and layout may explain most useful variation, leaving little additional signal for ML. |
| Sparse maintenance observations | The first exploratory A/B fit had 16 pending-maintenance queries and 319 nonpending queries from one source family. |
| Confounded layout and maintenance state | Eligible A rows had 16 files; eligible B rows had one file. Maintenance interference cannot be separated from layout differences. |
| Repeated observations within one rewrite | Hundreds of queries are not hundreds of independent maintenance episodes. |
| Background timing drift | Earlier controls changed on a scale similar to some rewrite contrasts; warming, caching and host changes can mimic benefits. |
| Service-time target | Current latency models exclude prior dispatch queue waiting, where a scheduler may have its main effect. |
| Incomplete scheduling integration | A/B training alone does not demonstrate the temporal contribution. |

An older SF1 reserved-family comparison recorded:

| Method | Equal-episode mean absolute error |
|---|---:|
| Query median | 21.23 ms |
| Query/layout median | **20.34 ms** |
| Log Ridge | 21.54 ms |
| Shallow tree | 20.93 ms |

Source: [saved reserved evaluation](../results/consistent_reserved_evaluation_20261017/result.json). These are older experiment results, not results of the new SF10 comparison. They do not establish statistical superiority or calibration.

The median already captured much of the useful structure in that setting. These results reject a current claim that our learned latency model clearly wins; they do not prove Iceberg scheduling cannot work.

**Next scientific question:** do identical maintenance actions at different registered times produce repeatable differences in workload outcomes? If there is no useful physical timing trade-off, hyperparameter tuning cannot manufacture a defensible contribution.

## 2. Models, predictors, hyperparameters and code

### Intended components

| Component | Job | Limitation |
|---|---|---|
| A | Estimate query service time while this client has a pending maintenance request | Pending does not establish actual engine overlap or causal slowdown. |
| B | Estimate query service time without that pending request | Requires comparable layouts, query types and host conditions. |
| C | Predict future offered query demand | Arrival counts alone do not establish future CPU/I/O demand or original SQL mix. |

We also need a maintenance-duration/resource estimate to determine whether a quiet interval is long enough. The three-component idea does not remove that requirement.

The SF10 implementation compares a shared estimator using maintenance state as a feature against separate A/B estimators. Splitting is a hypothesis, not an automatic improvement.

### Registered 22 inputs

| Group | Inputs |
|---|---|
| Query | Query-template ID |
| Intervention-table layout | File count, row count, total file bytes |
| Execution context | Maintenance client request pending; dispatch queue depth |
| Host measurements over 60 seconds | CPU busy fraction, memory used fraction, read bytes/second, write bytes/second |
| Host measurements over 300 seconds | The same four measurements |
| Actual preexecution plan | Operator, scan, join, aggregate, exchange, sort, filter and window counts |

Actual runtime, actual bytes scanned and output cardinality from a query cannot become predictors for that same query. The layout features describe the intervention table; they do not claim to describe every table scanned.

### Current settings

| Parameter | Current value | Interpretation |
|---|---|---|
| Architecture | Shared and separate A/B | Compare pooling against condition-specific fits |
| Target transformation | Log service milliseconds | Reduces domination by very large runtimes |
| Ridge alpha | 1 | Coefficient regularization |
| Ridge solver | SVD | Numerical solver |
| Ridge tolerance / max iterations | 0.0001 / 1,000 | Constructor settings; SVD does not use these as iterative tuning knobs |
| Boosting loss | Squared error on log target | Error objective |
| Boosting learning rate | 0.05 | Contribution of each added tree |
| Boosting iterations | 100 | Boosting rounds |
| Maximum leaves / depth | 7 / 3 | Tree complexity |
| Minimum samples per leaf | 5 | Restricts tiny fitted groups |
| L2 regularization | 1 | Leaf regularization |
| Early stopping | Disabled | Avoids an implicit random validation split |
| Seed | 20261026 | Reproducibility, not a knob to search for winning outcomes |

Potential future registered investigations include Ridge alpha on a small logarithmic grid, boosting depth/leaf size/learning rate/iteration budget, raw versus log targets, shared versus separate capacity budgets, and feature ablations. Tune using development families only; preserve held-out test evidence.

With six fixed SQL templates, plan counts may merely encode query ID. Complexity learning requires more SQL variants and held-out query families.

The current model refuses unseen query/layout/state combinations and inputs outside training numeric ranges. Unsupported predictions remain absent. Report coverage alongside error: low error on a tiny easy subset is not success.

Hyperparameters belong to models. Scale, fragmentation, concurrency, maintenance timing and workload mix belong to experimental design. The latter currently deserve more attention.

### Code reading order

1. [SF10 registration and hyperparameters](../three_model_maintenance/protocols/sf10_models_campaign02_20261026.json)
2. [Training and comparison](../three_model_maintenance/training/sf10_comparison.py)
3. [Audited model-row export](../three_model_maintenance/preparation/sf10_candidates.py)
4. [Query-plan extraction](../three_model_maintenance/preparation/query_plan.py)
5. [Physical campaign orchestration](../three_model_maintenance/experiments/sf10_campaign.py)

## 3. Understanding TPC-H

TPC-H models a wholesale business: customers place orders containing parts supplied by suppliers. The schema has **eight tables and 61 columns**.

| Table | Columns | Meaning | SF1 rows | SF10 rows |
|---|---:|---|---:|---:|
| region | 3 | Geographic regions | 5 | 5 |
| nation | 4 | Countries | 25 | 25 |
| supplier | 7 | Supplier details | 10,000 | 100,000 |
| customer | 8 | Customer details | 150,000 | 1,500,000 |
| part | 9 | Product catalogue | 200,000 | 2,000,000 |
| partsupp | 5 | Supplier/part stock and cost | 800,000 | 8,000,000 |
| orders | 9 | Order headers | 1,500,000 | 15,000,000 |
| lineitem | 16 | Items within orders | 6,001,215 | 59,986,052 |

Counts come from the local schema and saved source inventories.

`orders` fields: order key, customer key, status, total price, order date, priority, clerk, shipping priority and comment.

`lineitem` fields: order key, part key, supplier key, line number, quantity, extended price, discount, tax, return flag, line status, ship date, commit date, receipt date, shipping instructions, shipping mode and comment.

Relationships:

```text
customer -> orders -> lineitem
                       -> part and supplier
part + supplier -> partsupp
customer/supplier -> nation -> region
```

Raw files are pipe-separated text. An actual local order row starts:

```text
1|36901|O|173665.47|1996-01-02|5-LOW|Clerk#000000951|0|...
```

This describes order 1, customer 36901, status O and total price 173665.47, followed by the other fields.

**TPC-H is generated benchmark data, not actual customer transaction data.** Validated dbgen output is suitable for controlled benchmark research; it is distinct from dummy data or fabricated measurements.

The full benchmark specifies 22 analytical queries and two refresh functions. Our current campaign uses six custom TPC-H-derived templates, not the complete compliant benchmark. See the [TPC-H specification](https://tpc.org/TPC_Documents_Current_Versions/pdf/tpc-h_v2.18.0.pdf).

Our six templates cover filtering, grouping, a two-table join, a three-table join, sorting/top results and a five-table supply join. The supply join does not scan lineitem and can expose shared-host interference separately from direct lineitem layout benefit.

### Explore the files

- [Schema: every table and column](../datasets/tpch/TPC-H-Tool/TPC-H%20V3.0.1/dbgen/dss.ddl)
- [Local SF1 raw data](../datasets/tpch/sf1/)
- [Official SQL templates](../datasets/tpch/TPC-H-Tool/TPC-H%20V3.0.1/dbgen/queries/)
- [Our six SQL templates](../three_model_maintenance/protocols/sf10_models_campaign02_20261026.json)
- [Saved SF10 inventory](../results/three_model_sf10_scratch_recovery_20261025_03/reuse_manifest.json)

Safe local preview:

```bash
head -n 5 "/media/shashank/Data1/PDocuments/Capstone/implementation/datasets/tpch/sf1/orders.tbl"
```

Recorded worker3 SF10 source directory:

```text
/mnt/nfs-storage/shashank_prafullathta/implementation/datasets/tpch/sf10_generated_20261024_02/
```

Scale factor describes approximate benchmark data volume, not compressed Parquet size, RAM usage or total experiment disk needs.

## 4. Alternative storage systems

Separate these layers: TPC-H supplies data/workload; Iceberg supplies table metadata, snapshots and file organization; Parquet stores columnar records; Spark executes queries.

Iceberg data-file compaction combines small files into larger files, reducing file-opening and metadata overhead. Payoff depends on layout and workload. [Iceberg documentation](https://iceberg.apache.org/docs/latest/spark-procedures/)

| Alternative | Maintenance operation | Assessment |
|---|---|---|
| Delta Lake | OPTIMIZE combines small files | Closest cross-format extension |
| Hudi Merge-on-Read | Merge update logs into base files | Strong ongoing read/write trade-off; needs genuine update workload |
| LSM-based systems | Merge sorted storage runs | Different research setting with substantial migration/literature work |
| Plain Parquet | Explicit file rewrites | Controlled baseline without table-format transaction machinery |

Sources: [Delta optimization](https://docs.delta.io/optimizations-oss/), [Hudi compaction](https://hudi.apache.org/docs/compaction/).

Recommendation: retain Iceberg as the primary system. Switching format merely to obtain a positive result does not fix the scientific question. Cross-format validation is useful after a reproducible mechanism is established.

## 5. Understanding Snowset and our timing replay

Snowset is a recorded workload trace. Its publishers describe approximately 70 million Snowflake queries over 14 days in February–March 2018. Each main-dataset row describes one query. [Publisher overview](https://github.com/resource-disaggregation/snowset)

The full trace contains identity, creation/end timestamps, durations, infrastructure information, storage/cache I/O, spill, networking, CPU/memory and operator-profile statistics. See the [publisher schema](https://github.com/resource-disaggregation/snowset/blob/master/schema.md). It does not provide original SQL text for our replay.

Our extracted arrival file retains just:

```csv
queryId,warehouseId,arrival_utc
8305634485816232694,4521920227430629158,2018-02-22T18:26:14.878000Z
3140896127011203291,4521920227430629158,2018-02-22T18:26:14.895000Z
8208596142661555319,4521920227430629158,2018-02-22T18:26:16.479000Z
```

These are actual exported rows: the second query arrives 17 milliseconds after the first, and the third 1.584 seconds after the second.

Replay preserves offsets from the selected historical window start and assigns benchmark SQL to each arrival:

```text
historical timestamp -> offset -> scheduled arrival
                     -> assigned benchmark SQL
                     -> queue -> dispatch -> completion/failure
```

Arrival time differs from execution start. If the system cannot keep up, backlog accumulates and remains visible. No dropping or time compression is used to make a run appear successful.

### Current choices and possible variations

| Parameter | Current choice | Future registered investigation |
|---|---|---|
| Warehouse | One selected on training-period volume | Multiple warehouses/rate strata |
| Windows | Chronological, nonoverlapping source windows | More days, longer periods, rising/falling demand |
| Physical horizon | 1,200 seconds | Longer horizons to observe deferred benefits |
| Arrival spacing | Original | Preserve for original-arrival claims |
| SQL assignment | Deterministic round-robin across six templates | Different explicit benchmark mixes, never claimed original SQL |
| Forecast bins | 60 seconds in count export | Other registered aggregation intervals |
| Host history | 60/300 seconds | Longer past-only context |
| Clients | One | Capacity-checked concurrency |
| Maintenance offset | 600 seconds in maintenance arm | Multiple preregistered action times |

The extracted cohort records 2,760,971 arrivals for warehouse 4521920227430629158. Selection used the most arrivals in the original seven-day training partition. It is a busy diagnostic cohort, not evidence of representativeness.

Timestamp fidelity preserves reported arrival behavior, not Snowflake hardware, original SQL, customer data or execution performance. Empty bins indicate no reported queries, not verified server idleness. Query count does not equal resource demand.

Retrospective runtime/resource fields cannot be treated as information available before the same query arrived, nor as compaction labels for our Spark/Iceberg system.

### Explore the files

- [Exact arrival CSV](../datasets/snowset/arrival_cohort_export_repair_20261014/observed_arrivals.csv)
- [Per-minute counts](../datasets/snowset/arrival_cohort_export_repair_20261014/observed_bin_counts.csv)
- [Cohort settings](../datasets/snowset/arrival_cohort_export_repair_20261014/cohort_config.json)
- [Cohort provenance and counts](../datasets/snowset/arrival_cohort_export_repair_20261014/cohort_record.json)
- [Arrival extraction](../scripts/extract_snowset_arrivals.py)
- [Benchmark mapping](../scripts/phase6-live-evaluation/prepare_trace_benchmark_mapping.py)
- [Forecast diagnostic](../scripts/evaluate_arrival_forecast_diagnostic.py)

The local arrival CSV is available offline. The full original Parquet corpus is not established as completely mirrored locally.

## 6. Research branches, team ownership and feasibility

These are hypotheses to investigate, not promised improvements.

| Branch | Question | Priority |
|---|---|---|
| Physical timing trade-off | Does compact-now versus compact-later repeatably change outcomes? | Highest |
| Fragmentation/scale | Where do file-open and rewrite costs become material? | High; SF10 before SF100 |
| Query complexity | Do plan features generalize beyond query IDs? | High; diverse/held-out SQL required |
| Model architecture | Shared or separate A/B? | High; code implemented |
| Forecasting | Does prediction beat persistence/seasonal baselines? | High; independent windows needed |
| Work-weighted demand | Predict service demand rather than counts? | Promising; honest mix assumptions required |
| Queue-aware scheduling | Reduce waiting and completion times? | Central eventual outcome |
| Partial maintenance | Rewrite a subset instead of one large operation? | Promising extension |
| Ingestion/deletes | Does growing maintenance debt strengthen the temporal trade-off? | Valuable new workload |
| Cross-format | Does the mechanism generalize to Delta/Hudi? | Later |
| Uncertainty/abstention | When should unsupported decisions be refused? | After sufficient independent data |
| Causal effects | Separate interference from layout improvement? | Requires stronger design |

Suggested division for the user and four teammates:

| Owner | Responsibility |
|---|---|
| User | Integration, frozen protocols, evidence ledger and paper argument |
| Teammate 1 | Physical effects: layouts, scale, rewrite duration, timing controls |
| Teammate 2 | Query complexity, architectures and baselines |
| Teammate 3 | Snowset exploration, demand regimes and forecasting |
| Teammate 4 | Queue outcomes, policy evaluation and independent audit |

### Recommended sequence

1. Recover remote terminal evidence when worker3 is available.
2. Establish a repeatable timing trade-off across matched layouts and independent episodes.
3. Compare shared/separate estimators and complexity features with honest coverage.
4. Establish forecasting skill against simple baselines.
5. Compare complete policies: immediate, fixed timing, current-load rules and forecast-aware timing.
6. Evaluate waiting/completion outcomes and maintenance completion over a common horizon; retain unfinished work.
7. Expand scale and systems when preceding evidence justifies it.

A strong paper needs a demonstrated maintenance-timing method, measured benefits, failure regimes and uncertainty. Training three models alone is not sufficient novelty.

**This is a viable final-year research project. A SIGMOD/VLDB-level outcome remains unproven and depends on demonstrating that temporal information improves useful decisions beyond strong simple alternatives. Preserve that question even if the eventual solution uses fewer than three learned models.**
