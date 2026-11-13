# Implementation and next-agent handover

## 1. Read this before touching the worker

Current user instruction: **skip SSH and work locally**. This unit implements planning and saved-evidence analysis. No new SQL, physical collection or model fitting is authorized by the generated plans. The worker's present process, Git and experiment state is unknown after transport failure. Do not infer it from historical receipts or restart anything.

All earlier November 1–2 experiment cutoffs have expired. Their protocols cannot authorize a new episode. After the user restores access and resumes remote work, inspect actual active jobs, services, campaign results and Git state before any mutation; then write a fresh registration with new identities and cutoffs. Preserve historical failures, occupied tables and all services.

The human goal is improved metrics, not more infrastructure. Read [the strategy](01_research_strategy.md), [experiment cards](02_experiment_catalogue.md) and [current status](STATUS.md) before expanding scope. Every implementation ticket must name its target mechanism, outcome and stop rule.

## 2. Code delivered in this unit

All new modules are under `three_model_maintenance/research/`. They use the Python standard library and do not import a Spark client or invoke a physical launcher.

| File | What it actually does | What it does not do |
|---|---|---|
| `common.py` | Strict JSON input, explicit numeric checks, SHA256 binding, exclusive output creation | Invent missing fields or overwrite old evidence |
| `design.py` | Validate a 34-card dependency graph; enumerate a bounded selected-stage design; counterbalance order; estimate serial effort from supplied durations; conservatively group overlapping actual source ranges | Select real windows, allocate tables, establish independence or authorize a run |
| `accounting.py` | Stream a genuine completed serial FIFO ledger; bind requests/calls/source rows; reconstruct complete response/wait/service, area, quantiles and drain | Certify engine/task/correctness gates or measure CPU/I/O |
| `comparison.py` | Require all registered paired episodes and matched population/layout; enforce declared maintenance scope; report descriptive family-level differences | Produce significance, fill failed arms, claim a policy is accepted |
| `ownership.py` | Reference implementation of unique exact marked-SQL-to-execution-to-job binding with explicit terminal job lists | Integrate into the frozen collector, infer missing jobs, certify tasks or retroactively pass a failure |
| `validate_saved.py` | Register code/input hashes and replay supplementary checks on four real completed historical episodes plus a preserved failed campaign | Generate fake fixtures, new physical observations or a trained model |
| `__main__.py` | CLI for the above design/accounting operations | Start SQL, create a table or launch a controller |

The programme JSON lives at `three_model_maintenance/protocols/research_program_20261113.json`. Its states are all `planned`. Generated `block_slot` values are planning slots; `source_family` and `table_identity` remain null until bound to genuine evidence in a new physical protocol. The generator rejects more than 10,000 units **before constructing the product**; the broad 29,160-cell illustration cannot accidentally become an enumerated campaign.

The matched comparator has a conservative exact terminal-file-state equality rule. If equivalent rewrites naturally produce different byte totals, design and independently audit a prospective logical/layout-equivalence contract. Do not add a post-hoc tolerance to get a desired comparison accepted. It also cannot by itself verify the broader feature-history overlap; use the overlap-family assignment before constructing comparison manifests.

## 3. Existing code to reuse, not rewrite blindly

| Concern | Existing path | Next concrete work |
|---|---|---|
| SF10 physical execution/audit | `three_model_maintenance/runtime/sf10_collect.py` | Review `audit` and `run`; introduce a new versioned ownership contract only after exact raw replay |
| Periodic/terminal engine archive | `three_model_maintenance/runtime/terminal_archive.py` | Capture direct SQL execution/job links along with existing complete job/stage/task evidence |
| Host telemetry isolation | `three_model_maintenance/runtime/process_sampler.py`, `counter_process.py` | Preserve explicit lifecycle, actual acquisition and no-gap checks; do not redo working machinery without a measured reason |
| Prior exact attribution diagnosis | `three_model_maintenance/audits/sql_ownership_diagnostic.py` | Recover its original raw SQL inventory and replay the new binding implementation against it |
| Existing candidate A/B model logic | `three_model_maintenance/models/latency.py` | Retain strict row admission and whole-family model provenance; add candidates only after data readiness |
| Training orchestration | `three_model_maintenance/training/pipeline.py` | New immutable registration/output for future training; never overwrite frozen fits |
| SF10 candidate comparison | `three_model_maintenance/training/sf10_comparison.py` | Review feature support, family split and selection budget before activation |
| Full-cohort queue work | `queue_aware_maintenance/` | Reuse verified full-drain accounting and registered FIFO semantics; new action horizon needs a new version |
| Failure alerts | `scripts/phase6-live-evaluation/run_with_failure_alert.py` | Wrap every standalone real check/run; preserve its actual exit and alert receipt |
| Display/screenshot evidence | `three_model_maintenance/observability/review_server.py` | Read-only presentation; not a reason to run purposeless experiments |

