# Variables, metrics and experimental design

## 1. The comparison we actually want

The primary question is: **with the same query arrivals, starting layout and required rewrite, does choosing a different start time reduce the time users wait for results?**

An arm that skips maintenance entirely answers a useful diagnostic question, but it cannot win an equal-maintenance comparison by doing less work. Similarly, an arm that finishes only its easy queries cannot win by excluding unfinished requests. Freeze the offered population before execution, preserve every request, drain it fully, and record the completed maintenance obligation and final table state.

Start with one static table and one rewrite. A deadline, penalty or SLA is not present merely because it would make a controller easier to formulate. If maintenance must finish by a particular time, register that obligation and its operational reason before collecting the comparison. Until then, compare completed obligations without inventing a penalty coefficient.

## 2. Variable map

| Component | Initial control | Controlled variation later | Mechanism and interpretation | Main confounder |
|---|---|---|---|---|
| Data scale | Verified SF10 source and exact row multiset | SF100 after SF10 opportunity is established | More scan/rewrite work may change the useful scheduling region | Different cache fit, disk capacity and parallelism |
| Physical layout | Matched initial manifest/file distribution | Requested 16, 64, 256 files as capability candidates | File-open/planning costs versus scan parallelism | Requested counts may differ from actual output; compression and clustering also change |
| Query structure | Existing six verified SQL statements | Separately registered low/high scan, join, aggregation and selectivity mixes | Different queries respond differently to layout and contention | A changed mix changes baseline work as well as interference |
| Arrival pattern | One exact Snowset-derived arrival mapping within each block | Naturally observed lower/higher load and burstiness windows | Backlog and headroom determine when maintenance is costly | Source windows are observed conditions, not random treatments |
| Arrival time transformation | None | Only a separately labelled future stress study if justified | Changes intensity independently of SQL | Retiming no longer reproduces original trace arrivals; excluded from the initial programme |
| Client concurrency | One serial FIFO client | Verified two-client implementation after the serial study | Changes queueing and engine overlap | Existing serial accounting cannot certify concurrency |
| Maintenance action | One eligible full-table bin-pack rewrite, fixed options | Target size, file-group/incremental actions, partitions | Changes duration and amount of beneficial debt removed | Different actions are not a timing-only comparison |
| Maintenance start | Fixed registered offsets for action-value study | Same admissible start/wait choices for every policy | Temporary contention versus earlier benefit | Later starts can change snapshot usage and post-horizon work |
| Forecast | Persistence or observed-history baseline | Count forecast with a bounded development-only model search | Anticipates future arrivals relevant to rewrite duration | Leakage, inaccurate workload-to-CPU interpretation |
| Query cost model | Query/layout median | Shared state-conditioned model or separate A/B models | Estimates service consequence of state/layout changes | A/B sample imbalance and state/time confounding |
| Rewrite cost model | Simple measured duration/bytes baseline | Bounded learned duration/transition estimator | Predicts how long interference lasts | Few independent rewrites; input/output layout confounding |
| Uncertainty treatment | No learned interval claim | Independently calibrated intervals, if supported | May prevent fragile actions on unsupported states | Query rows are not independent calibration blocks |
| Host environment | One measured worker/backend configuration | Separate host/storage/budget study | Changes contention and resource trade-offs | Other users, cache state, thermal and storage effects |
| Observation machinery | One frozen verified implementation in all policy arms | Separate observer-cost experiment | Logging itself can alter response and resource work | Changing observer between policies invalidates the comparison |

The proposed numeric levels are a design shortlist, not physical registration. They require capacity checks, actual source identities and rationale in a fresh protocol. Do not force output file counts or silently replace unsupported settings.

## 3. Separate the three effects of compaction

1. **Permanent layout effect:** compare the same query on fragmented and compacted snapshots when no rewrite is running. Record actual scan/planning/task metrics. Fewer files alone is not a benefit: reduced parallelism can make some scans slower.
2. **Transient interference:** compare reads of the *same pre-rewrite snapshot* with and without an overlapping rewrite, when the engine supports verifiable snapshot pinning. This isolates contention from the later layout. A client-side maintenance-pending flag is not proof of active engine overlap.
3. **Timing effect:** execute a complete cohort while one rewrite starts at different registered times. This is the actual policy outcome, including waiting, service, changed snapshots, backlog and drain.

