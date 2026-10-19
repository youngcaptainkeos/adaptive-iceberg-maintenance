# Literature and novelty assessment — 17 October 2026

## Verdict and review scope

No defensible SIGMOD/VLDB-level novelty is established by the current three-component architecture, layout-aware median, learned rewrite predictor, or general instruction to wait for a quiet period. Existing work overlaps all of those ideas. The implementation is a useful experimental platform, not yet a demonstrated research contribution. A narrowed Iceberg decision problem remains worth investigating, conditional on a distinguishing mechanism and physical evidence.

Reviewed primary-source methods/limitations: AutoComp PDF sections4–8; Smart Compaction full HTML; NoisePage architecture paper section3 and Lin Ma thesis chapters4–5; SOPHIA design/evaluation sections2/4/6; PTO author's abstract and ten-page appendix. PTO's main ACM PDF could not be retrieved in this session: claims about capabilities absent from its full paper remain UNKNOWN. This is a focused review, not exhaustive prior-art clearance. Direct primary references below, no quotations.

## Closest work: evidence, scope and implication

| Work | Direct evidence and locator | Implication / limit of conclusion |
|---|---|---|
| [AutoComp, SIGMOD Companion2025](https://www.cs.umd.edu/~abadi/papers/autocomp-sigmod.pdf) | Sections4.2–4.3 estimate file reduction and compute cost, rank under a budget. Section4.4 explicitly permits same-cluster execution, dedicated maintenance clusters, sequential execution and predictable off-peak deferral. Section6 runs concurrent workload experiments; section8 leaves richer workload traits as future work. | Quiet-period deferral, resource awareness and compaction cost-benefit are already discussed. Did not locate an implemented, quantitatively evaluated arrival-forecast/queue-aware start-time optimizer in these sections. This narrower observation is not proof the extensible system cannot support one. |
| [Smart Compaction, arXiv2608.08639v1, Aug2026](https://arxiv.org/html/2608.08639v1) | SectionII-A target is bin-packing file-reduction ratio, not query latency. SectionIII-I5 identifies static snapshots/temporal evolution as limitations; III-I7 says full economic cost-benefit is future work. Query benchmark shows some scans slow after compaction. | A metadata-based predictor or observation that fewer files need not mean faster queries is not our novelty. A scheduling contribution must optimize actual workload outcomes, beyond structural reduction. Treat as a preprint; do not assert a peer-reviewed venue from copyright text. |
| [PTO, SIGMOD2026, author publication](https://vamsikrishna1902.github.io/publication/SIGMOD-2026), [appendix](https://vamsikrishna1902.github.io/files/SIGMOD-2026-appendix.pdf) | Author describes query-frequency/selectivity heuristics, table sampling and gradient-boosted trees to choose partitioning, target file size, row groups and sort layout. Appendix supplies layout/candidate experiments. | Layout-aware query optimization is established. Evidence read supports a layout-selection comparison, but the main paper is unavailable here: do not fill its timing/interference/uncertainty cells with NO. |
| [NoisePage, PVLDB2021](https://db.cs.cmu.edu/papers/2021/p3211-pavlo.pdf), [Lin Ma thesis2021](https://www.csd.cmu.edu/sites/default/files/phd-thesis/CMU-CS-21-134.pdf) | Architecture section3 uses forecasts, behavior models, interference models and receding-horizon/MCTS planning. Thesis4.4 models concurrent resource competition; chapter5 plans actions across time intervals and handles action duration. | Forecast plus action cost plus interference plus planning is already established. NoisePage's integrated engine models are different from an external Spark/Iceberg controller, but changing the engine alone is insufficient novelty. |
| [SOPHIA, USENIX ATC2019](https://www.usenix.org/system/files/atc19-mahgoub.pdf) | Sections2/4 combine workload prediction with time-varying reconfiguration cost-benefit. Section4.3 optimizes when/what to change over a horizon. Compaction-method changes are costly tunables; section6 experiment6 tests noisy forecasts. | Timing, temporary performance harm, value of waiting, and robustness testing all have prior art. Distinguish Cassandra/Redis reconfiguration from scheduling Iceberg rewrites; do not describe this as an existing Iceberg scheduler. |

Correction to prior discussion: AutoComp uses a weighted normalized trait score in its presented ranking; Pareto-frontier exploration is future work in section8. A secondary paper's description must not replace the primary method. Likewise, merely adding uncertainty tests would not distinguish us from SOPHIA's forecast-noise experiments.

## Contribution claims rejected or still unproven

- Query/file-count median: empirical baseline, no established novelty; this review did not identify the exact identical lookup rule, and does not need that identity to reject a publication claim based on it alone.
- Three learned models: architectural choice, not contribution. Low latency-prediction error need not yield better actions; pointwise MAE is not a scheduler objective.
- Predict future low load and defer: directly overlaps AutoComp's scheduling discussion and general anticipatory tuning.
- Model interference: already present in NoisePage; need a materially different modeling problem/mechanism.
- Forecast-aware cost-benefit or receding-horizon control: overlaps NoisePage/SOPHIA. A generic MPC implementation is not enough.
- Forecast uncertainty: potential specific technical mechanism, but uncertainty/robustness alone is established. Need precise risk assumptions, decision rule, comparison and evidence.
- Real-data/open reproducibility: valuable evaluation/system artifact, but not on its own a research algorithmic novelty guarantee.

## What our current evidence actually says

Current scripts train compact latency models on query ID/file count/client-pending state and rewrite models on file count. No forecast features or learned scheduler are implemented in this comparison. Full60/300s offered history is an eligibility filter, not a demand-aware feature. Family0train1validation2test; third family now consumed. Heldout primary layout median20.3430ms equalepisodeMAE versus tree20.9283/logRidge21.5426; no learned-query win. Four heldout rewrites cannot establish general cost accuracy.

Data support a more serious experimental concern: reading the existing18episode CSV yields1526–1610offered queries and958–1056still queued per episode, approximately62.8–65.9percent queued at final census. These are counts from saved receipts, not new runs. The setup is heavily overloaded at the chosen single-client dispatch configuration. Lower future arrival rate therefore does not imply an idle server: existing queue debt may keep it occupied. More accurate forecasting is not automatically the dominant missing component.

Furthermore, the eligible latency comparison drops early requests, including early compact-now interference, and measures service time rather than total response time/debt. It cannot establish that one maintenance start time is best. Current one-rewrite/static-layout episodes lack continuing real ingestion/layout deterioration; a perpetual-maintenance story needs that additional evidence. Four custom SF1queries with no original Snowset SQL limit workload validity. These limits neither invalidate the saved baseline comparison nor become evidence for a new claim.

## Most promising hypothesis, explicitly not a verified gap

Investigate an external Iceberg controller that decides whether to start a rewrite or wait by estimating end-to-end queue consequences across the rewrite's uncertain duration and workload-dependent post-rewrite layout change, using only causally available observations. Distinguish arrival quietness from queue drain and compute occupation. A compact state model may be preferable to three regressions.

Potential technical contribution would have to be one of: a new validated queue/layout transition model that materially improves timing; a decision rule with a justified risk/decision-margin property under stated forecast/model errors; or a systems mechanism obtaining these decisions with substantially less intrusive measurement than a generic planning approach. None is currently implemented or proven novel. Snapshot visibility/commit semantics and nonuniform query benefits are Iceberg problem constraints, not automatically new algorithms.

Do not specify an arbitrary weighted scalar or SLA merely to obtain rankings. Freeze a measurable whole-horizon objective and account for unfinished work and end-state differences. A controller must not win by shifting maintenance or queue debt beyond the observation horizon. If a horizon-end penalty is chosen, its meaning and sensitivity require explicit registration.

## Minimum decisive experiment before another large collection

1. Define the decision objective and a small preregistered set of start times/noaction. Choose real source windows and verified layouts using criteria fixed before physical outcomes. Preserve original arrivals, queue conservation and natural operation completion. This document authorizes no physical launch.
2. Start with a retrospective perfect-future diagnostic, not a deployable forecast: ask whether different action times can materially improve the chosen objective over current-state/quiet-window rules at all. Include maintenance cost and terminal queue/layout state. Absence of robust timing headroom is a stop signal; do not build a larger forecaster first.
3. Use measured, fresh matched physical action/control episodes, multiple independent source blocks and registered ordering/replication. Historical sequential arms can motivate a hypothesis but are not paired counterfactual proof; cache/drift and single-client saturation can dominate.
4. If headroom exists, compare a strong current-state controller, predicted-quiet-window baseline, conventional forecast-plus-cost horizon planner adapted honestly from published principles, and our precise mechanism. Label adaptations/reimplementations, not original systems, unless faithfully reproduced. AutoComp's multi-table ranking may be weak in a one-table task; extend scope or explain the narrowed comparison rather than claiming to defeat all of AutoComp.
5. Ablate queue state, future demand, interference/post-layout estimates and the proposed risk mechanism on the same new blocks. Future-observation oracle is diagnostic only. Do not shuffle, synthesize or compress demand to manufacture uncertainty; evaluate naturally realized forecast errors and prospectively registered restrictions on available history/modeling.
6. Gate success on independent block-level decision outcomes and justified uncertainty/precision, not improved per-query MAE or a single best trace. Reusing today's test family after design changes makes it development history. Need new untouched physical-cost evaluation/calibration blocks; the demand forecast has its own historical partition/provenance constraints.

## Recommendation and outstanding literature work

Do not restart model tuning or a large physical batch yet. Next concrete deliverable is a one-page decision formulation, faithful baseline specifications and a small headroom/identifiability protocol. If those produce no separable mechanism and no measurable timing effect, narrow the final-year project claim or pivot; neither venue aspirations nor a three-model diagram establish a gap.

Before a final novelty claim, obtain the PTO main text, finish detailed comparison with dynamic LSM work such as [ArceKV](https://www.vldb.org/pvldb/vol19/p958-liu.pdf), and expand the search to predictive indexing, robust physical design and maintenance scheduling. The retrieved [Predictive Indexing preprint](https://arxiv.org/abs/1901.07064) is an explicit additional lead, not yet a fully reviewed comparator. No exhaustive claim of first forecast-aware/uncertainty-aware controller is supported here. No code/models/test outcomes changed or new experiments launched during this literature review.

## 19 October follow-up: dynamic compaction overlap

Reviewed [ArceKV's primary PVLDB paper](https://www.vldb.org/pvldb/vol19/p958-liu.pdf), sections3.2–4, pages962–964. Its state evolution delays compaction effects until a later window after completion. Its objective considers costs across compaction sequences; short-term choices can miss longer-term gains. Simulation selects parameters for a score-based decision engine, using workload statistics and recomputation when conditions change. This is substantial prior art for transition-aware, workload-dependent compaction optimization—not merely static file ranking. The reviewed mechanism operates inside RocksDB/ElasticLSM. These sections do not establish that ArceKV solves our exact external Iceberg FIFO response-time problem; they also do not prove it cannot be adapted. No experimental comparison with ArceKV has been performed.

Our inference: delayed layout effects, simulation, dynamic compaction decisions and short/long-term cost tradeoffs must not be presented as standalone novelty. The prototype's exact scheduled-arrival/full-drain accounting and snapshot-pinned query semantics are concrete implementation/evaluation choices. Their existence does not establish a new algorithm. A publication claim still requires a distinct mechanism and independent physical evidence beyond this single-day feasibility study.

PTO main text remains unresolved. The [author's publication page](https://vamsikrishna1902.github.io/publication/SIGMOD-2026) links DOI10.1145/3786681; its publisher redirect returned403 in this review. Existing local PTO PDFs produced no text with pdftotext, and no local OCR executable was available. Do not interpret that extraction/access limitation as evidence that PTO lacks timing or interference features. Earlier abstract/appendix conclusions remain qualified; a full main-text comparison is still an open requirement before novelty claims.

This literature follow-up changed no physical protocol, policy, model or ongoing run. It is analysis of primary sources, not a runtime validation job.

## 19 October correction: PTO main text visually reviewed

This supersedes the earlier main-text access limitation for the saved version.
The publisher redirect still returned403, but the repository already contains
all26pages of the main paper as an image-only PDF. Using the PDF skill, rendered
and visually inspected pages1–26; methods, evaluation and discussion were read
from those page images. No OCR output was assumed. Source:
[saved PTO main paper](<literature survey related to autocomp citeations/PTO.pdf>),
SHA256 `73066a4750e01236ea194464f28b08452ec1c9542b79e98ec2c83152bd6029c3`,
DOI [10.1145/3786681](https://doi.org/10.1145/3786681). Page numbers below are
printed article pages67:1–67:26, not a website excerpt. Numerical tables14/21
were inspected as rendered; this note does not transcribe every configuration.

| Question | Main-paper evidence | Defensible comparison |
|---|---|---|
| What is predicted/optimized? | Section2.2 p4 maximizes skipped rows over input workload/tables. Sections3.3.1–3.3.2 pp10–11 define layout features and skipping-benefit targets for per-table gradient boosting. | Its predictor concerns layout skipping, rather than our measured whole-query-call and rewrite-duration components. This does not make our empirical models novel. |
| Is maintenance execution cost part of layout scoring? | Section3.2.3 p7 footnote1 explicitly excludes final compaction time from sort-strategy scoring and suggests adding estimated compaction latency to skipping benefit as an extension. | We can state this specific omission for the presented scoring method. We cannot claim the authors overlooked maintenance cost entirely or that PTO cannot be extended. |
| Does it consider optimization overhead? | Section4.2.2 pp15–16/Table3 reports component/application times and treats discovery as an offline background step. Section5 item2 p22 permits stopping table optimization under a latency budget. | PTO does account for optimization effort operationally; “PTO ignores all costs/budgets” would be false. Our response-time objective and separate maintenance reporting differ from that budget. |
| What about online operation and drift? | Introduction contribution7 p3 says evaluation is offline and envisages periodic background use. Section5 item4 p23 describes periodic batched reruns, no automatic workload-drift detection, and redesign needed for concurrent real-time ingestion. | A forecast-driven FIFO start-time controller is not the evaluated mechanism described here. Do not generalize this into a claim that all dynamic behavior is absent: periodic adaptation and updated workloads are discussed. |
| Is full query workload evaluated? | Section4.1.1 p11 uses22TPC-H/103TPC-DSqueries atSF10,000; Section4.2.1 p13 evaluates workload execution on optimized tables; Section4.5 pp20–22 separately uses scan fragments on selectedSF30,000tables. | Our SF1/four-template study cannot claim comparable scale or workload breadth. No head-to-head execution was performed. |

Our inference from the reviewed methods: the exact arrival-time/backlog/full-drain
start/wait objective is a different evaluated problem from PTO's layout selection.
That establishes a comparison boundary, not an open-field or first-of-kind
claim. NoisePage/SOPHIA/ArceKV still overlap anticipatory planning, interference
and transition reasoning. A sound paper should compare timing over fixed,
justified layouts, or evaluate a faithful layout-selection integration under
common resources; it must not relabel an immediate-binpack baseline as PTO.
Neither experiment has been added or implied by this literature review.

PTO access is no longer the outstanding uncertainty for this saved version.
The outstanding gates are our actual complete physical comparison, independent
source blocks, a distinct validated mechanism, and a broader prior-art search.
The active frozen physical study and all predictions remain unchanged.
