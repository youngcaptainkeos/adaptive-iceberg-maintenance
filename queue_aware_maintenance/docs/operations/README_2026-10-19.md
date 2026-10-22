# Queue-aware Iceberg maintenance feasibility

New isolated implementation for the19–20October2026study. Prior scripts, raw failures, fits and archives remain intact.

Goal: a runnable external controller that evaluates start/wait/noaction using actual backlog, real historical service/rewrite evidence and causal demand forecasts, followed by a substantial real Spark/Iceberg comparison. No publication-level novelty or improvement is assumed. Counterfactual simulator predictions are explicitly estimates, never physical labels.

Source files live here, including provenance-bound frozen evidence primitives in instrumentation/. Server jobs launch via the existing failure-alert wrapper under nohup. Physical cohorts must retain all offered real trace arrivals and measure waiting plus execution until drain, with explicit administrative cutoff/censoring if incomplete; no successful full-drain claim from a partial run.

See STUDY_PLAN.md and progress.json/receipts under results/queue_aware_maintenance_20261019 on worker3. Final deliverable requires controller source, reproducible protocols, actual server tests, complete physical cohort or preserved explicit failure and feasibility report, causal-source audit, raw evidence and SHA verification on both machines. A negative result is reported honestly; it cannot be relabelled as an effective controller proof.

## Reproduction and current state

Physical recovery registration: `protocols/physical_study_container_repair_20261019.json`.
The live runtime is frozen at `af274dba5fc59b0c2acc3892d8c46d34d144928b` in
`/tmp/capstone_queue_aware_20261019_container_repair` on worker3. Canonical analysis
code can advance without changing this running checkout. Do not launch a second
physical coordinator while its PID or child is live. Exact current handles and
cutoffs are in `OVERNIGHT_HANDOVER.md`.

The first attempt remains 0 passed / 1 failed / 7 unattempted, with its table and
raw SQL retained. The actual-client row-container defect was verified by a
read-only query and repaired without relaxing zero logical difference. Recovery
uses eight fresh table names. Neither recovery launch nor source preflight is a
completed proof of concept.

Run these steps **on worker3 only after the complete cohort is terminal**. The
registration utility refuses an incomplete cohort; use a unique output path if
an earlier analysis failed, preserving its failure. It binds actual evidence
hashes rather than accepting a placeholder hash.

```bash
cd /mnt/nfs-storage/shashank_prafullathta/implementation
python3 -B queue_aware_maintenance/register_comparison.py \
  --cohort-result results/queue_aware_maintenance_20261019/cohort_container_repair/result.json \
  --semantics-audit results/queue_aware_maintenance_20261019/simulator_semantics_audit/result.json \
  --protocol results/queue_aware_maintenance_20261019/comparison_protocol.json \
  --output-directory results/queue_aware_maintenance_20261019/comparison
nohup python3 -B -u scripts/phase6-live-evaluation/run_with_failure_alert.py \
  --label queue_aware_independent_comparison_20261019 \
  --receipt results/queue_aware_maintenance_20261019/comparison_failure_notification.json \
  -- python3 -B -u queue_aware_maintenance/compare_study.py \
  --protocol results/queue_aware_maintenance_20261019/comparison_protocol.json \
  > results/queue_aware_comparison_20261019.log 2>&1 < /dev/null &
```

The registration step is evidence binding, not a test. Actual comparison runs
under the detached alert wrapper. Retain its PID/log and inspect its terminal
receipt. Source/import preflight does not substitute for this comparison.

Outputs: per-episode reconstruction receipts, `result.json` and
`feasibility_report.md`. The audit checks every actual SQL result, snapshot,
engine task, telemetry window, FIFO transition and full-population response
integral. It rebuilds policy backlog from past raw transitions and replays the
fixed policy implementation. This is independent raw-input reconstruction, not
an independent implementation of the policy mathematics; core preparation
separately reconstructs empirical estimates and FIFO identities.

