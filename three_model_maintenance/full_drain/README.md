# SF10 full-drain fixed-rewrite adapter v1

**Local implementation only. No runtime validation, physical experiment, fit or benefit claim.** Existing runners and outcomes are unchanged. All execution/validation belongs on worker3 under the standing detached failure wrapper.

This version implements one foreground FIFO client and one actual bin-pack rewrite. The intervention is a registered start offset; no forecasts, models or simulator are called. Every arm must finish every offered query and the rewrite. The arrival horizon stops arrivals, not dispatch. A separate operational cutoff forbids new SQL; hitting it makes the cohort incomplete, never a successful completed-only average. Active calls finish naturally.

## Components

- `contract.py`: separate horizon/cutoff/action window, strict input/source pins, preserved 1s/2s/95% telemetry gates, fresh table and exact rewrite obligation.
- `registration.py`: binds actual existing mapping/configuration and explicit parameters. Draft is non-launchable. Worker-only `--remote-ready` requires real prerequisite receipts, including complete dependency inventory. It does not infer success from the earlier incomplete diagnostic.
- `study.py`: freezes all intended arm configurations and their order before execution; later protocol binding excludes only readiness and the study link to avoid circular hashes.
- `action_submission.py`: new action-specific durable intent and actual-start sample/metadata/cutoff checks. The legacy submission recorder admits a guarded cutoff only for queries and is left unchanged.
- `engine_scope.py`: rejects unexplained jobs in all recorded inventories after idle admission; it does not certify jobs never observed by REST.
- `ledger.py`: real offer/queue/dispatch/result transitions, with post-horizon dispatch admitted until the operational cutoff. It uses original publication-aware event names and never retimes arrivals.
- `runner.py`: actual SF10 SQL and rewrite, independent counter sampling, durable feature publication, periodic/terminal legacy and exact-SQL task archives, typed results, original/final full multiset validation, source copies and immutable collection/acceptance records.
- `accounting.py`: full offered-population FIFO response/wait/service, exact outstanding-area conservation, nearest-rank quantiles, action lag, query drain and work drain. CPU/I/O stay null without attributable accounting.
- `audit.py`: reconstructs original observation/publication/acquisition/task gates, actual SQL correctness, source multisets, explicit rewrite counters and the new exact-SQL raw executed-work audit. Missing dependencies fail.
- `compare.py`: requires every arm in a preregistered comparison, bound protocol/acceptance hashes, full raw replay and matched inputs/observer/layout/work. No comparison of surviving subsets, no significance or promotion claim.
- `job.py`: records the actual runner PID/exit after cleanup; a successful engineering sidecar alone cannot override a failed child.
- `scripts/launch_sf10_full_drain.py`: one-shot worker-only nohup/start_new_session launch with actual PID/log, unique paths, full HEAD/code/protocol agreement, competing-process check and failure notifications. Known persistent backend is preserved.

## Real inputs, not an example campaign

`registration.py` requires seven pinned input specifications (`path`, `sha256`): `source_config`, `source_preparation`, `source_capability`, `executed_work_gate`, `mapping`, `mapping_record`, `mapping_audit`. Source config must contain the six independently referenced SF10 queries and original telemetry/publication/acquisition settings. It is the source vocabulary, not a protocol to rerun.

The executed-work prerequisite must actually have status `passed_saved_raw_executed_work_only` and `dependency_inventory_complete:true`. The14November diagnostic and incomplete source cannot satisfy this gate. The21November new auditor is still unvalidated. This deliberate blocker is not relaxed by this adapter.

The explicit parameter JSON must contain exactly:

```
experiment_id, comparison_id, block_id, source_family,
output_directory, destination_table,
action_offset_ns, latest_action_offset_ns,
action_window_rationale, parameter_rationale,
no_new_episode_after_utc, no_new_operation_after_utc,
minimum_free_bytes, minimum_drain_admission_ns,
initial_file_count, archive_interval_seconds, idle_poll_seconds,
direct_archive, expected_spark_properties
```

`expected_spark_properties` binds observed Spark properties, including `spark.master` and `spark.driver.memory`; actual environment must match. Other held-fixed properties must be explicitly included after remote inspection.