Do not estimate effect 3 by subtracting unrelated averages from effects 1 and 2. Those are mechanism diagnostics. A scheduling claim needs physical policy comparisons.

## 4. Exact response accounting

For request `i`, record a scheduled arrival `a_i`, actual first offer, dispatch, client execution start `s_i` and result fetch completion `f_i` using the same monotonic clock. Preserve UTC separately for provenance.

| Measure | Definition | Meaning |
|---|---|---|
| Response | `R_i = f_i - a_i` | Total user-visible delay relative to the registered arrival |
| Waiting before call | `W_i = s_i - a_i` | Generator lateness, admission/backlog and dispatch delay combined |
| Client service | `S_i = f_i - s_i` | Client execute-through-fetch duration; includes driver/engine/transport work |
| Generator lateness | `actual_offer_i - a_i` | Whether the replay apparatus itself fell behind |
| Full-cohort mean response | `sum(R_i) / N_offered` | Primary metric; available only after the complete offered cohort succeeds |
| Tail response | Nearest-rank p95/p99 over all offered-and-completed queries | A long-tail guardrail, not a substitute primary chosen after seeing results |
| Outstanding area | `integral N_outstanding(t) dt` from first arrival through final result | Must equal `sum(R_i)` for the same population and clock convention |
| Drain | `max(0, last_result - arrival_horizon_end)` | Work remaining after arrivals stop |
| Horizon throughput | Completed requests before the common arrival horizon | Useful secondary view; does not discard the remaining cohort |

The exact nanosecond identity `sum(R) = sum(W) + sum(S) = outstanding area` is an accounting check, not statistical independence. The new parser reconstructs it from the raw ledger and compares saved totals.

Record separately: offered, completed, failed, queued, active, unattempted arms, rewrite eligibility/start/end, successful rewrites, input/output bytes and files, row correctness, final debt, telemetry coverage and all unavailable measurements. A failed episode remains a failure. No finite timeout turns missing responses into zero or completed-only averages into the primary result.

## 5. Resource measurements

Resource reduction is a valid potential contribution, but it needs its own complete accounting. CPU percentage sampled at one instant is not total CPU work. Lower response time does not necessarily imply less CPU.

| Resource | Required evidence | Boundary |
|---|---|---|
| CPU core-seconds | Valid cumulative process/cgroup CPU counters, stable identities, all intended executors/controller processes and explicit intervals | Process totals only if ownership is known; host counters remain host totals |
| Engine task CPU | Actual per-attempt executor CPU counters with units and complete successful/failed/retried task inventory | Do not equate wall duration to CPU or silently ignore retries |
| Physical storage I/O | Valid process/cgroup/device counters, reset/overflow checks and complete observation intervals | Logical scan bytes, shuffle bytes and physical disk traffic are distinct |
| Rewrite work | Actual input/output bytes, files, duration and task work | Include unsuccessful attempts and required cleanup only when actually observed |
| Controller overhead | Feature acquisition, forecasting, model calls, planning, persistence and observer work | Existing 335-row inference timing covers only one part of this path |
| Peak pressure | Memory/process RSS, concurrent tasks and measured load with sampling coverage | Peaks are sample-dependent; no complete-peak claim from sparse sampling |
| Energy/cost | Calibrated meter or a registered resource-price model | Do not convert CPU percentage to joules or claim monetary savings without a model |

Measure through completion of **both the offered workload and required maintenance**, using a boundary that covers the later operation. Maintenance ending after the final query must still count. Distinguish measurement/audit overhead outside the operational boundary; publish it separately rather than hiding it.

The current response parser deliberately returns CPU/I/O as `null`. It cannot certify future resource comparisons. Existing final correctness SQL had no telemetry from the workload stream; do not retroactively invent that resource cost.

## 6. The smallest useful sequence

1. **Repeatability:** identical-action replicas establish noise and order effects before attributing differences to a policy.
2. **Layout curve:** three actual layout levels with fixed query/source conditions reveal whether there is any layout benefit to exploit.
3. **Timing curve:** first eligible start, midpoint and arrival-horizon end with one identical obligation. These are proposed offsets `0`, `H/2`, `H`, subject to eligibility and a new action/drain contract. The old runner's action-before-horizon restriction cannot be silently relaxed.
4. **Interaction screen:** a bounded 2×2×2×2 design for layout, natural load class, query mix and start time. Sixteen cells per block, not all variables simultaneously. Load windows must be chosen without looking at policy outcomes and mapped to exact source ranges.
5. **Focused policy comparison:** select development-supported regimes, then compare cheap policies and minimal learned ablations there and on representative boundary regimes.
6. **Frozen test:** untouched source families, predefined metrics, no retuning from errors.

