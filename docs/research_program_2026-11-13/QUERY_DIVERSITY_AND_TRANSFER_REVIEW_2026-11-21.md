# Query diversity, benchmark reuse and transferable scheduling ideas

Recorded 21 November 2026. Literature/source review only. No runtime validation, scientific experiment, fitting, SSH operation or code modification. The new full-drain adapter remains unvalidated. Recommendations below are prospective, not accepted policies or an exhaustive novelty review.

## What the current six statements cover

The saved SF10 configuration contains six custom, fixed-literal statements. These are TPC-H-derived statements, not the standard complete TPC-H query workload.

| ID | Name | Main mechanism | Directly reads intervention lineitem? |
|---|---|---|---|
| 0 | filtered_revenue | Date filter plus count/revenue aggregation | Yes |
| 1 | grouped_lineitem | Full scan with low-cardinality grouping | Yes |
| 2 | orders_lineitem_join | Two-table join with a date filter | Yes |
| 3 | customer_orders_lineitem_join | Three-table join and aggregation | Yes |
| 4 | group_sort_top_parts | Filter, high-cardinality grouping, sort/top-k | Yes |
| 5 | five_table_supply_join | Five-table supply-side join | No |

The last statement is useful as a declared interference control, not a direct lineitem-layout-benefit example. Table/join count alone cannot predict maintenance sensitivity: the five-table query does not access the rewritten table, while a simpler scan does.

Repeats add timing observations, not new SQL structures or independent source families. Fixed literals also keep selectivity comparatively narrow. A query/layout median may be a strong estimator in this regime without establishing that learned query costs are universally unnecessary. More templates alone do not establish additional independent scheduling blocks.

Supported current use: controlled integration and mechanism investigation. Unsupported current use: arbitrary analytical-SQL generalization, realistic original Snowflake query replay, or production-wide learned scheduling advantage. These limits do not invalidate the benchmark rows or imply fabricated labels.

## Primary-source reading map

Each link was inspected in this review. Short findings are intentionally separated from our proposed adaptation.