The historical model milestone is in `docs/learned_cost_model_implementation_plan.md`; earlier evidence is in `docs/daytime_review_2026-10-14.md`. This programme narrows future priorities without rewriting those records.

## 4. Local validation evidence and scope

The first regression completed at 17:37:48 UTC on 13 November 2026 under label `research_saved_regression_20261113_01`, wrapper PID 40215. It reconstructed 12,376 actual query rows across four completed historical episodes, exactly matched response sums and independent outstanding-area integration, reproduced two saved descriptive storage-placement contrasts and preserved the SF10 0/1/1 failure count. Source families collapsed to one overlap component. No physical acceptance changed.

A later code review added a pre-allocation design cap and explicit no-empty/unique SQL-binding checks. A separately labelled second regression checks the final source and the real programme's excessive design bound. Refer to `STATUS.md` and its receipts for its actual outcome; never carry the first pass forward as validation of later edits.

The original SQL REST inventory is **not mirrored locally**. `ownership.py` therefore remains syntax-reviewed and unexercised against that input in this unit. The saved diagnostic summary is not a replacement for the raw payload. Prospective ownership repair remains the first dependency.

The four historical episodes are under `results/queue_storage_sql_20261024/episodes/queueaware_storage_20261024_01` through `_04`; each has pinned `events.jsonl`, `mapped_arrivals.csv`, `config.json` and `result.json`. The regression registration lists their exact hashes. The result is supplementary accounting, not a rerun of all original publication/correctness audits.

## 5. Useful commands

Run from the repository root. Outputs must be new paths. The following commands describe actual implemented interfaces; they are not instructions to rerun completed checks or bypass the standing failure wrapper.

```bash
python3 -B -m three_model_maintenance.research validate-program \
  --program three_model_maintenance/protocols/research_program_20261113.json \
  --output /absolute/new/path/program_structure.json

python3 -B -m three_model_maintenance.research plan \
  --program three_model_maintenance/protocols/research_program_20261113.json \
  --design timing --blocks 3 \
  --output /absolute/new/path/timing_PLAN_NOT_RUN.json

python3 -B -m three_model_maintenance.research overlap-families \
  --windows /absolute/path/actual_source_windows.json \
  --output /absolute/new/path/overlap_components.json

python3 -B -m three_model_maintenance.research account \
  --episode /absolute/path/genuine_completed_episode \
  --pins /absolute/path/predeclared_four_file_sha256.json \
  --output /absolute/new/path/supplementary_accounting.json

python3 -B -m three_model_maintenance.research compare \
  --manifest /absolute/path/preregistered_comparison.json \
  --reports /absolute/path/episode_id_to_accounting_report.json \
  --output /absolute/new/path/descriptive_comparison.json
```

Three planning slots balance three timing-arm positions; they do **not** assert that three real families exist or that three blocks suffice statistically. `--pins` is a JSON object mapping the four exact filenames to SHA256 values. `--windows` is a JSON list with `id`, `dataset_id`, `warehouse_id`, `history_start_utc`, `start_utc`, `end_utc`. See the actual regression registration for a genuine matched-comparison manifest shape.

For any future validation, use the failure wrapper under a detached process and record actual PID, command, UTC launch time, log and expected check time. User-authorized local saved-evidence work was the explicit exception this turn. Normal physical/fit/scientific execution resumes on worker3 after access and gates are verified. Do not start an old receipt/output path again.

## 6. Exact next implementation queue

### I01 — Recover and validate direct ownership (E00–E01)

**Mechanism/outcome:** trustworthy attribution permits valid response measurements during concurrent maintenance. This is an enabling repair, not a performance claim.

Recover `results/sf10_sql_job_inventory_paged_20261111_01/raw_sql_inventory.json` from worker3 only after access resumes. Expected saved SHA256 is `bab3f029266f27b72dd3e809a3ab1cb8de3533dfe94916783aeddb54fd49b0af`; verify actual bytes rather than trusting this text. Bind it to the recovered failed episode raw SHA `1243ef1b1810b995280725b555c41b478cdb3b5efa7d9e550d3a09949ef365a8`. Run a new detached read-only audit comparing exact SQL bindings and all original rejected-job links. Preserve the original 0 passed / 1 failed / 1 unattempted outcome.