`direct_archive` contains `page_length`, `max_pages`, `max_requests_per_checkpoint`, `timeout_seconds`. These are operational bounds requiring rationale; they cannot truncate SQL inventories. Caller-supplied dates must be fresh. No ready protocol or output table was invented while worker3 is offline. A fresh registration must document workload/capacity selection, expected run budget and arm order before execution.

Start offsets specify the earliest desired action opportunity; `latest_action_offset_ns` is a separately registered latest actual submission boundary, not an unreported tolerance. Exact actual RPC start and lag are reported. Late actions are allowed only under this new contract and explicit cutoff, including during drain when registered. A missed action window fails rather than converting to a no-maintenance arm.

## Future commands — do not run on the laptop

On worker3, after actual process/Git/source/capacity inspection and prerequisite acceptance, first prepare one draft per intended arm (without `--remote-ready` or `--study`). Freeze their real paths/SHA256s in an ordered JSON list. Then create the prospective study:

```bash
python3 -B -m three_model_maintenance.full_drain.study \
  --drafts ACTUAL_ORDERED_DRAFT_PINS.json --baseline ACTUAL_BASELINE_ID \
  --output NEW_PROSPECTIVE_STUDY.json
```

Bind each launch-ready protocol to that study using the same inputs/parameters:

```bash
python3 -B -m three_model_maintenance.full_drain.registration \
  --inputs ACTUAL_SHA_BOUND_INPUTS.json \
  --parameters ACTUAL_REGISTERED_PARAMETERS.json \
  --output NEW_PROTOCOL.json --study NEW_PROSPECTIVE_STUDY.json --remote-ready
```

Commit/push the concrete protocol, safely synchronize and verify full HEAD/source SHA. Then launch:

```bash
python3 -B scripts/launch_sf10_full_drain.py \
  --protocol NEW_PROTOCOL.json --expected-head FULL_VERIFIED_COMMIT_SHA
```

The launcher records `results/<experiment_id>_launch/{admission.json,launch.json,run.log,child_result.json}`. A failed real child gets `failure_notification.json`, and preserves its exit status. An allocated launch-admission failure also alerts. Wrong-checkout/malformed/draft invocation is rejected before creating a real attempt. No services, tables or original data are removed.

For independent post-block comparison, register all arm identities, directories, intended action offsets, protocol hashes and actual acceptance hashes after terminal completion; keep the arm list/order bound to a pre-execution study registration. Run `python3 -B -m three_model_maintenance.full_drain.compare --manifest ... --output ...` only on worker3 detached through `run_with_failure_alert.py` with its own label, receipt and log. The comparison manifest schema is `full_drain_fixed_timing_comparison_v1`, with `comparison_id`, `block_id`, `baseline_experiment_id`, `study_registration` (the same path/SHA256 used by the arms), and `arms`; each arm has `experiment_id`, `directory`, `action_offset_ns`, `protocol_sha256`, `acceptance_sha256`, `terminal_receipt_sha256`.

## Completion and claim boundaries

1. Source/table preparation and initial multiset checks happen before the arrival clock.
2. Real offered arrivals retain their original spacing. Queue waiting includes observation/publication/dispatch delays.
3. Query drain and required rewrite finish; periodic acquisition continues while either is active.
4. Work completion is recorded, archive worker joins, mandatory terminal task captures complete, then the private counter child finishes cooperatively.
5. Final metadata/full multiset SQL happens afterwards. This validation-only work is explicitly outside the workload/maintenance observation stream; its resource cost is unmeasured.
6. Immutable `result.json` records complete response accounting pending final independent gates. `engine_audit_inputs.json` freezes actual new output bytes; independent raw reconstruction must pass before separate `acceptance.json` exists. Any failure writes `failure.json`, exits nonzero and blocks comparison. An earlier collection result never silently becomes a pass.

Acceptance means the implemented engineering checks passed, not calibration, training permission, general policy superiority or global Gate A acceptance. Resource fields remain null. The comparison reports final measured layouts and equal successful rewrite obligations; it does not promise identical future performance after the measured cohort. Failed/censored/no-op arms cannot enter comparison.

## Known limits and next gates

