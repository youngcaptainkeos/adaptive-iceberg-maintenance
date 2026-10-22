# Submission overhead recovery: 21 October 2026

Recovery completed successfully at19:08:17IST (13:38:17UTC). This is a real matched submission-path diagnostic, not a maintenance-policy comparison or cost-training experiment.

- 68 real queries:4warmup+64measured,8pertemplate/permode.
- Exact results, fixed table snapshot/logical equality and actual task ownership checked;32full-observation calls passed original strict60/300s telemetry/window/freshness gates.
- ABBA full/minimal/minimal/full phases; no rewrite, originalarrivalreplay or fitting.
- Failed20Octoberattempt remains preserved:1completedwarmup/0measured. Fresh recovery table queueaware_20261021_submission_probe_02 was used.

| Query template | Full median prep-to-result (ms) | Minimal median prep-to-result (ms) | Full minus minimal (ms) |
|---|---:|---:|---:|
| 0 | 436.07 | 402.04 | 34.03 |
| 1 | 2524.94 | 2523.64 | 1.31 |
| 2 | 518.86 | 470.77 | 48.09 |
| 3 | 354.02 | 311.06 | 42.96 |

These are descriptive differences between end-to-end medians, not a pure causal observer-overhead estimate. Both paths retain durable statement recording, exact correctness/snapshot/task evidence and the same background sampler. Minimal omits per-submission telemetry wait/window construction. Spark-call durations also varied between phases, especially template1, so a near-zero total difference does not prove preparation is free. ABBA and warmup mitigate but do not eliminate cache/time drift.

What this establishes: the corrected diagnostic can finish and strict preparation has measurable, template-dependent end-to-end consequences in this one run. What it does not establish: observer-free capacity, production throughput, uncertainty bounds, queue-aware policy benefit, calibrated interference costs or novelty. Do not train on minimal-mode probes, remove freshness/correctness gates, or extrapolate these differences into the old queueing experiment as measured counterfactual labels.

The earlier model-headroom gate still shows immediate best under actual future arrivals in both development windows. A large benefit campaign remains unjustified until a separately registered development action-time/observer-scope experiment demonstrates physical headroom or a supportable model correction. New independent source blocks must remain untouched by tuning.

Evidence: results/queue_aware_continuation_20261021/submission_probe_recovery_1329/{events.jsonl,queries.json,result.json,terminal_notification.json}.
Result SHA256 19de6bfb02e693fbffd8eacd85850efba51fb6e82087719db18f4a637038caee.
Raw events SHA256 1a543274f7db403ec774be6819fa7d2c00bd6a0cb77dccd5bbc50a6cb250a4b4.
Frozen revision3cfd42a8e19006923c5594d6cce523c376a9111d; probe sourceac8cba2b5e00bf2c2893694bb582811c703cad9c14d4fce75f5ce5e4f4922aca; protocol0bb1cc143c7af72304cca11add4aad9e9d6ea1a20a598c45f389e2709ccdc436.
Ntfy startmjhuEY1XyUPT and completionqKRo1t0Lci8H deliveredHTTP200. Processes finished naturally; no services stopped/data deleted.
Raw output mirror checksumverified; physicaltablecopy verification is recorded in the final methodology append.
