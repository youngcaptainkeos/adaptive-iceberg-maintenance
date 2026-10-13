# Fail-closed experiment contract

Implemented: 2026-10-13. This step removes fabricated-input paths and adds refusal
gates. It does not approve a new experiment or certify the old models. The legacy
collector, evaluation, reset and shell launchers are blocked until event logging,
time-aware telemetry and decision logic are repaired. Preflight is read-only.

## What changed

- Trace replay has no missing-file fallback or invented diurnal curve. It requires
  a provenance manifest, checked source/derived/transform hashes and original timing.
- Training has no mini/test filename mode, artificial compaction targets,
  missing-feature imputation, fixed calibration offsets or reused data splits.
- Calibration uses the maximum absolute residual in each experiment block, with
  an actual finite-sample order statistic. Too few calibration blocks fails; no
  clipping or replacement bound. This is not a guarantee under distribution shift.
- All supported query types must be represented in each regime and split. Separate
  experiments and chronological purge gaps prevent same-run/window leakage.
- Every compaction target must overlap a matching successful physical rewrite.
  Baseline queries must overlap no rewrite attempt, including no-ops.
- Both models must meet declared per-query MAE, coverage and baseline-improvement
  acceptance gates before publishing any model bundle. No acceptance values are
  invented in code. Zero measured residual bounds are valid, not fabricated by default.
- Model bundles record schema, source/protocol hashes, split counts, calibration
  unit, per-query metrics and model hashes. Loading validates evidence before pickle.
- No existing model directory is overwritten. Publishing occurs only after both
  models pass; old artifacts remain historical evidence.
- Preflight verifies registered benchmark/trace artifacts, recorded code revision,
  unchanged tracked experiment Python sources, engine/version, table identity,
  current snapshot and metadata record/file counts. It does not scan the table or
  issue writes. An offline pass does not establish live connectivity.
- Root launchers no longer auto-start Spark, reset tables, train or promote models.
  Implicit earliest-snapshot resets and the simulation-capable legacy agent are retired.

## Artifact specifications

Paths in JSON are relative to the manifest directory or absolute. Every referenced
artifact is an object with `path` and lowercase `sha256`. These are provenance
checks, not authentication of arbitrary assertions in a user-written JSON file.
Physical logs and transformations still need independent methodological review.
No runnable example configuration is supplied: we do not yet have an approved
replay transformation or adequately labelled physical training dataset.

### Observed trace manifest

Required fields:

- `schema_version`: `verified_trace_v1`; `origin`: `observed`.
- `source_url`: publisher/source HTTPS URL.
- `source`, `derived`, `transformation_code`: file references with SHA256.
- `transformation_description`: observed source/member selection, aggregation and
  benchmark mapping. CPU usage must not be labelled as observed SQL arrivals.
- `time_mapping`: `original_elapsed_seconds`. Compression, repetition and invented
  events are not supported in this step.
- `normalization_min`, `normalization_max`, `normalization_rationale`: declared
  scaling with nonzero range and no test-based tuning.
- `regime_boundaries`, `regime_rationale`: three ordered boundaries in (0,1), used
  only for reporting categories. They are no longer embedded policy numbers.

Derived CSV columns: `elapsed_s`, `observed_demand`. Values must be finite and
nonnegative, times start at zero and strictly increase, normalization must contain
all measurements, and the observed timeline must cover the requested interval.
Replay selects the last recorded bin at its original elapsed time; no sinusoid,
time rescaling, padding, looping or invented interpolation is performed.

### Physical experiment manifest

- `schema_version`: `physical_experiment_v1`.
- `experiment_id`, `purpose`, `configuration_rationale`, `code_revision`.
- `benchmark_sources`: nonempty artifact list; `generator_provenance`: artifact.
- `trace_manifest`: artifact reference to the above manifest.
- `duration_seconds`, `trace_start_offset_seconds`.
- `engine`: `host`, `port`, `username`, `expected_version`.
- `table`: `identifier`, `snapshot_id`, `record_count`, `file_count`.

