# Prepared executed-work audit: worker3 validation pending

21 November 2026. **Implemented locally, not executed or accepted.** The server was unreachable in the preceding connectivity check. The user authorized local construction and later remote testing. No audit, SQL, fit or physical experiment was run for this unit. A power interruption pause was respected; work resumed only after the user said continue.

## Purpose and its connection to performance

The next timing experiment must compare user response for the same offered work and completed compaction. The current evidence blocker is distinguishing work that actually executed from references to dependencies that did not execute within that job. Without that distinction, CPU/task accounting during maintenance can be wrong. This unit builds a bounded independent audit for that measurement prerequisite. It does not optimize an unrelated subsystem or demonstrate a scheduling gain.

The earlier history audit reconstructed exact ownership, but relied on a separate count reconciliation for its task evidence. The new implementation combines independent raw SQL ownership, every observed owned job/stage history, executed-stage reconciliation and raw task receipts. It does not consume the prior auditor's job proofs or collector `selection.json` as truth.

Existing physical acceptance remains unchanged. Historical integration remains **5 passed / 1 failed / 0 unattempted**. The older archive03 campaign remains **0 passed / 1 failed / 1 unattempted**. Missing stages6094/6095 remain unknown. This unit cannot promote either result, create labels, fit a model or enable a new live collector.

## New implementation

- `three_model_maintenance/research/executed_work_audit.py`: frozen-registration preparation plus worker-only saved-raw audit.
- `scripts/launch_executed_work_audit.py`: worker-only, unique-output, detached launcher using the standing failure wrapper and ntfy configuration. Intended commit/code/config hashes, original reference pins, a fresh admission cutoff and absence of a known competing Python project executor are checked. A nonblocking file lock also prevents two instances of this auditor from running together. That lock is not a universal lock for other project executors; the operator still inspects actual server processes and handles before launch.

No frozen collector, model, existing protocol or raw result is edited.

## Evidence contract

The sole initial reference is the committed `three_model_maintenance/protocols/live_history_audit02_20261114.json`. Its original `inputs` hashes, episode identity and application URL are copied unchanged. The old start deadline is not reused: a fresh saved-file audit window must be supplied when worker3 returns. No protocol is launch-ready today.

The original capability called each of six registered SF10 templates once. That is the rationale for the expected call count; counts of jobs, stages, tasks and missing references are reconstructed, not set as desired outcomes. Existing source snapshots are engineering inputs, not independent new performance data.

The audit requires:

1. Exact request/completion population equality and one exact marked SQL record per call, with explicit successful/running/failed job lists. Shared job ownership is rejected.
2. SHA-pinned archive file inventory, no symlink paths, paired response/receipt identities, matching application URLs and HTTP200 status, ordered request clocks, complete final SQL pagination and a saved terminal checkpoint flag.
3. All observed owned job and referenced stage attempts, with explicit integer adverse counters. Failure, killing, retry, terminal regression, missing owned jobs and final nonterminal stage observations fail. Coverage refers to saved observations, not unobserved intermediate engine events.
4. Explicit completed/skipped job stage and task totals. A completed stage is attributed as executed only when its whole recorded interval lies within the directly referencing job interval. A stage completed before the job is listed as a historical dependency. Ambiguous partial interval overlap fails; it is not silently reassigned.
5. Every executed stage's raw HTTP task population, exact indices and successful first attempts, unique task IDs, task launch inside its stage interval, and agreement with stage/job completion counts. Conflicting saved populations, missing task responses and shared executed stages fail.
6. All original input, code and reference hashes before and after the audit. Original files are read-only; outputs use new exclusive paths.

The remaining referenced-stage count must match the explicit aggregate skipped-stage count. This **does not establish that an individual absent reference was skipped**. Each absent reference retains `observed_state: null`. The result separately reports `dependency_inventory_complete` and observed executed-work coverage. Physical acceptance, old-failure acceptance and training eligibility are always false.

The success status is `passed_saved_raw_executed_work_only`. It is not Gate A completion. No raw result-value equality, telemetry, full overlap/resource accounting or fresh runtime integration is certified here.

