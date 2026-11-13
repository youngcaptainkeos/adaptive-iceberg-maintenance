# Literature positioning and a defensible publication route

Reviewed against primary sources on 13 November 2026. This is a focused comparison, not an exhaustive novelty certificate. Historical detailed paper notes remain in `docs/novelty_comparison_2026-10-17.md`; later corrections in those notes take precedence over earlier tentative descriptions.

## 1. What is already known

| Work | Relevant existing contribution | Consequence for our study |
|---|---|---|
| [AutoComp](https://arxiv.org/html/2504.04186v1), 2025 | Automated compaction with candidate traits, cost/benefit selection, compute budgets and scheduling choices, including sequential and off-peak execution | Do not claim earlier compaction work ignores scheduling, resource cost or workload considerations. Compare to a clearly specified compatible implementation of those ideas, and label any adaptation rather than claiming full reproduction. |
| [PTO](https://vamsikrishna1902.github.io/publication/SIGMOD-2026), SIGMOD 2026 | Workload-driven predictive selection of lakehouse organization parameters, including partitioning, target file size, row groups and rewrite strategy | A learned layout estimator or query-aware file sizing is not enough to distinguish us. Our proposed start-time study holds the rewrite choice fixed initially. |
| [SILK](https://www.usenix.org/conference/atc19/presentation/balmau), ATC 2019 | Addresses LSM foreground/background interference through I/O scheduling, low-load opportunities, priorities and preemption | Quiet-period scheduling and protecting foreground latency are established ideas. Its engine-internal, preemptible LSM setting differs from our external non-preemptive lakehouse action. |
| [SOPHIA](https://www.usenix.org/conference/atc19/presentation/mahgoub), ATC 2019 | Combines workload prediction with transition cost/benefit to plan when and how to reconfigure NoSQL systems | Forecast plus transition-cost planning is not novel by itself. We need a precise lakehouse decision problem and measured advantage. |
| [NoisePage architecture](https://www.vldb.org/pvldb/vol14/p3211-pavlo.pdf), PVLDB 2021 | Separates workload forecasting, behavior modelling and action planning in self-driving DBMS operation | A three-component architecture is a useful organization, not our paper's novelty claim. |
| [How Good are Learned Cost Models, Really?](https://arxiv.org/abs/2502.01229), SIGMOD 2025 | Evaluates learned costs through actual optimization tasks and finds traditional models often competitive or better | We must evaluate decision outcomes against strong simple methods, not sell lower prediction error as a systems improvement. Its tasks differ from our maintenance problem. |
| [Smart Compaction](https://arxiv.org/abs/2608.08639), August 2026 preprint | Studies metadata-based compaction utility; reports a simple threshold for its binary decision and query-dependent effects of compaction, including loss of scan parallelism | Treat file-reduction prediction and “compaction can hurt” as existing work. Our outcome must be actual complete-cohort response/resource work under controlled maintenance timing. A preprint is still relevant prior work. |

These comparisons support a **candidate distinction**, not an established novelty claim: an auditable external Iceberg controller that jointly accounts for existing backlog, temporary rewrite interference, the later layout effect and a completed maintenance obligation, while showing when forecasts or learned costs add value over an inexpensive rule. Whether this distinction is sufficiently new depends on the final algorithm, exact comparisons and evidence.

## 2. Two plausible paper routes

### Route A: an effective, lightweight timing method

Possible research question:

> Can an external controller improve complete-cohort response by choosing when a fixed eligible rewrite starts, using past-only demand and measured state-dependent costs, after accounting for controller overhead and equal maintenance work?

Necessary evidence: useful timing sensitivity, mechanism isolation, strong fixed/reactive/predictive baselines, a real learned-versus-simple ablation, independent frozen evaluation, complete resource/response boundaries and one credible transfer dimension. A complicated model is optional. If a simple predictive method wins, describe that method honestly.

### Route B: when learned maintenance timing is worth its cost

Possible research question:

> Which combinations of layout debt, query sensitivity, demand pressure and rewrite duration create enough action value for learned timing to outperform a cheap rule?

Necessary evidence: a controlled regime map, well-measured repeatability, narrow practical-null intervals in no-benefit regions, informative ablations and reusable evaluation artifacts. This route can accommodate mixed or negative results. It cannot be supported by a failed pipeline, sparse unrelated runs or low-powered “no significant difference” statements.

An observer-overhead study is another distinct branch if its mechanism and generality can be demonstrated. The historical storage-placement contrasts are engineering evidence and share one source component; they are not proof of learned scheduling improvement.

## 3. Fair literature baselines

Separate **published method**, **available artifact**, **our reimplementation** and **inspired baseline** in the paper. Record version, supported features, changed assumptions and tuning budget. If a paper's system cannot run in our environment, do not use its published numbers as a direct performance comparison against our worker.

The minimum executable ladder is fixed/periodic starts, a bounded reactive queue rule, a simple forecast with median costs, learned forecast only, learned costs only and the combined candidate. Add a compatible AutoComp-inspired candidate/threshold policy when action scope permits. SILK and RocksDB are contextual comparisons unless the project explicitly implements a separate LSM study; they are not drop-in Iceberg timing policies.

The original model-selection result where the query/layout median was strongest must remain visible. It motivates this baseline ladder. It does not prove ML will never help, and it does not justify endlessly searching architectures on the same consumed test family.

## 4. Dataset and workload statement for the paper

TPC-H supplies the benchmark data and SQL in our implementation. Snowset supplies observed arrival timing and workload statistics; the original private SQL is unavailable. The accurate phrase is **trace-driven benchmark workload**, not “replaying real Snowflake queries.” Verify actual extraction/window identities, timezone, mapping, row hashes and feature history in each registration. The [Snowset project repository](https://github.com/resource-disaggregation/snowset) is the primary reference for trace scope and available attributes.

Describe the actual six-statement subset, tables touched, query structure and scale used in the experiment. Do not imply that every TPC-H query or every table is exercised merely because the dataset is derived from TPC-H. Distinguish verified SF10 rows from a plan to use SF100. Scaling data alone does not produce independent workload families.

For physical operations, cite the matching [Iceberg procedure documentation](https://iceberg.apache.org/docs/1.4.3/spark-procedures/) and record the actual running engine/library versions once reachable. A documented API is not proof that our backend supports every option.

## 5. Alternative storage branches are separate hypotheses

[Delta Lake's compaction documentation](https://docs.delta.io/optimizations-oss/) describes bin-packing optimization; it is a plausible portability study after a working Iceberg mechanism. [Hudi compaction](https://hudi.apache.org/docs/compaction/) addresses merging log data into base files for Merge-on-Read tables, which changes the maintenance/debt semantics. An LSM pivot requires a fresh comparison against mature storage-engine work such as SILK and subsequent literature. Switching formats is not evidence that the original timing idea works.

For a larger factor space, the [NIST design handbook](https://www.itl.nist.gov/div898/handbook/pri/section3/pri334.htm) explains fractional-factorial designs and their trade-offs. Our initial interaction screen is the complete 16-cell design for four two-level factors. If we later fractionate it, disclose which interactions are aliased and do not claim all effects are separately identified.

## 6. Paper structure and figures

| Section | What to demonstrate | Planned figure/table |
|---|---|---|
| Problem and motivation | Why the timing choice matters under a fixed maintenance obligation | Real timeline of arrivals, backlog, rewrite and final layout |
| Scope and mechanism | Permanent layout benefit versus transient interference versus queue effects | Controlled layout curve and snapshot-pinned interference comparison |
| Method | Exact observation/action contract and simplest effective decision rule | Architecture and short action-selection pseudocode |
| Data and implementation | Trace mapping, dataset subset, physical environment and evidence integrity | Dataset/source-family table, hardware/configuration table |
| Baselines and experimental design | Same work, same admissible actions, split roles, frozen primary comparison | Protocol and factor table; consumed versus untouched source ranges |
| Main results | Actual response and tail/resource effects across independent blocks | Paired effect plots with registered intervals; no fabricated error bars |
| Component value | Whether forecasts, costs, separate A/B and uncertainty matter | Same-planner ablation with overhead next to benefit |
| Boundaries and transfer | Where the method fails or offers no useful gain | Regime map, error/abstention rates, SF100 or environment transfer if completed |
| Reproducibility and limitations | How to reproduce each conclusion and what is unsupported | Raw-to-figure manifest and complete failed/unattempted inventory |

Use genuine measured values only. Empty planned panels stay labelled “not measured.” Review screenshots can show real implementation progress, but paper evidence needs interpretable measurements and reproducible analysis, not merely processes running.

## 7. Submission readiness

Before choosing a venue, require a sentence stating the actual new result, a direct explanation of how it differs from the closest work, and enough independent evidence to defend it. Check current venue scope, paper length, artifact requirements and deadlines when a submission is realistic; no venue acceptance is promised here.

A top-tier submission will likely need stronger breadth and rigor than a few days of engineering can provide. The near-term deliverable is a decisive, valid opportunity study. If that shows no useful timing signal, narrow or change the research question on evidence. If it shows a signal, build the smallest method that captures it and spend the remaining effort on independent validation rather than extra model complexity.
