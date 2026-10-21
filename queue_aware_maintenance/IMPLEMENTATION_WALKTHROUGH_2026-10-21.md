# What we coded, in plain language

This guide explains the implementation as of21October. It does not claim the new timing experiment has completed. Its final results will be in the study's `analysis/report.md`; both methodology documents receive actual progress/results automatically.

## What this particular experiment asks

Imagine a queue at a shop while someone reorganizes the shelves. Reorganizing now might slow the people already waiting, but could make later service faster. Before building a smarter adviser, we need to find out whether doing it later actually helps in our setup.

We replay the same real20-minute arrival sequence eight times on fresh copies of the same table. Each run uses one of four interventions: start maintenance at the first opportunity after0,60or600seconds, or do no maintenance. The second round reverses the first round's order. Every original request stays in the queue until its result arrives; we do not stop measuring when the20-minute arrival period ends.

This is a controlled experiment on a known development workload. Fixed times are experimental settings, not fabricated model predictions. We have not trained a new model for it, and repeating one workload does not create independent workloads.

## New files for this timing experiment

| File | What it does |
|---|---|
| `fixed_start_policy.py` | A small timer-based intervention. Its `decide()` function checks the real elapsed time and says start/wait. It never predicts future query costs. |
| `preflight_timing_study.py` | Checks the new timing rules against real decision times and queue identities recorded in an earlier run. It checks source hashes, balanced orders, imports and whether worker3 can push the methodology updates. No SQL is submitted here. |
| `run_timing_study.py` | The coordinator: registers all eight runs, checks available resources/time, starts one run at a time, records progress, stops dependent work on failure, updates both methodology documents and sends ntfy messages. |
| `compare_timing_study.py` | After all eight runs finish, rebuilds their results from raw evidence and produces the complete comparison. It refuses to compare only successful survivors from an incomplete study. |
| `protocols/timing_headroom_development_20261021.json` | The experiment's settings and evidence references: exact arrivals, intervention order, new table names, source hashes, time cutoffs and reasons for the choices. |
| `TIMING_STUDY_PLAN_2026-10-21.md` | Human-readable study design, limits and execution/recovery instructions. |
| This guide | A map from your research question to the actual code. |

## Existing files edited

- `controller_factory.py`: `build_policy()` selects the correct decision rule. Added an explicitly registered fixed-start option, with a source-hash check. Existing queue-aware and forecast policies keep their original behavior.
- `audit_episode.py`: added fixed-time checks. A completed fixed-start run must actually perform one rewrite, must not submit it early, and its recorded decisions must match the registered time rule. The existing SQL, snapshot, task, telemetry, queue and timing checks remain.
- `docs/methodology_working_doc.md`: append-only detailed evidence history. The coordinator records what actually happened after each completed run and after final analysis.
- `docs/updated_methodology_working_doc.md`: the copied master document you asked to keep updated. The coordinator appends the same durable unit record and pointers here too. It does not replace old text.
- `OVERNIGHT_HANDOVER.md`: records frozen revisions, paths, current state and what the next person/assistant must check. Historical failed attempts stay visible.

## How a real run happens

1. The coordinator selects the next preregistered intervention and writes its exact configuration. No outcomes determine which run happens next.
2. `run_episode.py::run()` creates a fresh isolated Iceberg table from the verified source snapshot. It checks row/layout counts and full logical equality before replaying anything.
3. The arrival thread (`offer()`) releases each real request at its original recorded offset. `CohortLedger.transition()` records whether each request is offered, queued, dispatched or completed. The queue is real; its future arrivals are not given to the decision rule.
4. At decision opportunities, `build_policy()` supplies `FixedStartPolicy.decide()` or the null control. A60-second intervention means the first observed opportunity after60seconds, not a claim that its SQL started at exactly60.000seconds. Actual submission time is reported separately.
5. If the rule says start, the `action()` function submits Iceberg's real rewrite operation. Query calls continue through the existing serial client and keep their selected snapshot. Existing model code is not used to manufacture the action's physical consequences.
6. `StatementRecorder.execute()` records actual SQL submission, execution-return and fetch-completion clocks. It also stores real returned rows. `PublicationTelemetrySampler` makes actual durable host observations available; it does not invent missing samples.
7. `EngineArchive.checkpoint()` preserves real Spark jobs/stages/tasks. This helps us check that our requests ran and that unrelated Spark work did not contaminate an exclusive experiment.
8. `audit_episode.audit()` reconstructs the complete request population, correctness, snapshot binding and timing. Response time means original arrival→actual result. It must equal waiting+call time and independently calculated area under outstanding-request count.
9. Only after a run passes does the coordinator advance. A crash, wrong result, missing telemetry or unmet cutoff preserves the attempt and stops dependent work. It never retries until a favorable result appears.
10. After all eight pass, `compare_timing_study.run()` repeats raw reconstruction and decision replay, then reports each intervention against immediate maintenance for both rounds. Negative/inconsistent results remain in the report.

## What the main coordinator functions mean

- `run()`: the overall checklist and sequence controller.
- `save()`: writes durable progress so disconnecting the laptop does not lose the last known state.
- `timing_details()`: reads actual recorded maintenance submission/completion clocks; it does not substitute the requested start time for what really happened.
- `append_docs()`: appends actual evidence to both methodology files, commits only those files and pushes them. If they already contain unrelated concurrent edits, it preserves them and reports a documentation blocker rather than staging someone else's work.
- `announce()`: sends ntfy start/progress/completion messages and keeps delivery receipts.

## How this differs from the three-model idea

Predictive models estimate what might happen. The broader queue-aware controller uses current backlog, predicted future demand and estimated rewrite/layout effects to choose a start time. This experiment temporarily removes that decision complexity and directly tests a few timing interventions. If timing cannot reliably help, more complicated predictors are not automatically useful.

The new fixed-time controls are not a new intelligent controller and do not establish novelty. Their purpose is to determine whether there is a physical effect worth learning to choose. The queue-only and forecast-only ablations implemented earlier are later comparison candidates; they are not part of this four-intervention timing study.

## Earlier recent files, for context

- `continue_research.py`: finished the read-only overhead/accounting/headroom diagnostic. Its zero perfect-arrival **model** gain was a warning, not proof that physical timing cannot help.
- `ablation_policy.py`: contains queue-only and forecast-only information-removal baselines. They were exercised on real recorded states; not yet a physical benefit study.
- `probe_submission_overhead.py`: ran the successful68-query full/minimal preparation diagnostic. The timing-interface error was fixed using real recorded clocks. Minimal preparation is not observer-free, and these probes are ineligible for cost training/policy comparison.
- `audit_failed_submission_probe.py`: verified that timing repair against the actual failed warmup record without new SQL.
- `SUBMISSION_PROBE_RESULTS_2026-10-21.md`: preserves the successful diagnostic's measured numbers and limits.

## What will still be missing even if all eight runs pass

A repeated physical result here is development evidence from one source window, one static SF1 table, four SQL templates and a serial client. It does not establish independent-day performance, calibrated causal interference estimates, production scalability or novelty. If delayed maintenance consistently helps, the next evaluation needs untouched workloads and strong queue/forecast/planning baselines. If it does not, the report must say so.

The remote process does not depend on your laptop. Worker3 saves raw evidence and pushes methodology updates after completed units. A laptop that is offline cannot have its local files updated immediately; the next check must pull the committed documents and mirror/checksum completed raw artifacts. No local synchronization is claimed while it is disconnected.
