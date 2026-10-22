# Three-model maintenance candidates

Main owns this package. Queue-aware implementation belongs to the other chat in
`queue_aware_maintenance/`; it is read-only to this package. Neither architecture
is accepted. The opt-in registered collection runtime launches real SQL for
engineering evidence; it does not implement a learned maintenance scheduler.

- **A:** query service milliseconds conditional on observed client maintenance
  pending. This is not proof of active Spark overlap or a causal slowdown.
- **B:** query service milliseconds without client maintenance pending, conditional
  on actual layout. No invented fragmentation growth or counterfactual label.
- **C:** offered query arrivals from past-only observations. Original Snowset SQL
  mix and ingestion are unavailable; a round-robin benchmark mix is imposed, not
  recovered from source. Counts are not CPU utilization.
- Rewrite duration and layout transition need separately evidenced estimates;
  they are not output of a query-service A-minus-B subtraction.

## Current implementation

`contracts.py` specifies candidate-only model cards/prediction records: explicit
units, source-family roles, actual feature availability, model/evidence hashes,
condition, support and no fabricated uncertainty. Unsupported predictions have no
value. The contract rejects implicit scheduler/calibration promotion and unknown
query predictors. It does not load any legacy joblib or provide a fitted predictor.

`audits/readiness.py` verifies SHA-bound existing candidate CSVs and independent
receipt, source-family membership, pre-feature telemetry frontier, numeric fields,
completeness and joint query/layout/client-state support. It records consumed test
history and forecast scope. Success means the audit completed; its report can and
currently must withhold new fitting. This is not another raw Spark reconstruction.

Registered job (worker3 only, detached failure wrapper; use unique attempt paths):

```bash
python3 -B -m three_model_maintenance.audits.readiness \
  --config three_model_maintenance/protocols/readiness_20261022.json
```

A/B/shared training, future C inference and model-card runtime validation are
pending the gates in `docs/IMPLEMENTATION_PLAN_2026-10-22.md`. No runnable scheduler
or trained candidate bundle is claimed by adding this package.

`preparation/fit_registration.py` inventories consumed sources and exposes a
structural candidate-registration check. It cannot authorize fitting: independently
verified source identity, expanded bounds and immutable pre-outcome registration
remain mandatory. No prospective end-to-end validation is claimed without real new sources.

## Package map

| Folder | Contents |
|---|---|
|`models/`|Separate A/B, shared conditional and independent empirical candidates.|
|`runtime/`|Opt-in future client-state and durable feature-publication journal.|
|`evaluation/`|All-ID coverage and paired equal-episode error reporting.|
|`preparation/`|Raw evidence binding and source/fit-registration guards.|
|`audits/`|Read-only actual-evidence validation commands.|
|`protocols/`|Registered hashes, parameters, input/output paths and rationale.|
|`docs/plans/`, `docs/reviews/`|New implementation plans and actual validation reviews.|

Earlier flat documents/protocols retain their exact paths for historical references.
See [model/capture plan](docs/plans/MODELS_AND_CAPTURE_2026-10-22.md).
Estimator and new publication source exists; no accepted fitted bundle or validated
new physical collector is implied. No current source inventory grants fitting.

Actual scoped validation outcome and remaining gates: [model/capture review](docs/reviews/MODELS_AND_CAPTURE_2026-10-22.md).

Real detached collection registration and code explanation: [live capture launch](docs/reviews/LIVE_CAPTURE_LAUNCH_2026-10-22.md). Its saved launch review is not a terminal success receipt; inspect server progress/result for current state.

Sample-frontier repair and running recovery: [registered plan](docs/plans/FRONTIER_REPAIR_2026-10-22.md), [actual regression/launch](docs/reviews/FRONTIER_REPAIR_LAUNCH_2026-10-22.md). Use the terminal server receipt for final status.

Attempt03 failed inventory freshness before compaction. Attempt04 evidence placement/
terminal archive integration is registered in [the plan](docs/plans/FAST_EVIDENCE_COLLECTION_2026-10-22.md);
inspect actual server receipts for execution status. No fitted A/B bundle is implied.
