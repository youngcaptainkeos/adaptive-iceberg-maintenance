# Three-model source and raw evidence review — 22 October 2026

## Implemented and executed

Implementation revision: `29834c9047f97b5d3715323030b64730ecf73de1`.
Added a bounded, hash-pinned source audit and a historical raw-feature binder.
Both actual audits ran on worker3 detached through the failure-alert wrapper;
no local fitting/test execution, SQL, new physical experiment or legacy weight loading.

| Job | Wrapper PID | Actual result | Receipt SHA256 |
|---|---|---|---|
|Source boundaries|1179956|Passed the registered 13-file structural scope|f303a77e70830837f234483881b0a4abd15a67e44d8b3c49386f0c792d982625|
|Historical raw binding|1180090|Completed 9,923 records across 18 episodes; one ambiguity retained|7ea62756ce2d4dd2cd5453633a8ad20bd8ba9b30a43a231fb7cd46834415606e|

Logs: `results/three_model_source_integrity_20261022_launch.log` and
`results/three_model_raw_features_20261022_launch.log` on worker3.
Receipts: respective `results/three_model_*_20261022/result.json` directories.
Both result directories and bound rows were mirrored locally and exact SHA256
agreement verified. Bound JSONL SHA256:
`95bd3748b7734dc66c9cc07c441eda26de2269e95b4370064ebee8fbf1323db3`.
Raw binding ran 04:27:23.977–04:27:32.212 UTC. Both jobs finished; no new model
training or scheduler is running as part of this unit. No execution failure occurred;
a completed diagnostic containing a mismatch is not an all-clear certificate.

## Negative findings and limits

1. Episode `sf1_consistent_20261016_14`, measurement
   `5883c0cba14a482788d2f60243156d7e`: timestamp-derived pending state differs
   from prior-log-prefix pending state. The row records
   `historical_binding_consistent:false`; it is quarantined from clean eligibility,
   not deleted or relabelled. All old CSVs and outcomes remain unchanged.
2. Event-log UTC stamps are captured before fsync publication. Exact feature
   availability is therefore null; the later actual client-call timestamp is only
   a recorded bound. Prior-log ordering does not prove application-thread visibility.
   Runtime adapter acceptance remains false for the entire historical export.
3. All three source families are consumed history. Every bound row records fresh
   training eligibility false. No old test was rescored or reused as a fresh test.
4. Correction to the plan's earlier metadata statement: the local legacy metadata
   has eight features; worker3's preserved dirty metadata has thirteen. The latter
   SHA256 is `b0f869ae0b404f794e0194c937e94cc743c91e74d48f25152589849a8394b1d0`.
   Neither supplies the required new schema/validation record. No weights loaded.
5. Source checks cover named structural/import/retirement boundaries, not semantic
   proof of every repository line. Historical diagnostic forecasters and empirical
   comparators are not accepted A/B/C models. New unsupported inference must return
   no prediction, never silently replace a failed learned prediction with a median.

## Next implementation gates

1. Add consumed-source registry and fit-registration validator, rejecting role
   overlap, incomplete provenance and consumed-test reuse before opening outcomes.
2. Implement A/B and shared conditional estimators with identical eligible rows,
   declared predictors and training-only transforms. Report empirical competitors
   separately. Only 70 complete-history pending-state rows currently exist; that
   sparsity cannot be repaired by synthetic augmentation or weaker gates.
3. Package C as a past-only arrival-count forecaster with explicit history/horizon
   and source/runtime time mapping. No original SQL mix, CPU or ingestion forecast.
4. Register new independent collection, measurement and resource conditions before
   physical work; coordinate with queue track. Freeze development choices before
   new whole-family evaluation, then independent calibration and decision tests.
5. Evaluate whether forecasting improves real maintenance decisions over faithful
   simple/learned alternatives. Three models alone are not a novelty claim.

Current deliverable is verified historical provenance plus explicit unresolved
boundaries. A/B/C fitting, semantic predictor validation, calibration, independent
policy benefit and publication readiness remain unestablished.


## Subsequent consumed-source gate completion

Implementation `3efc02ea7052c9f46151e574775064464f9edc37` added
`preparation/fit_registration.py`. Detached worker3 actual inventory completed
05:24:32.984–05:24:32.997 UTC with all18episodes/9923queries and3families
reconciled. Each actual consumed family was detected by the same dependency helper
used by the prospective validator; one quarantined measurement preserved.
Launcher shell PID1194025; wrapper/client PIDs not separately retained.
Report `results/three_model_consumed_inventory_20261022/result.json` SHA256
`25d810b5c62a2f5e0fc82adedb39fe98330ab702d811236a74d3656cac7416d7`;
registry SHA256 `e7918bdb77440e2e041572414432d54990c42f3edb1fed8317983a3035308495`.
Mirrored and hashes matched. No execution failure, fit, scoring or SQL.
Full prospective path not exercised without a genuine new registration; independently
verified identities, expanded source bounds and pre-outcome protocol freeze remain
required. `fit_authorized:false` even for a structural registration pass.
