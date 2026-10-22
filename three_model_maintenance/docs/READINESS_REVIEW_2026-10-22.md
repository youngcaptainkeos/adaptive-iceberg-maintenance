# Three-model readiness review — 22 October 2026

## Completed unit

Implemented separate candidate contracts and read-only model/schema/source support
audit. Queue-aware package, old model weights, consumed test predictions, physical
protocols and frozen measurement runtimes unchanged. Worker3 auditv2 passed its
provenance/schema/availability census and correctly withheld fitting. This is not
a raw Spark re-audit, model accuracy test, validated inference adapter or scheduler.

Runtime revision66ab2ae, nohup failure wrapper1176176, source/hash registration
`three_model_maintenance/protocols/readiness_20261022_v2.json`.
Receipt `results/three_model_readiness_20261022_v2/result.json`, SHA256
`764dacc28c7cc8104f759c496500359a3270d575d6cf853ba0293866eb16e5e3`.
Server log `results/three_model_readiness_20261022_v2_launch.log` mirrored locally
under that result directory. Input CSV and verification hashes match registration.
First report is preserved; v2 explicitly adds all-zero support combinations instead
of displaying only states observed somewhere. Neither run loaded/fitted/scored
models, issued SQL or generated data. All four package Python sources were parsed;
readiness imports candidate contracts. Runtime card/prediction semantic validation
is source-only pending actual newly bound artifacts/request records.

## Measured support under unchanged full60/300s history eligibility

| Historical source family | A: client pending | B: client not pending | Rewrite operations |
|---|---:|---:|---:|
|0 former training|22|1569|4|
|1 former validation|25|1647|4|
|2 consumed one-time test|23|1640|4|
|Total|70|4856|12|

All9923query rows and18episodes retained in the census;4926queries have complete
histories and4997do not. Twelve query/layout/state cells have zero complete-history
support across the three families: every queryID0–3on filecount1with pendingTrue.
These are enumerated absent combinations, not fabricated examples; they may be
structurally unavailable under the observed commit/visibility schedule. Do not
force such states into collection or interpolate a valid prediction. Observed
pending queries on16/32files are still sparse and dependent within episodes.

A predicts service under observed client-pending condition; active engine overlap
and causal slowdown are different labels. B is layout-conditional without client
pending; unchanged table size/one source/one client do not establish fragmentation
or interference generalization. A−B cannot label unobserved action effects.

## Readiness decisions and next implementation

- **New independent cost fitting withheld.** Three existing families have all been
  used, including the former test. Preserve history and register genuinely fresh
  source roles before a new candidate comparison/calibration/test. Additional
  repeats of a known window remain the same connected source family.
- **A inputs:** compact observed-state predictors exist; richer planned rewrite
  size/progress inputs are not in this export. Actual rewritten bytes are outcomes
  and cannot silently replace a pre-query planned-work feature.
- **Availability adapter:** export carries per-episode monotonic feature clocks.
  Bind actual raw event UTC/runtime correlation before issuing the new cross-process
  predictor request; do not manufacture UTC from the next query's start time. The
  raw join can be implemented/read-only audited before new collection.
- **C:** historical count diagnostic uses registered1/5/10bin horizons, but its
  bin duration must come from source/config before conversion to seconds. It is
  not a deployed predictor, original SQL mix, ingestion or futureCPU forecast.
  Review causal prefix/split/version/artifact availability before adapting it;
  no legacy joblib deserialization/promotion in this unit.
- **Next ready source job:** implement raw-feature availability join and candidate
  artifact/fit-registration gate, then inspect untouched-source inventory without
  cost-outcome selection. Prepare A/B/shared empirical and compact candidate trainer
  against that registration, with no old-test retuning. This precedes collection
  requests; coordinate physical reservations with queue owner. No large experiment
  campaign or automatic scheduler launch is authorized by this review.