## Remote execution after connectivity returns

First inspect actual processes, active handles, remote dirty files, branch ancestry and available raw evidence. Fetch and fast-forward only when intended paths are safe; preserve unrelated changes. Verify worker/client HEAD and authored file SHA256. Do not restart services to establish availability.

Then launch once, on worker3 in `/mnt/nfs-storage/shashank_prafullathta/implementation`:

```bash
python3 -B scripts/launch_executed_work_audit.py \
  --label executed_work_audit_YYYYMMDD_01 \
  --expected-head FULL_VERIFIED_COMMIT_SHA \
  --latest-start FRESH_ISO_UTC_CUTOFF
```

These are explicit placeholders, not a runnable registration. Choose an unused label and a window suitable for inspecting existing files; record its rationale. The launcher refuses a different checkout, wrong HEAD, dirty intended code/config, expired admission, reused output paths, changed evidence pins or a detected competing executor. It allows the existing labelled persistent Spark backend wrapper to remain running. It never launches SQL, compaction or model fitting.

It creates `results/<label>_launch/{protocol.json,admission.json,launch.json,run.log}` and starts the actual command under `nohup` and `start_new_session` through `run_with_failure_alert.py`. `launch.json` records the actual PID and a first-check estimate of60seconds. This is an inspection estimate, not a promised duration. Failures after allocating an attempt directory are preserved and alerted; malformed invocation, wrong local checkout or reused attempt names are rejected before creating a new run. A failure to save a receipt never kills a live child.

The audit's result will be at `results/<label>/result.json`; the failure notification receipt, if needed, is in the launch directory. Do not rerun the same output path. Do not treat an SSH disconnect as proof of completion. Inspect the actual terminal receipt and process, then mirror and checksum all completed outputs. Append both methodologies and synchronize intended files after the unit.

## Validation and failure decisions

No local runtime validation is authorized by this build. Local source parsing and manual code review are build checks only; they do not import the new modules or audit evidence. No synthetic data or mutations of historical records are used.

| Actual remote outcome | Proceed with | Do not do |
|---|---|---|
| Missing or changed input pin | Recover the exact original evidence and verify provenance | Repin replacement bytes to get a pass |
| Explicit adverse history, ambiguous stage interval or task/count mismatch | Preserve the failure; inspect its concrete job/stage/task and make one mechanism-based repair under a new registration | Drop the inconvenient job, default a counter to zero or retry unchanged |
| Executed-work checks pass, dependency inventory incomplete | Retain both dimensions; review a prospective runtime contract or separately registered event-log evidence route | Accept the old physical campaign or silently relax its gate |
| Complete checks pass on saved evidence | Integrate only under a new reviewed prospective capability protocol | Claim a live controller, resource savings or compaction benefit |

Fresh runtime capability must then cover actual reads and compaction with unchanged correctness/telemetry/publication gates. A saved-file pass alone does not satisfy this.

## Bounded next performance study

After the measurement gate passes, implement one matched full-drain timing adapter. Fix SF10 data, source arrivals/query mapping, starting layout, one rewrite obligation/options, concurrency, observer and engine settings. Change only compaction start time. No-maintenance is a separate mechanism diagnostic and cannot win a comparison by doing less required maintenance.

Measure null-control repeatability first, then the layout effect and interference needed to interpret timing. Proposed early/mid/end starts remain planning choices until exact eligibility/horizon/drain semantics and fresh identities are registered. Every arm must complete the same offered cohort and maintenance obligation; include waiting, service, controller overhead, late drain and final debt. CPU/I/O remain unavailable unless complete attributable counters exist. No arbitrary SLA or weighted objective is introduced.

If the timing effect is negligible relative to noise and overhead, stop increasing model complexity. If simple rules close the useful gap, keep them. Add demand forecasting, learned costs and separate A/B models only through component ablations on development families, with reserved independent families for confirmation. A failed hypothesis triggers a bounded preregistered branch, not an endless measurement-repair programme.
