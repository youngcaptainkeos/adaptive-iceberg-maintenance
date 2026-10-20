# Preserved study audit and research-claim status — 20 October 2026

The human authorized a new read-only audit and backup after the overnight deadline. No new physical episode, SQL, model fitting, comparison of surviving policies or changes to frozen experimental code are authorized by this audit unit. The overnight automation is paused.

## Verified collection outcome

The terminal cohort result is `failed_preserved` because the registered launch cutoff was reached, rather than because an attempted episode failed: **7 passed / 0 failed / 1 unattempted**, with **21,940 completed queries**. The missing episode is the queue-aware policy on source window 1. All four policies ran on window 0; only immediate, forecast-quiet and no-maintenance ran on window 1. Do not convert this into a seven-arm comparison or treat seven runs as seven independent demand blocks.

The seventh episode finished at 2026-10-19 23:11:08 UTC (20 October 04:41:08 IST), after the 22:15 UTC launch cutoff. The coordinator preserved the eighth arm as unattempted. Its completion follower then refused comparison with `Incomplete/failed cohort preserved; no survivor analysis`. The fixed eight-arm acceptance gate remains intact. Earlier failed and intentionally aborted cohorts retain their separate inventories.

Authoritative cohort: `results/queue_aware_maintenance_20261019/cohort_snapshot_publication/result.json`, SHA256 `a1f6e5a8c7ff42fc32c7d109d3a2a1cafe6442cd87d92c37616c53ded19a7ed8`. Frozen runtime revision `d5e7c4002f49c409ae0b1e01863ceea40368d39a`; physical protocol SHA256 `ae7da3e0724b65462b7e48583e64dd2bcf7ad620c0ae794c7a81b251466fb7ce`.

## Audit and backup scope

The new `audit_preserved_cohort.py` independently reads every completed episode's raw events and reconstructs results using the preserved frozen auditor. It checks terminal and code hashes, original arrival identities, FIFO conservation, SQL/result/snapshot correctness, engine tasks, telemetry bindings, exact response/wait/service accounting and outstanding-queue area. It replays decisions against past-only queue transitions and frozen forecast/cost models, and checks matching source/layout/model within each window. This is independent reconstruction from raw inputs, not an independently implemented mathematical policy or a new physical result.

It explicitly permits an incomplete inventory to be audited for integrity while forbidding policy comparisons and acceptance claims. It preserves failures rather than relaxing individual raw gates. Actual worker3 detached execution: outer shell 511311, failure-alert wrapper 511312, auditor 511313; label `preserved_cohort_raw_audit_20261020_0822`. Log `results/preserved_cohort_audit_20261020_0822.log`; unique output `results/queue_aware_maintenance_20261019/preserved_audit_20261020_0822/`; failure receipt with the same prefix plus `_failure.json`. Actual script bytes are recorded by the result. The running audit is read-only with respect to original evidence.

Completed study evidence was copied to the local results directory. Itemized checksum verification (`rsync -rcni`) exited zero with zero differences, excluding only the active new audit output. Receipt `results/queue_aware_maintenance_20261019/backup_verification_20261020.json` records 741 files / 2,647,759,059 local bytes in scope. No deletion occurred. This is an evidence backup, **not a backup of Iceberg warehouse data files**. The audit output is mirrored and verified separately after termination.

## What the queue approach actually adds

The current contribution candidate is a decision controller, not a requirement to train three complicated models. Historical empirical conditional query-call estimates, rewrite-duration/layout estimates and a past-only arrival forecast feed a snapshot-aware FIFO simulation. At a decision opportunity it includes already waiting queries, predicts later arrivals, evaluates candidate rewrite starts plus no action, and chooses predicted total arrival-to-result response time through drain. A query keeps its dispatch-time snapshot/layout in the corrected simulator. This differs from merely choosing a low predicted arrival-rate window.

These are concrete implemented capabilities. They do not imply a novel algorithm, calibrated estimates, causal interference predictions or better performance. Current costs are conditional medians from real historical measurements; pending-maintenance observations are observational. The implementation has a measured client turn-around estimate, not a complete external CPU/I/O load forecaster, arbitrary concurrent-query scheduler, robust uncertainty bound or multi-table optimizer.

## Distance from the claims

| Claim | Current status | Evidence still needed |
|---|---|---|
| Controller is executable on real Iceberg and makes a recorded queue-aware start/wait decision | Supported by completed physical episode and preserved raw audit; new reconstruction pending terminal receipt | Finish this integrity reconstruction and preserve its outcome |
| Measurements account for every offered query and complete drain | All seven saved episode audits report this | New raw replay must agree exactly, including SQL/snapshots/tasks/telemetry and response-area identity |
| Queue-aware timing beats simpler policies in the registered study | **Not established** | Complete, honestly registered matched study; no survivor comparison or refit on observed results |
| Forecast/cost estimates are calibrated and identify interference effects | **Not established** | Independent source-family calibration; identifiable measurements for causal interference if that is claimed |
| Benefit generalizes beyond this setup | **Far from established** | Independent days, repeated order-balanced runs, varying real load/layout/scale and concurrency; meaningful block-level uncertainty |
| Queue mechanism is novel relative to prior maintenance planners | **Unproven** | Precise mechanism and broader prior-art comparison, faithful strong planning/current-queue baselines and mechanism ablations |
| Publication-ready evidence | **Not yet** | All above plus reproducibility, realistic instrumentation cost and a clearly bounded contribution |

## Main scientific limitations and next gates

1. **Incomplete prospective comparison.** The last missing arm cannot simply be appended later and called an unchanged contemporaneous matched study. Register a completion/recovery protocol before physical work; preserve the original 7/0/1 result. Evaluate time drift and ordering explicitly, and decide whether fresh matched blocks are required. Do not tune on these outcomes or retry until favorable.
2. **Heavy serial queue and instrumentation.** Saved outputs show mean response roughly 22–24 minutes while over 99.9% is waiting before the actual query call, including client/observer scheduling. This is a queue-stress feasibility setup, not proof that production Spark service is that slow or that compaction caused the waiting. Measure observer/client overhead and practical timing headroom before a larger campaign.
3. **Weak independence and scope.** Two adjacent windows share one demand day; four SQL templates are mapped onto real arrivals, not original production SQL. One static SF1 table, 16 initial files, one allowed rewrite, no ingestion and one serial query client limit claims. Thousands of queries do not supply thousands of independent experimental replications.
4. **Benefit must exceed error and drift.** The earlier corrected-model predicted margin over immediate was small. A successful simulator reconstruction checks its stated semantics, not the accuracy of counterfactual response estimates. Test whether meaningful timing headroom exists before increasing model complexity.
5. **Novelty must be more specific than adding backlog.** Prior reviewed work already overlaps workload-aware maintenance, lookahead, delayed compaction effects and interference reasoning. The existing novelty review is the source of that assessment; no new exhaustive literature review was performed in this audit. A defensible direction is a precisely evaluated snapshot/backlog timing mechanism, with queue-only, forecast-only and faithful horizon-planner baselines and ablations. No robust decision-margin guarantee has been implemented.

Recommended order: finish integrity audit and backups; review the narrow implementation evidence; preregister a practical overhead/headroom and matched-completion plan; collect untouched independent blocks only if an effect large enough to measure is plausible; then evaluate benefit and ablations. Keep novelty, calibration and generalization claims separate.
