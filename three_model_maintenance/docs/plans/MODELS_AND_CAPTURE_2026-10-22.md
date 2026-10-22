# A/B/shared candidates and new capture boundary

## Folder organization

| Directory | Responsibility |
|---|---|
|`models/`|Candidate estimators and standalone empirical comparators. No scheduler.|
|`runtime/`|Opt-in future measurement journal and real cursor wrappers. No replay generator.|
|`evaluation/`|Explicit unsupported IDs, common coverage and equal-episode error reporting.|
|`preparation/`|Raw bindings, source inventory and training registration boundaries.|
|`audits/`|Detached real-evidence validation commands.|
|`protocols/`|Immutable input/code hashes and operational rationale per job.|
|`docs/plans/`, `docs/reviews/`|New plans and evidence reviews. Earlier documents stay at registered paths.|

Results remain in repository `results/`, never mixed with source or implicitly
loaded as accepted models. Historical file paths/hashes are preserved; no moving
old protocols, receipts, queue package or frozen physical code for cosmetic reasons.

## Step 1 implementation

`models/latency.py` implements separate A/B and shared conditional estimators,
using the same declared predictor contract and eligible training corpus. A is
observed client pending, B is not pending; this is not causal treatment. Compact
log-Ridge and positive-leaf tree families are supported. Both train preprocessing
only on their own training rows. Query identity is categorical; absent/unseen
features and unknown keys never receive imputed values or substitute predictions.

Three separate empirical competitors: SQL median, SQL/layout median and
SQL/layout/state median. No fallback hierarchy. Missing learned predictions remain
unsupported even when a standalone median can predict. Numeric training-box and
observed SQL/layout/state support are conservative registered choices; they may
substantially reduce coverage and are not statistical confidence guarantees.

Equal per-estimator specifications are not equal total parameter counts: separate
A/B fits two estimators, shared fits one. Report this distinction and actual support.
A new comparison must preregister its aggregate compute/hyperparameter budget.
The constructor audit registers Ridge alpha1 inherited from the earlier compact
baseline, tolerance0.0001/maxiterations1000 as explicit numerical settings, depth3
inherited from that baseline, minimumleaf1 and fixed seed20261015 for reproducible
construction. These are not tuned, fitted, recommended production settings or
acceptance thresholds. Tree uses positive training-label leaf means; its squared
error objective differs from the old absolute-error tree and must not inherit old
scores. No fits occur in this unit. Fair future comparison must freeze these choices
or a declared training-only selection budget before new outcomes.

`evaluation/paired.py` retains every actual evaluation ID, reports each method's
unsupported IDs/reasons and common-support equal-episode MAE. Empty support gives
null scores, never zero error. Common-support accuracy cannot stand in for all-row
accuracy or physical decision benefit. Whole-source-family splits remain mandatory.

Fitting requires a new independently verified authorization binding actual training
rows/evidence, episode IDs and estimator specification. No existing registry grants
that authorization; this module has no automatic training CLI or legacy artifact
loader. The authorization interface is not a security boundary or a substitute for
independent raw/source/freeze audit. Model fitting/inference remain unvalidated on
new sources until such a job exists.

## Step 2 implementation

`runtime/publication.py` is an opt-in new collector primitive. All client maintenance
and queue transitions and feature snapshots share a lock and version counter.
Pending means this client's request lifetime, never inferred Spark activity.
Maintenance cursor wrapper tracks actual return/failure without retrying. Features
must carry real capture clocks and source context; state flags are derived from the
locked store, not accepted as caller inputs or reconstructed from later timestamps.

A capture is persisted with fsync, followed by an actual timestamp observed after
fsync returned. A second persisted publication record and its observed return stamp
are retained in the actual query-completion evidence. These are conservative bounds,
not the exact storage-commit instant. Process PID/boot identity is recorded. Wall
clock calibration across processes/hosts is not established by these stamps.

Actual query wrapper verifies unchanged client state, registered freshness and
cutoff after durable intent, then records actual execute/fetch service duration.
Refused starts remain `query_not_submitted`; failures propagate with evidence.
No synthetic call, copied historical timestamp, clipped result, invented overlap
or dropped failure makes a receipt accepted. SQL calls occur outside the state lock;
state can change after the snapshot. Record that uncertainty rather than claiming
atomic engine exposure. Journal/fsync/state locking adds overhead that must be
measured in future physical evaluation, not subtracted away or called removable.

Each new receipt starts runtime_adapter_accepted false. Independent reconstruction
of actual capture/state/call outcomes and source/table/snapshot identity must precede
training acceptance. Freshness age, cutoffs and source context must be registered
for a real new collection; no values are silently supplied by this library.

The new primitive does not patch the old frozen collector or currently running
experiments. Physical adoption/validation is pending a fresh registered collection,
source identity and resource reservation. Historical missing publication times and
one inconsistent state remain unresolved historical evidence, not repaired data.

## Actual validation registered for this unit

Detached worker3 read-only job parses/imports hash-bound new code, constructs both
estimator types without fit/inference, decodes all actual9923 feature rows, rejects
all historical records as new live publication, retains known mismatch, exercises
the fit entry rejection with the actual no-authorization inventory, and verifies
all-unsupported admission coverage has null scores. This uses actual records; no
artificial rows, labels, model cards, SQL or simulated cursor. It cannot validate
fitted predictions or new live concurrency/durability/cutoff behavior. Those remain
explicit pending gates rather than falsely reported successful tests.
