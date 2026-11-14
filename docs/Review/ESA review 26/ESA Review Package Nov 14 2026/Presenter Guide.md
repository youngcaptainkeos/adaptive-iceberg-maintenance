# Presenter Guide — ESA Phase 1 Review

**Project title:** Workload-Aware Scheduling for Data Processing Systems
**Deck:** 25 slides; use this guide in the same order.
**Audience:** reviewers who need the problem, implementation and evidence boundaries explained clearly.

## The project in one minute

Large analytical tables can accumulate many small data files. Compaction rewrites those files into a layout that may help later queries, but the rewrite consumes compute and storage resources while queries may be waiting. Our question is whether workload forecasts and the current FIFO query queue can help decide when to start that maintenance. We built a Spark and Iceberg testbed, measured query and queue behavior, and developed separate candidate estimators for query service time, arrival demand and rewrite duration. The latest work ran six real SF10 queries, checked their pinned outputs, passed a saved-record audit and reconciled 168 executed tasks. Evidence capture still failed its completeness check for two missing dependency-stage records. This is measurable execution and audit progress, not a compaction or scheduling-benefit result. A fresh matched timing comparison is still ahead.

## Important language and evidence boundaries

- **Service time** is the measured query execution-and-fetch interval in the current collector. **Response time** is the user-visible time from offered arrival until result, including queue waiting. Do not call a service-time result a response-time result.
- **Model A** estimates query service time when a maintenance request is pending. **Model B** estimates service time without a pending request, conditional on the observed layout. Neither condition alone proves physical interference.
- **Model C** forecasts the number of future offered query arrivals over a registered time horizon. It does not predict CPU load or reconstruct Snowflake's original SQL workload.
- A separate rewrite estimator predicts the duration of maintenance and its resulting physical change. It is not calculated by subtracting A and B.
- The queue-aware controller observes arrivals, the FIFO backlog and layout; estimates query service, future arrivals and rewrite duration; chooses start, wait or no action; then evaluates the full cohort. It is a proposed next evaluation, not an accepted winning policy.
- An earlier Nov 13 diagnostic reported **308** in two separate units: disputed job links matched in the ownership regression, and complete stage attempts without saved task lists in the task-selection regression. Those counts are historical and must not be confused with the Nov 14 run, where two referenced dependency-stage records remain unknown.
- The Nov 14 saved-record audit and task-count reconciliation passed on archived Spark records after a real six-query execution. The integration archive remains 5 passed / 1 failed / 0 unattempted because two referenced dependency-stage records were missing. The audit did not issue SQL or fetch live Spark REST data; the earlier six-query run did execute SQL. No model fit, maintenance comparison or physical campaign was accepted.
- The earlier SF10 physical campaign remains **0 passed / 1 failed / 1 unattempted**; its maintenance arm was not attempted. Do not describe the campaign as successful.
- Historical SF1 service-time MAE: query/layout median 20.34 ms; shallow tree 20.93 ms; query median 21.23 ms; Log Ridge 21.54 ms. Lower is better for this prediction error, so the simple median was best in that limited evaluation. These older results do not show calibrated uncertainty or scheduling advantage.

## Slide-by-slide guide

### 1. Workload-Aware Scheduling for Data Processing Systems
Introduce the team, course and broad project title. Say that the project studies when shared data-system work should be scheduled under changing workload and queue conditions. The current case study focuses on Apache Iceberg compaction under Spark SQL queries. The title is intentionally broad enough to remain accurate if the implementation details evolve.

### 2. Abstract
Explain the tension: compaction can improve table layout, but it uses resources that concurrent queries also need. The project tests whether workload forecasts and queue state can improve the timing decision. Point out that the testbed, observation and audit pipeline exist. The latest milestone is six real SF10 queries with expected results, a passed raw-history audit and a separate count reconciliation for 168 tasks. The integration archive remains 5 passed / 1 failed / 0 unattempted because two referenced stage records are missing; a timing benefit is still unproven.

### 3. Review feedback
Summarize the feedback addressed in this review: make the data structures, model inputs, implementation status and evidence easier to understand. Mention that the evidence section now includes a recent validation screenshot with an explanation. Do not imply that this screenshot is a live experiment; it is a labelled historical capture.

### 4. Problem definition
Define the decision in everyday terms: given queries arriving for an Iceberg table, its current FIFO queue and available measurements, decide whether to compact now, wait, or take no action. A sound evaluation must count the entire workload and cannot hide queries left waiting or maintenance left unfinished.

