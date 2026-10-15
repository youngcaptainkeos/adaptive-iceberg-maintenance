# Cost-model failure audit — 15 October 2026

The user-authorized worker3 audit completed successfully under nohup (PID1700236,
now exited naturally). No SQL, maintenance, model refitting or test-set tuning was
performed. Frozen code/protocol and reports remain onworker3 and were mirrored
locally; all7output-file hashes agree.

## What the audit established

- Saved model predictions, actual CSV targets and training-median baselines
  reconstruct correctly. The recorded negative results are genuine saved outputs.
- All four saved scalers reproduce training-only means and variances within the
  registered floating-point tolerance. This check found no scaler-fit leakage or
  mismatch; it does not prove every other modeling assumption correct.
- The fitted corpus contains **three distinct frozen instrumentation versions**.
  Measurement-version/time differences are confounded with source-family changes.
- Pending-maintenance regression uses **11training rows and18transformed columns**,
  from one training episode. Its centered design rank is10. Rewrite regression
  uses **3training rows and11columns**, rank2. These are very sparse datasets,
  especially when whole episodes are the independent units.
- The shared latency model has1031training rows/19transformed columns, rank16.
  Existing held-out prediction contributions show substantial dependence on
  300-second read-I/O and query categories; some actual test I/O values lie outside
  training coverage. Pending-state predictions show large memory/demand terms.
  Contributions and correlations are descriptive, not proof of the failure's cause.
- Latency errors remain worse than median baselines. No new model was selected,
  accepted, calibrated or authorized for scheduling.

## What this audit cannot establish

It cannot validate the unexercised lock-expiry deferral branch, prove that logging
caused a latency difference, establish generalization, or decide a valid sample
size/power target. A read-only replay cannot substitute for new registered real
experiments. The separate32-file diagnostic export was not used to refit this model.

## Next gate

Freeze consistent measurement instrumentation and preregister independent matched
layout/maintenance-state/source blocks. Collect more independent rewrites and
maintenance-exposed episodes, not just more query rows. Develop simpler or positive-
target candidates using training blocks only, and evaluate on new untouched source
families. Preserve the current failed test results and strong median baselines.

## Artifacts

Remote repository: `/mnt/nfs-storage/shashank_prafullathta/implementation`.

- Log: `results/cost_failure_background_audit_20261015_launch.log`.
- Full diagnostics: `results/cost_failure_background_audit_20261015/report.json`.
- Readable server report: `results/cost_failure_background_audit_20261015/report.md`.
- Independent roundtrip: same directory, `independent_roundtrip.json`.
- Registration: `docs/experiment_protocols/cost_failure_background_audit_20261015.json`.

The old overnight automation remains paused. Laptop closure cannot interrupt the
already completed server audit; both server and local copies are saved.