Interpretation: compare total response, queue waiting, service, drain duration
and rewrite duration/count separately. Report negative or tied results. Two
contiguous windows are one source-day family; they cannot establish confidence
intervals, calibration, broad superiority or publication novelty. Real Snowset
arrival timing is mapped to four benchmark SQL templates, not original Snowflake
SQL. Physical table bytes remain on worker3 unless separately backed up;
mirrored raw receipts are not a physical warehouse backup.


## Superseding model audit (19 October13:42UTC)

The original fluid model failed its query/snapshot semantics gate:61 actual-source
boundary cases, with9923 historical whole-call targets independently checked.
Its ongoing physical cohort must retain that limitation even if all raw physical
audits pass. `snapshot_simulator.py` and `snapshot_policy.py` are separate repaired
candidates. Detached real-source reconstruction passed131838query/candidate checks
and61boundary cases; it is not physical validation. Both repaired initial model
choices are60seconds, versus immediate for the original model, with only about
22seconds predicted total-response advantage over immediate across thousands of
queries. This small model margin is not measured evidence of a policy benefit.
No new physical run may silently substitute the repaired model into the frozen
original cohort. Future use requires fresh registration, model receipt/hash
binding, actual controller integration and a complete physical comparison.

## Corrected full-study deliverable (prepared, not physically validated)

Both repairs are integrated explicitly for future episodes:
`policy_model_version=snapshot_whole_call_v2` and
`telemetry_wait_contract=durable_publication_v2`. Old protocols retain their old
implementations. The corrected eight-arm protocol is
`protocols/physical_study_snapshot_publication_20261019.json`, using the next
chronological windows (3,094 / 3,188 arrivals). Model bytes remain identical to
the historical model; no prospective physical labels were fitted.

Prepared worker3 runtime:
`/tmp/capstone_queue_aware_20261019_snapshot_publication`, frozen revision
`d5e7c4002f49c409ae0b1e01863ceea40368d39a`. Its actual provenance is saved in
`results/queue_aware_maintenance_20261019/prepared_snapshot_runtime.json`.
Preparing this checkout did not launch an experiment.

First inspect actual running handles and the resource-admission decision. This
command is a real operational diagnostic; it submits no SQL. Use a new output
path for a later recheck, preserving previous decisions.

```bash
cd /tmp/capstone_queue_aware_20261019_snapshot_publication
nohup python3 -B -u scripts/phase6-live-evaluation/run_with_failure_alert.py \
  --label queue_snapshot_publication_admission_before_launch \
  --receipt results/queue_aware_maintenance_20261019/admission_before_launch_failure.json \
  -- python3 -B -u queue_aware_maintenance/resource_admission.py \
  --study-protocol queue_aware_maintenance/protocols/physical_study_snapshot_publication_20261019.json \
  --output results/queue_aware_maintenance_20261019/admission_before_launch.json \
  > results/queue_snapshot_publication_admission_before_launch.log 2>&1 < /dev/null &
```

Only if resources are genuinely free and full admission passes, the registered
coordinator can be launched as follows. It rechecks admission before any SQL.
Do not run this while the original coordinator is live. Noclobber prevents
silently replacing an existing log.

```bash
cd /tmp/capstone_queue_aware_20261019_snapshot_publication
set -o noclobber
nohup python3 -B -u scripts/phase6-live-evaluation/run_with_failure_alert.py \
  --label queue_snapshot_publication_study_20261019 \
  --receipt results/queue_aware_maintenance_20261019/cohort_snapshot_publication_failure_notification.json \
  -- python3 -B -u queue_aware_maintenance/run_study.py \
  --protocol queue_aware_maintenance/protocols/physical_study_snapshot_publication_20261019.json \
  --expected-revision d5e7c4002f49c409ae0b1e01863ceea40368d39a \
  > results/queue_snapshot_publication_20261019_launch.log 2>&1 < /dev/null &
```

Initial admission at14:09UTC was rejected because both real execution locks were
held. Its model-only latest feasible launch was14:53:53UTC (20:23:53IST),
excluding additional initialization/audit overhead. This is not a permission to
cancel running work, extend cutoffs, shrink the cohort or promise completion.
If admission cannot pass, the corrected physical study remains unattempted.

