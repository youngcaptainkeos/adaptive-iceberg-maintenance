# SF10 exact typed audit repair — 26 October 2026

The SF10 scratch recovery03 actually completed all eight exact full-row ingestion
checks,12query executions/online independent-reference checks, and a useful
lineitem rewrite64→4files. Source has59,986,052lineitem rows. Its final v1 audit
failed25Oct04:25:40UTC09:55IST, with ntfyHTTP200. Original terminal remains
failed (`684e22d3e44662b0a3c2bef7a34ecaa782063ee1a504113a6ff0d196038fdf99`).
Both original and added persistent Spark services remain intact.

A detached saved-evidence diagnostic25Oct, wrapper2272215, found6result-string
mismatches and0timing mismatches across12observations. q1/q3/q5 both phases
contain Decimal values serialized by EventLog's JSON default=str. Live canonical
normalizes Decimal; reloaded JSON contains strings and v1 canonical preserves
strings, e.g377518399.00 vs377518399 and381015038.10 vs381015038.1. These
representations explain the failure; diagnosis alone does not accept the corpus.
Diagnostic: results/three_model_sf10_failure_diagnostic_20261025_01/result.json.

New audits/sf10_saved_capability.py is the versioned successor for this saved
SF10 audit. Historical scale_query.py and all frozen physical protocols remain
unchanged. Future SF10 pipelines must use the explicitly typed audit contract;
the untyped v1 audit is retained for historical reproducibility, not a fallback.
Projection schemas are registered against each exact SQL string: counts/keys are
integer, grouping text remains literal, DECIMAL expressions are exact decimal.
Logged decimals require finite numeric strings/≤28digits (original canonical's
precision); no floats, null filling, string inference or tolerance. Numeric-looking
text is never normalized. No hardcoded predictions or fabricated observations.

Protocol three_model_maintenance/protocols/sf10_saved_typed_audit_20261026.json
pins the entire immutable source package and auditor dependencies. It rechecks
request/completion uniqueness, all8loaded counts/exact EXCEPT ALL gates, all12
phase/query observations, raw plans and feature receipts, registered snapshot/SQL
binding, exact results/timings/availability and useful rewrite/full-row preservation.
Original v1 failure stays retained; successful repaired audit will have a new
separate receipt at results/three_model_sf10_typed_audit_20261026_01.

Run only saved evidence on worker3 under nohup/run_with_failure_alert.py, no SQL,
new datasets or physical rerun. Prelaunch implementation is not a passing audit.
No learned model, matched A/B demand corpus, calibration, SF100 readiness or
scheduler-benefit acceptance follows even if this capability audit passes.

Actual launch/results and synchronization to be appended after server execution.

## Actual repaired audit result — 26Oct21:10IST

Committed revision188091cab5446b984f029f1bd9261aefd0b8e611 pushed and worker3
fast-forwarded; source/protocol SHA matched before launch. Detached failure-alert
wrapper2740012 started15:40:32UTC21:10:32IST, estimated check60seconds. Actual
saved-evidence auditor completed with status
`passed_saved_sf10_typed_capability_audit_only` on its first execution.
Log: results/three_model_sf10_typed_audit_20261026_01_launch/audit.log.
Protocol SHA4e0b97983a2715bde0f97231f5d1862607571137e514af13d3e8ae17d6d9354b;
auditor SHA3b31acd68d66936b498e5aca9e0da31fad4c92efcc914b52abb71ae9cd5e62a9.
Result SHA9db75ebcc8fa23ad84e7831cfb9075913c2a4adae2b13efdf9614ac92c3c99ee.

All8raw exact ingestion comparisons,12typed results and exact timing checks,
all raw pre-execution plan/receipt/snapshot/SQL bindings and useful rewrite/full-row
preservation passed. Real plan operator counts range5–30 with up to5scans/4joins;
these describe structure, not learned runtime accuracy. All original input hashes
were equal before/after the audit. Original terminal remains failed and retains
SHA684e22d3e44662b0a3c2bef7a34ecaa782063ee1a504113a6ff0d196038fdf99.
No SQL, new source generation, physical rerun, table change or model fit occurred.
The new receipt supersedes only the v1 auditor's serialization interpretation;
it does not rewrite the historical failure or claim a successful original parent.

New output/launch and the original small immutable evidence package are mirrored
to the client. Checksum rsync for typed audit and original03 returned exit0 with
no differences (historical local progress snapshot excluded); result SHA matches.
Full generated raw files, Iceberg data and source DuckDB database remain on worker3,
not claimed fully mirrored. Services remain persistent.

Next gate: prospectively register SF10 trace-driven collection with this typed
result contract, real pre-execution plans and matched fragmented pending/nonpending
support; preserve offered history and whole-source splits. This12query capability
pilot is not sufficient for training/calibration/generalization or SF100 admission.
No immediate physical collection or model training is launched by this repair.
