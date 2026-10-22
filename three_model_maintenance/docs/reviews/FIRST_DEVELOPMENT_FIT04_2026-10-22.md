# First real exploratory A/B training: all four stages completed

Actual worker3 result,22October2026. This completes the exploratory training and
artifact-integrity unit, not independent accuracy/calibration or a scheduler.

## Execution and preserved failure

Original runtime df7d52a source preflight failed14:31:06UTC on a missing parenthesis
in the new artifact auditor, before any data-verification/freeze/fit/audit stage.
Original wrapper1334777, exit1, ntfyfailureHTTP200; original protocol/launch/logs
preserved. Git25296b0a49fb21abd6f8b57f0c8118ddf4f4e927 corrected the syntax only and
registered a distinct repair01job with unchanged data, estimators and gates.

Fresh nohupwrapper1335477/orchestrator1335478 launched14:33:19UTC20:03:19IST.
No competing collector/trainer at admission. Each child ran through its own ntfy
failure wrapper; no failed model fit/physical run repeated. All stages exit0:

| Stage | Actual UTC start–end | Result |
|---|---|---|
| Raw/source/input verification |14:33:19–14:33:31|Original physical/publication audits and byte-identical reconstructed exports passed.|
| Committed specification freeze |14:33:31–14:33:31|Actual rows/evidence/protocol/parameters bound before fitting.|
| Fit |14:33:32–14:33:36|Two candidate bundles saved, each containing A/B/shared estimators and three median comparators.|
| Artifact audit |14:33:36–14:33:39|Reloaded outputs reproduced; medians/support reconstructed independently.|

Terminal status `completed_exploratory_fit_and_artifact_audit_only`, parentSHA
`3a66a532615bd4ef1d6fbbcfea7d605f3dcfbc8f48cdbb9e432ea848b87c7678`.
Completionntfy deliveredHTTP200. No SQL was submitted by training/auditing.
All completed job/launch directories mirrored locally; rsync -rcni content checks
exit0/no differences. Original server and local copies retained.

## What was actually trained

335complete-history actual04queries,16client-pendingA/319nonpendingB, one whole
known day6development family.335other completed queries excluded for incomplete
60/300s histories as audited;884queuedrequests remain unlabeled. No syntheticdata,
failed03labels, consumed historical test reuse, padding or retuning.

Same14registered pre-query features, measured client service milliseconds. Fixed
log-target Ridge alpha1/tol0.0001/max_iter1000/SVD and depth3/minleaf1/seed20261015
squared-error tree. Each specification produces shared, A and B estimators. Three
standalone medians: SQL, SQL/layout, SQL/layout/state. Median outputs never replace
a refused learned prediction. No validation/test score, winner or uncertainty.

Ridge: each fitted shared/A/B model has17coefficients+1intercept; separate A+B
therefore36parameters versus18shared, not equal parameter count. Tree shared/A/B
node counts15/13/15 and leaf counts8/7/8. Python3.10.12, sklearn1.7.2,
numpy1.26.4, joblib1.6.0. Artifacts use the actual observed support and numeric box.

## Checks and exact evidence

For each bundle,335own-training diagnostic rows reproduced exactly after reload;
all five comparator outputs had finite positive values on their own training
support. Medians and joint cells/numeric ranges were reconstructed from actual
335rows without refitting.335original runtimeFalse receipts were refused by
ordinary live predict() for each bundle, proving this job did not flip those flags.
These checks establish artifact consistency, not prediction accuracy.

Protocol SHA `f0273eb90b694472f4dab6bc5b4e2dd708fdde485dd043908b5494804d74ce97`.
Stage result hashes:

- verification `de35e24ecfdd86123dcbe054adb036f900985b9f4048a200700d8492ed0fbe41`
- freeze `d29b06da33eb94728192b7697adfb86d6b2e2fcb95b519f928517a76e0cea97b`
- fit `eef31faea9e53ee002344bae83ad5203eada0d53dda7e3249380c16256a20076`
- audit `4d10d56590465c5489b1c3ecd8d593ce3f4dcaa9eb7b396f68e92699e52a3131`

Root on worker3 and client `results/three_model_first_development_fit04_20261022_repair01/`.
Actual saved files:

- `fit/log_ridge.joblib`:SHA `e72129a1cdeaf51a32e0553b2e6d07ef61a6911732f98aefc66f889df86e5108`
- `fit/positive_leaf_tree.joblib`:SHA `130766feb432aea7558b014f851cfde7cd546e79682e723acf42eb8ac947ffd5`
- `fit/model_card.json`:SHA `79926912159f9b73f7694aab1147ab8309fa12558acebbcbd9609ef777c403c1`
- `fit/*_training_diagnostic.jsonl`, `freeze/*_authorization.json`, `verify/result.json`,
  `audit/result.json`, per-stage logs, original registrations and complete lineage.

Training source/code explanation: [registered plan](../plans/FIRST_DEVELOPMENT_FIT04_2026-10-22.md).
Originalfit04registration remains failed; repair01 has separate identities/receipts.
No original raw/export fit/runtime flag was rewritten. Offline authorizations are
new scoped audit outputs, never acceptance of a live predictor or scheduling policy.

## Critical limitation and next gate

Every eligible A row has16files, every eligible B row has1file. Maintenance state
and layout are confounded in this training set. We cannot identify maintenance's
separate effect, compare compact/defer counterfactual costs or claim superiority of
three models.16Aqueries from one maintenance episode are not16independent episodes.
The fitted training-support contract correctly lacks B-on16files support here.

Next registered collection must obtain nonpending queries on the same eligible
fragmented layouts as pending queries, with complete genuine offered histories,
plus multiple disjoint source-family/whole-episode blocks. Keep existing fitted
artifacts frozen; do not tune from pseudo held-out rows. Register independent
train/validation/calibration/test and parameter budgets before new outcome use.
C/demand forecasting and rewrite-cost training were outside this job and remain
separate gates. No deployment/scheduler/calibration/publication-readiness claim.