- All code is unvalidated on worker3; syntax parsing is not runtime validation.
- The old terminal archive still contains its original conservative description-based ownership checks. They are retained, not bypassed; the additional exact-SQL audit cannot override their failure. Resolve that prerequisite through an independently reviewed capture repair before launching this study.
- Full drain can exceed engine UI retention. Register source/query counts and observed SQL/task retention/capacity before running; missing pages/tasks fail. This adapter does not alter or restart the existing Spark service.
- Exact initial layout signatures can differ between separately prepared tables. A comparison fails if they differ. Any alternative equivalence contract must be justified before outcomes, never patched in after a desired result.
- One foreground client, static logical data, one rewrite and the existing six SQL statements are a bounded mechanism study. There is no continuous ingestion, general query-complexity claim or production Snowflake workload reproduction.
- No automatic arm/campaign chaining is implemented. Review a terminal arm, append both methodologies, mirror/checksum evidence and synchronize before the next unit. This prevents an unvalidated adapter from launching a long campaign offline.

## How this changes the fairness of the experiment

The primary response measure is the sum of every query's actual fetch-end minus its scheduled arrival, divided by the full original offered count. Response = waiting + service = exact outstanding-request area. It is never divided by only the queries that finished before the horizon. Separately report rewrite duration, desired versus actual action start, query drain, required-work drain, and the recorded post-metadata completion boundary. Terminal archival and final validation are outside that response formula; their timing/coverage limits remain explicit.

Two timing arms carry the same full query cohort, fresh initial layout contract, one useful rewrite, observer code/settings and engine configuration. Only the preregistered action opportunity changes. No-compaction remains a useful diagnostic, but is outside this equal-obligation primary comparison. No forecast is introduced to compensate for an overloaded replay.

The executed-work auditor gains one explicitly named mixed-ledger trace schema. Its original standalone whole-ledger schema remains unchanged and is now explicitly required by its CLI. Job/stage/task reconciliation rules are shared and unchanged. This source change invalidates old code pins for a *new* audit; generate a fresh registration, retain the old one, and never rerun in the old output directory.

## Next-agent remote validation and failure decisions

1. Recover the actual worker processes, Git tree, source snapshots and saved results. Do not infer their state from laptop transport. Safely fast-forward this unit and verify intended source SHA256s. Preserve services and unrelated files.
2. Run the already planned saved-raw executed-work audit on genuine evidence, detached under the failure wrapper with a fresh protocol/receipt/log. A diagnostic pass with missing dependencies does not satisfy this adapter's admission gate. If missing, preserve failure and repair prospective capture; do not reconstruct absent stages from aggregate skipped counts.
3. Review/repair the known conservative legacy terminal ownership gate through a separately versioned, preregistered change and genuine retained-history/fresh six-query capability validation. Do not bypass it here. Check the new action recorder and mixed-ledger schema on actual remote evidence before admitting a timing study. No local fixtures or dummy SQL.
4. Measure development capacity on the intended fresh 64-file layout and the six-query mix. Keep real arrival windows intact. Predeclare window-selection rules using only development information, query mix, hardware, retention capacity and a realistic full-drain budget. A different four-file six-query capability is not a load estimate.
5. Freeze a small prospective study of fixed timing arms; inspect the dry registration/code paths without physical SQL first, then launch one genuinely useful engineering arm. Check the first actual publication/checkpoint and estimated drain. Missed gates fail; do not relax bounds.
6. If a complete arm passes all raw checks, append methodologies, mirror/checksum its complete evidence and synchronize before the next arm. If any arm fails or remains unattempted, the registered comparison is incomplete. Repair the mechanism and register a new version/identity rather than comparing surviving arms.
7. Only after repeated matched independent development blocks show a reproducible useful timing effect, test simple fixed/threshold policies and the forecast's incremental value with whole-source-family splits. Then consider additional learned cost models. A null or unstable result is a stop/pivot signal, not permission to search arbitrary metrics until one looks good.

No fresh launch-ready protocol, server PID, remote result or new performance number exists for this local build. The next useful inspection time is after SSH access and the actual prerequisite audit launch; no duration for a full physical drain is assumed.
