# Queue complexity / maintenance unit: actual preflight and launch

## Implemented and actually checked

Source revision26aa674a0183cef991972b1c63e4bd99b6703a93 was pushed and frozen at `/tmp/capstone_queue_complexity_20261025`. The original physical runtime790f4f89d1d8cbe821903af79392134bfb1c6bbb remains byte unchanged. Source/protocol SHA agreement was verified on worker3 before execution. The new adapter is separately registered/copied/audited; old raw validity alone cannot accept the new features.

Detached real-plan preflight wrapper2192722 ran25October01:39:37.374209–01:39:42.300788UTC (07:09IST), status `passed_actual_four_query_plan_and_source_preflight_only`. It acquired shared and physical locks, made8 actual EXPLAIN calls against a verified immutable terminal snapshot, independently reconstructed all4raw plans/publications and created no query-cost labels. Parser has now passed these actual four SF1 plans; no SF10/join validation is implied.

| Query ID | Operators | Scans | Joins | Aggregates | Exchanges | Sorts | Filters | Windows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|0|7|1|0|2|1|0|1|0|
|1|5|1|0|2|1|0|0|0|
|2|7|1|0|2|1|0|1|0|
|3|7|1|0|2|1|0|1|0|

Only two operator-count patterns occur. Structure counts alone do not distinguish three of these four different SQL templates or represent selectivity/runtime complexity fully. Query identity is retained; there is no fabricated complexity score or claim of unseen-template prediction. More diverse genuine queries/plans are a later evidence gate. Raw COST outputs remain diagnostic and unknown/unvalidated estimated rows/bytes remainNone.

Preflight receipt SHA256 `ac7226ea03803822fbda8b68889e902f509e09358c261107084b8d320cd6a7a3`; actual raw events SHA256 `855087a4184a80d5dc81c1fc163c8a721aeb86a9f80a3e93b85e9ba5d69f1f70`. Preflight and corresponding launch directories were copied locally and itemized checksum dry runs returned0 with no differences.

## Actual detached physical launch

Parent wrapper2193434/coordinator2193437 started25October01:40:53.026506UTC (07:10:53IST). First null-control arm wrapper2193543/client2193544 started01:40:55UTC. Actual source/table/setup progressed to durable one-second warmup telemetry; at01:42UTC no failure artifact or child log error. Status0passed/0failed/1running/1unattempted; no completed physical feature audit or performance conclusion at this initial observation.

Estimated terminal04:37:32UTC (10:07IST), based on actually observed whole-arm runtime plus305seconds perarm/900seconds final audit reserve, not a guarantee. Registered no-new-episode10UTC15:30IST/no-new-SQL13UTC18:30IST unchanged. Existing operations finish naturally. Start ntfy deliveredHTTP200, id `5vRQvDgrSii8`; each child/parent failure and meaningful completion reports through the existing authorized topic. No retry/competing physical fit or collection.

- Live coordinator: `results/queue_complexity_maintenance_20261025/progress.json`.
- Launch/log: `results/queue_complexity_maintenance_20261025_launch/{pid,launch.json,run.log}`.
- First episode protocol SHA256 `1bac0b699b3898541b2d1e594199a0ca6575c287a584e94960efbe44a8ff6b91`.
- Registration `protocols/complexity_maintenance_unit_20261025.json`, SHA256 `ade885ec56edb671466828cbc36e648272b550efdd17d7f8e7b473dbfc1ae3a2`.
- Adapter SHA256 `8310090afcac8ddbc8d0dc7a0ff5c5f8b7947529ef2d4bbe75d874d4ee1e9cfc`; new feature auditor `21593697fa47bddaa9c5f4edd4ae17588844d684cf8f48fcce5274781e5c12aa`; coordinator `23876c3e44ee324297065fcddd8ad8c952808aaf6e3bbd068a4bae3918b1bc09`.
- Actual working evidence is `/home/ccbd/capstone_evidence/queue_complexity_maintenance_20261025/`; terminal publication under canonical `results/.../episodes/` requires both original raw and new feature gates. No full client mirror of active raw evidence is claimed.

## Documentation, coordination and limits

Both methodology documents contain the registration, code/data rationale and remote start. Concurrent Main scratch-recovery documentation and the queue parent's launch commitac32c59 diverged normally; merge462997c preserved both original append blocks byte-for-byte after their common ancestor, without rewriting history or changing frozen running code. Main was notified of actual queue locks/PIDs/estimated release and must remain metadata-waiting until actual resource admission. Its failed SF10 generation/reference/prepare record remains preserved, not converted to success by this SF1 plan preflight.

The previous four-arm canonical storage raw backup is fully copied and verified with zero itemized checksum differences, excluding only duplicate original working copies retained remotely. See `results/queue_storage_sql_20261024_backup_status/completed_20261025.json`. This supersedes prior pending status for that transfer; it says nothing about the separate older eight-arm mirror.

The next completed-unit report must show actual maintenance, query-plan bindings, fragmented-layout client-pending/nonpending counts per query and complete actual-offered histories. Missing support remains missing, no outcome-selected extra episode. Both episodes use one consumed source family; client pending is not causal engine-active exposure. Existing empirical weights/runtime decisions remain frozen. Plan-aware model fitting, predictive benefit, calibration, independent source splits, broader quiet-period/SQL-mix/scale coverage and scheduler superiority remain future gates.

For the requested plain-language implementation explanation, see `docs/plans/COMPLEXITY_MAINTENANCE_UNIT_2026-10-25.md`: the recorder obtains real plans, the auditor proves their identities/timing and exports candidate data, and the coordinator runs/waits/documents both full episodes. Neither operator counts nor a random plan UUID is silently used as a new maintenance policy.

## Actual query execution after warmup

Warmup started01:41:36UTC; cohortclock recorded01:46:41.822815UTC. Live raw inspection through01:47:16.366839UTC observed37 completed actual queries and38 plan-query binding records (one request in flight), with no failure artifact. This verifies that the new adapter path is being exercised with real queries after preflight; the full original/plan/candidate/independent terminal audits are still pending. No complete episode, candidate corpus, new trained predictor or policy advantage is claimed by this startup check.