### 5. Project scope
Clarify the system boundary: Spark SQL over Iceberg tables and Parquet data, with the timing of data-file compaction as the operation. The project is not changing Spark's query planner or proposing a new storage format. Findings from this setup will not automatically generalize to other engines or hardware.

### 6. Data sources
Explain the two roles. TPC-H supplies a standard relational schema and query templates; Snowset supplies observed table-layout metadata used to construct varied layouts. They are combined for this experimental setup, but this does not mean Snowset contains TPC-H queries or that the tests reproduce Snowflake's exact workload. Call out that benchmark-generated queries and layouts are inputs to our experiment, not an official TPC-H performance result.

### 7. TPC-H schema
Walk through the tables at a high level: orders connect customers to line items; line items reference parts and suppliers; partsupp describes supplier-part relationships; nation and region provide geography. These relationships let the benchmark queries join realistic multi-table data. The displayed counts are the recorded dataset state at the documented scale, not a claim about Snowset row counts.

### 8. System architecture
Trace the path: workload and layout inputs go to the replay driver; Spark executes queries and compaction over Iceberg; observers collect arrivals, queue state, query timing, plans and table state; an audit layer links evidence and preserves receipts. Explain that evidence must be linked to exact executions before it can support model training or a policy claim.

### 9. Three model roles
Explain each role and its target. **A** estimates service time when the client has a pending maintenance request. **B** estimates service time when no maintenance request is pending, using the actual observed table layout. A shared comparator uses maintenance state as an input to test whether separate A/B models add value. **C** predicts future offered arrival counts over a defined horizon. A distinct rewrite estimator covers maintenance duration and physical change. The model names describe prediction tasks; none is currently an accepted scheduling policy.

### 10. Model inputs and output
Inputs are pre-decision measurements, such as query identity or plan properties, table layout and file metadata, whether maintenance is pending, past arrival counts, and the observed queue state. A service-time estimator outputs milliseconds; C outputs an arrival count for a future horizon; rewrite estimation outputs a duration and physical-change measure. Training rows must come from real measured executions, with each feature available before the decision. Never include post-decision results as predictors or invent a counterfactual label.

### 11. Implementation progress
This slide summarizes the Nov 14 live evidence. Six real SF10 queries returned results matching pinned references, with service times from 0.66 to 6.15 seconds. A read-only audit passed for six mappings, 24 directly owned jobs, 71 job observations and 114 stage observations. A separate reconciliation accounted for 24 executed stages and 168 tasks; two referenced stages remain unknown. The integration archive remains 5/1/0 because of those missing records. Emphasize that query correctness and audit reconciliation are positive engineering results, not proof of improved scheduling.

### 12. Historical SF1 baseline
Read the bars as prediction error in milliseconds; lower is better. The query/layout median has the lowest MAE at 20.34 ms. The shallow tree is 20.93 ms, query median 21.23 ms, and Log Ridge 21.54 ms. The simple median therefore performed best among these candidates in this saved reserved-family evaluation. These are older SF1 service-time prediction results; they do not establish statistical superiority, calibration, or that machine learning helps scheduling.

### 13. Candidate model comparison
Explain why we compare simple baselines with learned estimators: a model should add value beyond a median. Highlight the evaluation split: related runs and overlapping source histories must stay together so near-duplicate observations do not leak across training and test. Results remain exploratory unless the registered family-level test and calibration gates pass.

### 14. Evidence chronology
Clarify the screenshot dates and their purpose. The result dashboard and raw-history audit are from Nov 14; the Spark UI capture is also from that query run, and selected runtime views are from Nov 11. All are historical now. They document query execution and evidence checks, not a passed compaction comparison. The capture manifests and result JSONs are included in this package.

### 15. Latest SF10 results and audit

This screenshot summarizes six real SF10 query results and the follow-up archive checks. All six outputs matched pinned references; sequential service times ranged from 0.66 to 6.15 seconds. The raw-record audit passed for six mappings, 24 owned jobs, 71 job observations and 114 stage observations. A separate count check reconciled 24 executed stages and 168 tasks. Two dependency-stage references are still missing, so the integration capture remains 5 passed / 1 failed / 0 unattempted. Checkpoint body time was 0.57–0.73 seconds each; this is not the full controller overhead. These are baseline and evidence-repair measurements, not a maintenance comparison or policy win.