| Source | Relevant finding / reuse |
|---|---|
| [Cloud Analytics Benchmark, PVLDB 2023](https://www.vldb.org/pvldb/vol16/p1413-renen.pdf), [author artifact](https://github.com/alexandervanrenen/cab) | Snowset-motivated workload construction; generated benchmark streams, not original private SQL. |
| [AutoComp, SIGMOD Companion 2025](https://www.cs.umd.edu/~abadi/papers/autocomp-sigmod.pdf) | Production and public benchmark tracks; CAB/LST-Bench connection. Inspect each experimental setup separately. |
| [PTO, author page](https://vamsikrishna1902.github.io/publication/SIGMOD-2026), [appendix](https://vamsikrishna1902.github.io/files/SIGMOD-2026-appendix.pdf) | TPC-H/TPC-DS layout tuning; different action and scale from our start-time study. |
| [OReO, ICDE 2024 paper](https://cs.stanford.edu/people/paulliu/files/icde-2024.pdf) | Online layout reorganization; public benchmark subsets and private telemetry; Metrical Task Systems already transferred to databases. |
| [LST-Bench paper](https://jesus.camachorodriguez.name/_media/publications/lst-bench-sigmod2024.pdf), [official workload library](https://github.com/microsoft/lst-bench/blob/main/docs/workloads.md) | Reusable table-format workload definitions; read/write and lifecycle evaluation. |
| [DSB, PVLDB 2021](https://www.vldb.org/pvldb/vol14/p3376-ding.pdf), [author repository](https://github.com/microsoft/dsb) | TPC-DS-derived skew and configurable changing workloads. SQL dialect porting still needs validation. |
| [JOB original paper](https://www.vldb.org/pvldb/vol9/p204-leis.pdf) | IMDb relational data and query diversity; join optimization, not maintenance evaluation. |
| [Smart Compaction, arXiv v1](https://arxiv.org/html/2608.08639v1) | Metadata/file-reduction target and released artifact differ from our end-to-end response objective. |
| [SILK, USENIX ATC 2019](https://www.usenix.org/system/files/atc19-balmau.pdf) | Background I/O interference and opportunistic work; includes controls unavailable to our current external adapter. |
| [Idle Time Garbage Collection Scheduling, PLDI 2016](https://research.google/pubs/idle-time-garbage-collection-scheduling/), [paper](https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/45361.pdf) | Duration-aware fitting of background work into idle opportunities. |
| [Heracles, ISCA 2015](https://research.google/pubs/heracles-improving-resource-efficiency-at-scale/) | Feedback-controlled resource sharing, with isolation mechanisms. |
| [Improving Online Algorithms via ML Predictions, NeurIPS 2018](https://proceedings.neurips.cc/paper_files/paper/2018/hash/73a427badebe0e32caa2e1fc7530b7f3-Abstract.html) | Prediction-assisted decisions with robustness; theorem assumptions need separate mapping. |
| [Workload Driven Index Defragmentation, ICDE 2010](https://www.microsoft.com/en-us/research/publication/workload-driven-index-defragmentation/) | Workload-sensitive reorganization and granularity; related ideas predate lakehouses. |

CAB is particularly relevant to our timestamp/SQL mismatch, but is not a reconstruction of missing Snowset SQL. Retain actual trace-arrival evaluation under the current project contract. A generated-arrival CAB track would require a separately approved and preregistered benchmark change; never silently substitute generated demand for unavailable real evidence. Its original load calibration cannot be assumed valid for worker3.

## Recommended research design: isolate effects before adding dimensions

1. Preserve the six-statement integration suite so capture/attribution repairs are comparable. Its small size is useful for engineering.
2. Expand the research suite using supported official TPC-H templates and registered standard parameter variants on the existing schema. Target coverage of scan/pruning, joins/shuffle, grouping/sort, subqueries and intervention-insensitive controls. Report unsupported templates and every SQL adaptation. Independently verify each result. This is TPC-H-derived scheduling research unless the complete official benchmark procedure is followed.
3. Keep a prespecified template-held-out evaluation separate from parameter-held-out and source-window-held-out evaluations. Do not repeatedly test on the consumed family or treat literal variants as independent structures. Scope any claim to the split actually tested.
4. Keep real arrival windows intact. Characterize capacity on the intended actual initial layout/query mix before selecting development workload strata. Freeze the selection rule before validation/test. Never use original Snowflake duration/CPU outcomes as if they were Spark costs or pre-arrival query features.
5. Use one additional generalization dimension after the mechanism is stable: preferably a small TPC-DS/LST-Bench-compatible workload with independent windows. DSB is useful if drift/selectivity is the question; JOB/IMDb is useful if cross-schema query-cost generalization is the question. Do not add all simultaneously.
6. Hold query/data/layout/observer/maintenance obligation fixed for the first timing contrast. Every primary arm completes the same offered work and required rewrite. Partition/file-group scheduling, ingestion and resource budgets are separate future experiments and new contracts.

## Proposed duration-aware scheduling hypothesis

Test whether the relation between quiet-window length and rewrite duration explains when timing can reduce full-cohort response. This is our proposed adaptation, not a measured finding. Use measured backlog and past-only estimates of query-sensitive demand, rewrite duration and during-rewrite slowdown. A quiet arrival period is not necessarily an empty execution queue.

Compare a registered fixed-time baseline, a reactive queue/slack rule, and a duration-aware forecast-assisted rule, with identical action obligations and actual observer/inference overhead. Missing inputs remain missing; no replacement prediction is invented. If forecasts do not beat the cheap rule on independent blocks, retain the negative finding rather than adding a more complex architecture by default.

The cross-domain mappings have strict limits. GC idle deadlines can be supplied by a browser scheduler; ours are uncertain. SILK can preempt/control internal I/O; our current Iceberg SQL call cannot be treated as safely interruptible. Heracles relies on resource isolation; CPU utilization alone is not a complete contention signal. Ski-rental/MTS assumptions do not automatically hold for queue-dependent non-preemptive rewrites with a mandatory completed action. No transferred competitive guarantee is claimed.

A possible later file-group/partition-sized action can make long rewrites fit shorter quiet periods, but only under a new protocol that fixes the full eligible required work set, validates all commits and includes extra metadata/commit overhead. This is not permission to pause, cancel or kill a running rewrite or claim that a partial rewrite fulfills the original obligation.

## What would justify proceeding or stopping

Continue to learned timing only if layout sensitivity and temporary interference are both measured and at least one timing contrast changes the prespecified end-to-end outcome reproducibly. Evaluate mean response as the primary outcome; tail response/drain and attributable resource work are separate registered outcomes, not posthoc alternatives chosen for significance. If full-drain comparisons are null, first inspect workload eligibility, duration ratios and capacity; do not assume another dataset or ML architecture will rescue the result.

Novelty is not established by using ML, three models, off-peak maintenance, or bringing an existing idea to a new file format. A defensible contribution needs a specific new decision method or demonstrated boundary, comparisons to the closest maintenance/layout papers and cheap rules, and independent physical evidence. The existing capture failures, incomplete dependencies and unvalidated full-drain code are unchanged by this literature review.
