# Registered four-stage exploratory training job04

User explicitly authorizes all four steps as a detached worker3 job with ntfy on
failures. No new physical experiment/SQL, no tuning, no automatic retry.

## Inputs and scope

Use only verified collection04, physical result SHA
`a9c5188db00e679cb1944593aea884263d0f27f23676c47bbe507dcda0083736`
and candidate result SHA
`9650495f8b4ee19d544ff84a24a355d676381c35ff05d83b5745289a2e8f7e2c`.
335complete-history observations:16A/319B.335other completed queries have missing
histories and remain excluded with explicit reasons.884queuedrequests are not
labels. Source day6 is a known engineering family; the entire episode is training.
No row/random split, validation/calibration/test scoring, winner or error metrics.
The older03fit registration remains unchanged and blocked by its failed producer.
This new freeze is before fitting only, after development outcome inspection.

## Pipeline

1. `training/data.py`: check pinned terminal producer/config/export/input hashes,
   source Snowset/cohort/bin/SQL vocabulary, consumed-family bounds, full canonical
   archive manifest. Run original physical/publication audits and independently
   re-export feature/target/history bindings to a new verification directory.
   Require the actual CSV/publication JSONL bytes to match existing candidates.
   Preserve original runtimeFalse, exclude only actual incomplete histories.
   Save exact per-row and per-receipt hashes in a new offline data audit.
2. `training/pipeline.py` freeze stage: require protocol committed unchanged and
   every source hash unchanged; record current commit, parameters, train-only
   source roles, feature order, actual row/evidence content hashes and data audit.
   Issue narrow, hash-bound offline authorizations, not a live-runtime approval.
3. Fit existing estimators using identical fixed specifications for A/B/shared:
   log-target Ridge alpha1/tolerance0.0001/max_iter1000/SVD; depth3squared-error
   tree/min_leaf1/seed20261015. These settings are inherited from the prior source
   registration, not selected from04errors. Same14registered past-observed features,
   measured client service ms; training-only transforms and support bounds. Separate
   A/B total parameter counts may differ from shared; actual counts are saved.
   Compute independent SQL, SQL/layout, SQL/layout/state medians from actual labels.
   Save two joblib bundles, metadata cards and own-training diagnostic predictions.
4. `audits/trained_bundle.py`: verify artifact hashes and freeze lineage, reload
   both bundles, reconstruct medians/cell support/numeric ranges from actual data,
   reproduce each saved prediction and check finite positive values. On unchanged
   original runtimeFalse receipts, ordinary live `predict()` must refuse all335rows.
   No second fit, invented/OOD example, accuracy score or promotion.

## Deliberate API separation

`models/latency.py` keeps ordinary `admission()/predict()` runtime requirements.
`verified_training_admission()` accepts only the exact row/receipt content named in
an actual offline data audit. `fit()` binds that receipt/rows/evidence/protocol and
parameters; serialized bundles retain authorization hash. The separate training-
diagnostic method requires the same authorization and original audited rows.
There is no mutated copy of original runtime flags, generic missing-data allowance,
legacy predictor substitution or fallback median inside another estimator.
Median methods are separately named comparator outputs, not replacements on failure.
Bundle metadata is scoped offline; no live-serving model-card/prediction acceptance
is granted by the artifact audit. Missing support has no value/uncertainty interval.

## Execution and failure behavior

Parent `python3 -B -m three_model_maintenance.training.pipeline --protocol
three_model_maintenance/protocols/first_development_fit04_20261022.json` under
nohup through the mandated failure wrapper on worker3. Each child stage also has
its own unique label/log/failure receipt. Same shared collection/resource locks
prevent overlapping cooperative runs. No process/service is stopped. Parent
records attempted fitting as unknown until the child succeeds, rather than falsely
reporting no fit after a partial failure. Failed artifacts/logs remain intact.
Success ntfy reports completed exploratory training, never predictive accuracy.

Output `results/three_model_first_development_fit04_20261022/`: registration,
progress/result, verify/freeze/fit/audit subdirectories, per-stage logs and receipts.
Estimated2–5minutes after launch, depending on real source rehash/audit time.
No new physical workload. Next gate after all four pass: diverse whole-episode
collection for independent comparisons, much more A support, and a separately
registered calibration/validation/test plan; one episode is not enough.


## Firstfit04 initial source-check failure and repair01 registration — 22 October 2026

Committed df7d52ab91aef083d03972f76ee8d5f22f71ebb1 pushed/worker3fastforwarded with all10intended fileSHA agreement. Actual parentwrapper1334777 launched14:31:05UTC20:01IST. Initial check_registration AST parse failed14:31:06UTC: audits/trained_bundle.py median reconstruction loop missing closing parenthesis. Failure occurs before output-root creation, any verify/freeze/fit/audit stage and any estimatorfit; allfourstages unattempted. NoSQL/newlabels/modelcreation, no fitted-success claim. Parentntfyfailure deliveredHTTP200 idq1OQhCJgIMnn; original exit1/runlog/receipt retained and mirrored results/three_model_first_development_fit04_20261022_launch. LogSHA8701adb3997bd1dc4cd78b7349bb74911b70772579c01368a2f8e4cb160f2c29; alertreceiptSHA3f7722ff8ef7fbeae72ec7e1780f176449470ab22acf1186c519964fdcf0a7f5.

Corrected syntax only, reviewed remaining loop/branch code. New protocols/first_development_fit04_repair01_20261022.json freezes corrected auditor/source SHA, identical real04inputs/14features/parameters/wholefamilytraining-onlygates and fresh output results/three_model_first_development_fit04_20261022_repair01, distinct labels/receipts. Originalfailed protocol/source revision preserved in Git and original launchfiles untouched. This is an identified engineering repair, not repeated model tuning or physical retry. Newattemptplanned detachedworker3 with original sourcechecks/allfourstages/ntfy; ETA2–5minutes, launch/outcome follow. No runtimeaccepted flags modified.