Use the standalone preflight with `--manifest` and, for physical metadata checks,
`--check-live`. `--model-dir` additionally verifies the accepted training bundle.
Preflight does not enable the retired execution paths. Dataset hashes may require
substantial I/O; no cached/invented hash is substituted.

### Physical training manifest and protocol

Data manifest requires `schema_version: physical_training_data_v1`,
`origin: physical_spark_iceberg`, `training_data`, `compaction_events`, and a
nonempty `execution_evidence` list of checked physical artifacts plus checked
`raw_statement_events` JSONL references.

Training CSV has one completed physical query per row, not idle telemetry ticks.
Required measured features are the current nine telemetry/table features. Required
provenance fields: `measurement_id`, `experiment_id`, `split`, `query_id`,
`compaction_active`, `feature_timestamp`, `query_start_time`, `query_end_time`,
`compaction_event_id`, and the appropriate physical latency target column.
Timestamps must be timezone-qualified ISO strings. Features must be available
before query start. Target latency must match the observed monotonic call/result interval. See
`client_statement_timing_contract.md` for mandatory integer clocks, duration
decomposition and exact raw-ledger binding; UTC timestamps serve chronology.

Compaction-event CSV requires `experiment_id`, `compaction_event_id`, `start_time`,
`end_time`, `rewritten_data_files_count`, and `status` (`success` or `no_op`).
Unknown/failed/incomplete events cannot validate a training dataset. Preserve failed
events elsewhere; curation must not hide their interference with included queries.

Protocol requires `schema_version: physical_training_protocol_v1`, `rationale`,
`alpha`, `feature_window_seconds`, `purge_seconds`,
`min_queries_per_split_per_query`, `min_compaction_events_per_split`,
`minimum_test_coverage`, `minimum_relative_mae_improvement`,
`maximum_test_mae_ms_by_query`, and `model_parameters`. Hyperparameters must include
`n_estimators`, `max_depth`, `learning_rate`, `loss`, `random_state`.

Choose those values from pilot variance, scientific precision/risk goals and
training-only tuning, before final evaluation. Acceptance coverage cannot be below
the declared nominal target. A finite block-calibrated bound requires enough
calibration experiment blocks for rank `ceil((n+1)*(1-alpha)) <= n`.
The four query IDs are the vocabulary of the four existing SQL templates, not a
policy threshold. Future query vocabularies require a separately reviewed schema.

## Validation performed in this step

- Syntax/AST and shell parsing, plus source audit for removed fallbacks.
- Actual SF1 files accepted against their existing checksum manifest.
- Actual RUN_002 training CSV rejected for missing physical query/event fields.
- Actual historical model metadata rejected before model deserialization.
- Actual resource-inventory JSON rejected as an experiment/trace manifest; an
  inventory cannot authorize execution.
- Retired launcher refusals checked before any startup, reset or workload.

No fake dataset, mock model, simulated query, fabricated configuration, model fitting
or new physical benchmark was used in these checks. Positive end-to-end training and
live preflight remain untested until legitimate approved artifacts exist. Historical
mock/synthetic unit tests are preserved but not run or cited as evidence.

## Next gate and remaining limitations

Repair query/maintenance event logging, collection cadence, offered-load generation
and reset postconditions; then review a real trace transformation and preregister
the collection protocol. Only after that may execution guards be replaced with the
repaired implementation. Dead legacy collector/decision execution bodies have been retired. Physical
task-overlap/telemetry/layout export binding and offered-load execution remain
unimplemented; a matching client rewrite interval alone is insufficient to certify
a useful engine-overlap target.

This is a refusal/provenance foundation, not a validated forecasting scheduler.
Coverage thresholds alone do not establish coverage precision, independence or
safety under shift. Record run-level uncertainty and decision quality later.