For corrected-cohort comparison, use its actual terminal `result.json` and the
SHA-bound `snapshot_model_reconstruction/result.json` semantics receipt when
registering the comparison. The comparison code verifies the model version
against frozen source. Continue to preserve original failed-model outcomes and
all unattempted counts. See `FEASIBILITY_REVIEW.md` for unresolved research and
physical-validation requirements.

## Active corrected study and terminal analysis (supersedes original live handles)

As of19October14:40UTC the original study was intentionally aborted under
explicit human authorization; its partial evidence remains preserved. The active
corrected study is `cohort_snapshot_publication`, frozen at
`d5e7c4002f49c409ae0b1e01863ceea40368d39a`; coordinator226240. See the append-only
handover for newer authoritative observations. The original comparison example
above is historical and cannot analyze the aborted original cohort.

After the corrected study actually terminates with eight passed arms, zero
failed and zero unattempted, use the following on worker3. These paths are new;
never overwrite existing failed analysis output or refit from these results.
Registration rejects partial cohorts. Run the comparison only within the
remaining authorized deadline, after inspecting actual active work.

```bash
cd /mnt/nfs-storage/shashank_prafullathta/implementation
python3 -B queue_aware_maintenance/register_comparison.py \
  --cohort-result results/queue_aware_maintenance_20261019/cohort_snapshot_publication/result.json \
  --semantics-audit results/queue_aware_maintenance_20261019/snapshot_model_reconstruction/result.json \
  --protocol results/queue_aware_maintenance_20261019/snapshot_comparison_protocol.json \
  --output-directory results/queue_aware_maintenance_20261019/snapshot_comparison
nohup python3 -B -u scripts/phase6-live-evaluation/run_with_failure_alert.py \
  --label queue_snapshot_independent_comparison_20261019 \
  --receipt results/queue_aware_maintenance_20261019/snapshot_comparison_failure_notification.json \
  -- python3 -B -u queue_aware_maintenance/compare_study.py \
  --protocol results/queue_aware_maintenance_20261019/snapshot_comparison_protocol.json \
  > results/queue_snapshot_comparison_20261019.log 2>&1 < /dev/null &
```

Record the actual PID, log and receipt. A terminal comparison pass proves the
registered physical feasibility and reconstruction scope only. Final acceptance
also requires a candid report, full requirements audit and completed-evidence
mirror with server/client hashes. Any incomplete or failed cohort remains
incomplete; do not substitute a surviving-arm contrast.

## Deployed detached terminal follow-up

The current study has a server-side follower, `follow_terminal_study.py`, launched
under the failure-alert wrapper. It performs no SQL or model fitting. It waits
for the identity-bound coordinator (PID plus Linux process start ticks), then
requires the full eight-arm passed result, unchanged frozen analysis sources,
and the authorized analysis launch deadline. Only then does it register actual
terminal hashes and launch one detached comparison. Failure and incomplete
cohorts remain failures; existing analysis paths are never overwritten. At the
deadline it preserves active work and records unattempted analysis.

Current registration: `protocols/terminal_followup_20261019.json`. This is a
study-specific process identity, not a reusable template for another PID/run.
Any future study needs a newly observed process identity and fresh output paths,
registered before launch. The deployed invocation and exact source hash are in
`results/queue_aware_maintenance_20261019/terminal_followup_launch.json`.

Read-only checks on worker3:

```bash
cat results/queue_aware_maintenance_20261019/terminal_followup/progress.json
cat results/queue_aware_maintenance_20261019/cohort_snapshot_publication/progress.json
tail -n 20 results/queue_aware_maintenance_20261019/terminal_followup.log
```

While that follower or its analysis child is live, **do not execute the manual
comparison example above**. Inspect its actual process handles and receipt first;
a missing/late monitoring response is not proof that it stopped. A completed
`terminal_followup/result.json` still does not certify the full project: inspect
`snapshot_comparison/result.json`, the generated feasibility report, the final
requirements audit and synchronized raw evidence. No successful deployment or
single completed arm establishes calibration, novelty or policy superiority.