### 16. Spark UI evidence
This Spark UI capture was taken on Nov 14 during the real query run. It shows Spark job and task counters, including a visible active job at that capture time. It is historical now. The screenshot helps explain what the engine exposes for audit; it does not establish that the full integration archive passed or that a maintenance policy improved performance.

### 17. Dashboard evidence
Describe the read-only dashboard as a way to inspect recorded state and captured evidence. A dashboard is a monitoring interface, not itself a result. Distinguish current service visibility from historical run outcomes and avoid treating an empty active-job list as a completed experiment.

### 18. Preserved failed campaign
State the status plainly: the earlier Archive03 physical campaign remains 0 passed, 1 failed and 1 unattempted. Its maintenance arm was not attempted. The useful lesson is that evidence gaps and failures are preserved instead of silently converted into success. The new six-query run is separate; it does not pass or repair the earlier physical campaign.

### 19. Compaction capability
This slide demonstrates that the system can perform the physical operation in a separate capability test, including a layout change from 64 files to 4. Explain that this shows the maintenance command can work in the testbed. It does not prove concurrent query benefit, a safe scheduler, or a successful paired timing result.

### 20. Evidence repair and open comparison
The positive result is that six actual queries returned correct outputs, saved job ownership was audited, and explicit Spark counters reconciled 168 executed tasks. We also measured the checkpoint capture cost at 0.57–0.73 seconds. The integration archive still failed its completeness gate because two referenced stage records were missing. The next scientific gate is complete capture followed by a fresh matched control and maintenance comparison, counting observation overhead.

### 21. Related work
Briefly say that prior work addresses compaction, latency-aware maintenance, query-cost prediction and metadata-based compaction utility. Our question is narrower: whether queue and workload forecasts can improve maintenance timing under concurrent analytical queries, measured with a complete response and maintenance accounting. Novelty remains a hypothesis to test against the literature and results.

### 22. Phase 1 conclusion
Separate what exists from what is not yet known. We have a testbed, workload replay, queue observation, candidate estimators and an audit trail. Six real SF10 queries returned expected outputs, and audit/reconciliation checks counted 168 tasks. The capture integration remains 5/1/0 due to two missing stage references. The older SF1 simple median beat candidate ML models; no compaction timing comparison or repeatable scheduling advantage has been shown.

### 23. Next work
Walk through the gates in order: account for the two missing dependency-stage references and capture all job/stage/task links during execution; measure the full observation overhead, not only checkpoint time; pass a completeness audit; then run a fresh matched timing comparison. Only if full response improves repeatedly should the team claim that a queue-aware learned policy helps.

### 24. References and evidence
Point reviewers to the primary documentation and saved experiment records. TPC-H is used as a schema/query reference and this is not a certified TPC-H result. The final line records the Nov 14 six-query run, the incomplete 5/1/0 integration archive, the unknown stage references and the unchanged earlier 0/1/1 campaign status.

### 25. Thank you
Close with the research question and invite questions. If asked whether the project has already proven machine learning helps, answer: “No. We have built the testbed and improved evidence validation. The current evidence says a simple median was strongest in an older prediction test; whether queue-aware timing improves full query response remains to be tested.”

## Likely reviewer questions

**What exactly passed recently?** Six SF10 query outputs matched pinned references; a saved-record ownership audit passed; and counter reconciliation accounted for 168 executed tasks. The integration archive remains 5/1/0 because two referenced stage records were missing. No compaction comparison or policy test passed.

**Why is the integration outcome 5 passed / 1 failed if six query results were correct?** Query correctness and archive acceptance are separate checks. All six returned expected outputs, but one integration checkpoint failed its evidence-completeness gate because two referenced dependency-stage records were missing.

**Why use three models?** They estimate distinct quantities needed by a timing decision: service-time behavior under two request conditions and future arrivals. A separate rewrite estimate addresses the maintenance operation. Separate estimators are candidates, not a requirement; the shared comparator checks whether separation helps.

**What is queue-aware about the approach?** It observes the current FIFO backlog and arriving queries, estimates upcoming query demand and service/maintenance duration, and would judge actions using the complete arrival-to-result response. The policy evaluation remains future work.

**What result supports a model advantage?** None yet. In the historical SF1 evaluation the query/layout median had lower MAE than the tree and Ridge candidates. A repeatable policy benefit has not been shown.

**What is the most important next gate?** Make task and dependency-stage capture complete during execution, account for the 0.57–0.73 second checkpoint cost in full controller overhead, then run a fresh matched control/maintenance comparison including queue wait and remaining work.