Whole blocks need not run concurrently; isolate physical execution on the shared worker. Within-block order is counterbalanced and recorded. The design generator shuffles once using seed `20261113` and rotates positions across blocks. Exact position balance requires the block count to be a multiple of arm count; rotation is not a guarantee against carryover. Do not reset caches or restart services to make arms convenient. Use one registered warmup convention and measure/record order and environment.

## 7. Source families, leakage and independence

An episode is the atomic observational unit for splitting. Related replicas and all variants of a source window remain together. Include the entire feature-history, forecast-target and outcome range when finding overlap. Transitive overlap joins components: if A overlaps B and B overlaps C, all three belong together even if A and C do not intersect directly.

`research.design.overlap_families` implements this conservative grouping for actual dataset/warehouse identities and half-open time intervals. Disjoint groups are **not automatically statistically independent**. Same warehouse, adjacent days, repeated SQL mapping and shared host effects can still correlate them. Record warehouse/day/environment blocks and use time separation or higher-level grouping where warranted.

The four historical storage runs used in this unit share one overlap component. Their 12,376 query rows are not 12,376 independent experiments. The current 335-row A/B sample also does not support broad independence or calibrated-model claims. A source family already inspected for development is consumed for that purpose even when no model was fitted to it.

Maintain an immutable assignment manifest with roles: engineering, training, validation/model-selection, calibration, final test. Later refitting on combined development data is allowed only under a new explicit freeze protocol that preserves untouched calibration/test roles. It must not overwrite the previously frozen family-0 model or reuse an already-consumed reserved test as fresh.

## 8. Precision, decisions and multiple comparisons

Before confirmatory execution, choose a smallest worthwhile response improvement and acceptable tail/resource/debt deterioration using measured operating costs and the intended deployment. They are **unset today**. Do not select the threshold after observing the final test.

Use pilot **whole-block paired differences** to estimate variability and plan enough new blocks for a useful confidence interval. A rough normal-approximation planning calculation is `n ≈ ((z_(1-alpha/2) + z_(power)) * sd_paired / delta)^2`; it is not a guarantee, and skewed or dependent block data need more careful simulation using actual pilot blocks, not fabricated query-level independence. Register alpha, power, precision target, max blocks and stopping rule before the test. If those assumptions cannot be defended, report descriptive evidence and limit the claim.

Analyse paired differences within a family first, then aggregate family effects with a declared weighting. Equal-family means answer performance across source families; query-weighted means answer a different population question. Report both if useful, with one primary. For enough defensible blocks, use a paired family-level interval or block/bootstrap/permutation procedure appropriate to the randomization and dependence. Never bootstrap query rows as independent replicas.

Select one primary comparison before the test. Report all preregistered secondary comparisons; use a declared multiplicity correction such as Holm if making several confirmatory claims. Exploration across 34 cards does not provide 34 independent chances to declare success. Any discovered subgroup or newly selected metric requires a new untouched confirmation study.

Use fixed evaluation size or a genuinely preregistered sequential procedure. Repeatedly checking for a favorable result and stopping when it appears is not permitted. Infrastructure failures are retained by treatment and cause; do not silently remove failed arms or substitute a new source. If a protocol amendment is necessary, preserve the old cohort and start a separately identified study.

## 9. Decision outcomes

| Evidence | Decision |
|---|---|
| Physical evidence incomplete | Repair the identified blocker within the effort budget; no model/policy result |
| Layout benefit exists but timing spread is within a narrow practical-null interval | Prefer a cheap fixed policy; investigate a justified new action or a boundary paper |
| Timing matters, but forecast/model additions do not help | Retain the strong simple policy and publish the marginal-value result only if sufficiently supported |
| Learned policy improves the frozen primary comparison with acceptable registered guardrails | Candidate contribution in the tested regimes; evaluate transfer |
| CPU/I/O improves while response does not | Report secondary result; register a fresh resource-primary study before making that the main claim |
| High uncertainty or too few independent families | Collect justified new evidence or narrow the claim; do not relax gates |

No accuracy score, process screenshot, file-count reduction or successful audit by itself meets the project's outcome goal.