Then version the live capture: archive SQL inventories with page/URL/time/hash and explicit complete coverage boundaries; match each completed marked call exactly once; archive linked job, stage, task index and attempt evidence; require actual explicit counters. Missing/ambiguous fields fail. No “broadcast jobs are always ours” shortcut and no completion inference from empty active lists. Capture periodic and mandatory terminal evidence before expensive final validation SQL.

**Done when:** raw reconstruction passes on genuine retained payloads, independent review finds no default-zero or ownership shortcut, new live contract is registered with fresh identities, and one fresh verification block passes all existing physical gates. Do not change frozen/running source. Bound effort to the stated repair budget.

### I02 — A complete timing/action study adapter (E02–E06)

**Mechanism/outcome:** establish whether start-time choice can improve full-cohort response at all.

Connect the verified ownership collector to the full-drain queue ledger. Bind one exact offered population, initial layout and rewrite obligation across all arms. Add a versioned start-window/drain contract that permits the registered late action without stopping admitted queries. Snapshot-pinned mechanism reads need actual supported syntax and evidence, not an assumed implementation. Register the timing arms and complete observation boundary before collecting them.

**Done when:** matched null replicas and complete timing arms have correct raw accounting, terminal layout/maintenance evidence, preserved failures, and enough pilot block information to assess noise and plan precision. No model search is needed for this step.

### I03 — Resource and overhead accounting (E08–E09)

**Mechanism/outcome:** determine whether observation/planning consumes any expected gain and whether CPU/I/O is a viable separate target.

Implement a versioned raw-counter reader with identity/unit/reset/coverage validation. Distinguish worker totals, engine task totals and controller totals. Join only valid actual intervals and include all attempted work. Extend the comparison report with independently supported resource fields; unavailable data stay null. Keep a separate whole-controller measurement including collection, features, prediction, planning and persistence.

**Done when:** the complete boundary is reconstructible from genuine counters and results remain correctly labelled where only host-level attribution is possible. No CPU or energy benefit claim from inference microbenchmarks.

### I04 — Cheap policies and actual action value (E10)

**Mechanism/outcome:** improve measured response with minimal additional work.

Implement frozen fixed/reactive/simple predictive policies over the same admissible action set. Make every unsupported state, deferral and unmet obligation explicit. Require current availability timestamps and full decision receipts. Do not choose thresholds from final-test results. Test whole episodes and report full response, tails, resource work, completed obligation and final state.

**Done when:** a strong inexpensive reference exists and the remaining useful gap is measured. If it closes the gap, stop adding model complexity.

### I05 — Minimal model additions and honest ablations (E11–E17)

Only after I04 and coverage readiness: train the bounded candidates on fresh registered development families, compare shared/separate A/B and forecast/no-forecast in the same planner, measure full overhead and retain the simplest effective method. Preserve every preregistered comparator. Calibration requires independent evidence; otherwise omit that branch.

### I06 — Freeze, independent test and paper artifact (E18/E31)

Freeze selected code, model bundle, feature contract, thresholds, outcome metric, statistical plan and source assignments. Evaluate once on untouched families. Record all errors and results. A failed/null primary outcome remains the primary outcome. Produce raw-to-figure scripts, complete manifests, environment description and limitations. Transfer or new storage-engine experiments are separate later branches, not substitutes for failed confirmation.

## 7. Handoff checklist

- Read current user overrides; do not revive old SSH/cutoff instructions.
- Inspect actual processes and active experiment handles before launching anything.
- Check local/remote/GitHub ancestry and preserve unrelated dirty files and the local-only archive.
- Use the experiment card and [record template](EXPERIMENT_RECORD_TEMPLATE.md); register actual parameters and their rationale.
- Bind code, protocol, datasets, source windows and model artifacts by hashes before execution.
- Launch one scientific executor at a time, detached with ntfy failure handling and unique receipts.
- Capture complete raw evidence; never manufacture a missing state or counter.
- After each major unit append both methodology documents, preserve original outcomes and write the next gate.
- Commit only intended files, push, and verify worker/client HEAD plus intended SHA agreement when SSH is authorized and available. Until then, explicitly report remote sync as deferred.
- Update `STATUS.md` with actual evidence; do not mark catalogue entries completed from a code-only check.
- Tie the next chosen task back to improved response/resource metrics. No active task without an impact path.
