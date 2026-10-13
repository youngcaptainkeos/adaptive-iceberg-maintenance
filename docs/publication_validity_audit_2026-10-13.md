# Initial publication validity audit

Date: 2026-10-13. Status: **BLOCKED for new publication evaluation**.
Contract: `docs/publication_goals_and_execution_plan.md`.
Machine-readable observations: `docs/publication_validity_audit_2026-10-13.json`.

## Scope and conclusion

Read-only source/schema/model audit and SSH source inventory on worker3. No new
benchmark, simulation, dummy-data test, training, reset, or maintenance was launched.
The earlier worker's RUN_003 was observed without changing its running processes.
These findings do not certify physical origin, model quality, or literature novelty.

The immediate blocker is measurement and provenance integrity, not model count.
Do not add a forecaster or claim a publication result from this pipeline yet.
Nineteen blocker observations were found; these include related manifestations of
the same root issue, not nineteen independent scientific failures.

## Repository integrity

Local and remote tracked HEAD matched `452027613d6deb376e3ea5657fea1468d4ea5251`
before this audit commit. Remote inventory covered 327 project source/configuration
files under scripts/docs and root text sources, excluding vendored repositories,
datasets, warehouse binaries, and caches.

- 277 remote sources were absent locally, including historical phase implementations.
- Four shared sources differed: `docs/methodology_v2_cost_benefit.md`,
  `docs/methodology_working_doc.md`, `methodology_v2_cost_benefit.md`, and
  `run_everything.sh`.
- Remote has substantial untracked historical work. Local has unrelated untracked
  draft 3/chronicle volume 2 and pre-existing changes. None were overwritten or staged.
- Source hash inventory is preserved in the JSON report. Full reconciliation remains
  pending; matching HEAD alone must not be reported as full workspace integrity.

## Real artifact observations

Remote snapshot time: 2026-10-13 16:51:39 UTC (22:21:39 IST).
RUN_003 CSV is a snapshot of an existing run, not a newly authorized experiment.

| Observation | Value |
| --- | --- |
| Collection elapsed | 1799.5 seconds |
| Telemetry rows | 498 |
| Query records with identity | 80 |
| Compaction-labelled query records | 10 |
| File count range | 33–604 |
| Median consecutive sampling interval | 1 second |

Median sampling interval hides long gaps: 498 rows over about 1800 seconds is not
a complete 1 Hz series. Samples-based CPU windows must be replaced with time-aware
windows and measured coverage. Ten compaction-labelled queries are insufficient
for strong per-query held-out accuracy or calibrated-confidence conclusions. Current
labels do not prove physical overlap because query intervals are missing.

RUN_001/RUN_002 local training artifacts lack query identity and event intervals.
Default model metadata remains the older eight-feature version, with test MAEs
about 22–26 seconds; query-aware code does not prove query-aware deployed artifacts.

### Subsequent RUN_003 training log observation

After the source inventory, the existing pipeline completed training and moved to
the baseline evaluation/reset stage. Its physical-run training log reported:

| Model | Total target samples | Test MAE | Test coverage |
| --- | --- | --- | --- |
| A, compaction | 10 | 158672.7 ms | 0.0% (two test records) |
| B, no compaction | 70 | 2445.4 ms | 72.7% |

Model A test R2 was -19381.348 and its calibrated offset 116427.7 ms. The split
contained only one calibration record. Neither model is accepted for publication
evaluation on this evidence. Coverage estimates from these tiny test sets are
diagnostics, not precise population estimates or guarantees.

Despite the results, training saved the artifacts and the shell pipeline advanced.
This directly demonstrates the need for minimum independent calibration/event
coverage, declared model acceptance criteria, and a fail-closed training gate.
The audit did not interrupt or relaunch the pre-existing pilot. Preserve its outputs
as failed validation evidence rather than presenting them as successful models.

## Blocking mechanisms in the code

1. Missing Google trace selects an invented diurnal curve locally and remotely.
2. Training can fabricate compaction latency as baseline latency multiplied by 1.25.
3. Filename containing mini/test activates relaxed training rules. RUN_003's basename
   is training_data.csv, so do not assume that branch was actually taken in this run.
4. Small-sample training reuses observations for train/calibration/test; fixed 50 ms
   bounds replace absent or zero calibration evidence.
5. Current policy projects a fixed two-file increase and has no future-demand model
   or common-horizon cumulative cost calculation.
6. Live CPU window lengths count minute-scale decision samples rather than seconds.
7. Query outcomes are labelled using the collection-time compaction flag, not actual
   event overlap; evaluation discards query records after interval aggregation.
8. Metadata failures become zero-file healthy-looking state. Reset/compaction errors
   require explicit failed-run handling rather than continued success-shaped output.
9. Local master launcher requests a policy the current CLI does not support. The
   remote launcher differs and must be inspected before reconciliation.

Exact source locations are recorded in the JSON report. This is a bounded pattern
audit, not an exhaustive proof that all faulty or hardcoded behavior was detected.

## Claims requiring review

Do not repeat exact OOD safety invariance, guaranteed starvation elimination,
subsecond micro-compaction success, or live subsecond prediction accuracy without
reconstructing raw experiments. Recent draft 3 and chronicle volume 2 repeat some
of these assertions. Preserve drafts, but maintain an evidence-linked claims ledger
before updating paper conclusions. A forecast or tree model does not mathematically
guarantee future maintenance completion or coverage under arbitrary distribution shift.

## Next bounded implementation task

After source reconciliation and checking the existing pilot outcome, implement
fail-closed experiment preflight and remove synthetic trace/training fallbacks.
Require explicit dataset/trace paths with provenance and checksums, verified physical
engine connection, table/snapshot/cardinality evidence, model compatibility, and
disjoint adequate calibration data. Configuration must be explicit and justified;
do not replace old magic numbers with different magic numbers.

Then repair event logging and time-aware telemetry before collecting new training
data. Do not launch another physical evaluation until that gate passes. Completing
this audit is progress on P0, not completion of P0 or approval of existing claims.

## Reproduction of this audit

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/audit_experiment_validity.py
```

Exit code 2 is expected when blockers are found; this is not a benchmark failure.
For remote comparison pass `--remote-inventory` with a fresh read-only JSON inventory
containing root/head/status, observed_at, source_sha256, trace_exists, and run summaries.
The saved report preserves the inspected remote source hashes and observation time.
Do not execute historical synthetic/mock tests as publication evidence.
