# Model and capture source: actual validation review

## Implemented

Source revision `343e344c97820dfdaf732320634d587a4331067f`.

- `models/latency.py`: separate A/B, shared conditional log-Ridge/tree candidates,
  independent SQL/SQL-layout/SQL-layout-state medians, training-only transforms,
  content-bound fit authorization, explicit unsupported prediction records.
- `evaluation/paired.py`: retains all IDs and reasons, common-support equal-episode
  MAE, null score with no supported predictions. No missing-value imputation.
- `runtime/publication.py`: new opt-in locked/versioned client-state journal,
  actual after-fsync observed timestamps, per-feature capture identity, direct
  maintenance/query cursor wrappers, cutoff/freshness gates and refused-call logs.
- Organized models/runtime/evaluation and new docs/plans/docs/reviews; historical
  registered files and frozen collectors retain their paths and original hashes.

## Actual worker3 validation

Protocol `protocols/model_measurement_20261022.json` SHA256
`cba6221221030b4d971c740894cdcdc7c8c996526cc47bc748010176eef1e024`.
Detached failure-alert wrapper PID1197167. Started 05:36:13.709302 UTC and ended
05:36:15.907512 UTC, 22 October 2026. Python3.10.12, sklearn1.7.2.

`results/three_model_model_measurement_20261022/result.json` SHA256
`8a2cacf6e0891ff59d94b5370247d75eb1d555cb80e855de60f378be63f4b023`.
`admission_coverage.json` SHA256
`49ddba660f098f1df61481e14f161143a63e1f591a04f850145d008117fd9c45`.
Worker3 launch log `results/three_model_model_measurement_20261022_launch.log`.
Result, coverage, launch log and wrapper PID mirrored under the local result folder;
result/coverage hashes match server exactly. Wrapper finished naturally and was
absent at final process inspection. No failure occurred; no service was stopped.

Passed **registered historical admission and source checks only**:

| Actual check | Observed outcome |
|---|---|
|Decode actual candidate features|All9,923 rows decoded|
|Historical clock ordering|All9,923 capture/intent/call chains checked|
|Historical receipt passed as new live evidence|All9,923 explicitly rejected|
|Original incomplete offered history|987 lack complete60s;4,997 lack complete300s; preserved|
|Known maintenance-state mismatch|One retained, exact ID unchanged|
|Candidate constructor compatibility|Both registered estimator families constructed|
|Fit entry with actual consumed inventory|Rejected before fitting for both families|
|All-unsupported admission comparison|Zero supported rows; null MAE for every method|

The unsupported records above are outcomes of real evidence-admission checks, not
fabricated model predictions or an accuracy result. Historical results remain valid
only within their original documented scope; these rejections do not erase them.

## Pending and limitations

No estimator was fitted or predicted; no old test score recomputed; no SQL or
new physical collection. Parsing/import/constructor checks do not establish fitted
model correctness or numerical performance. No new live publication or cursor call
was exercised, so concurrency, failure durability and cutoff behavior are source
implementation pending genuine physical validation. The source intentionally starts
runtime acceptance false and cannot turn the historical data into fresh evidence.

The new journal has not been wired into an accepted physical collector. Future
integration must register source identity and history/target-expanded bounds, fresh
isolated tables, source roles, cutoffs, freshness age and a noncompeting resource
reservation. Audit actual rows, SQL/table/snapshot/state/call binding and capture
publication overhead before admitting any training data. Never silently loosen
freshness or discard refusals to get a run through.

Separate A/B has two fitted estimators versus one shared model; identical individual
settings do not imply identical aggregate complexity. No acceptance threshold,
uncertainty interval, causally identified A-minus-B label, maintenance policy benefit
or publication novelty follows from these implementation checks.
