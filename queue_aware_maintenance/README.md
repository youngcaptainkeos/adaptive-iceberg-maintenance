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
