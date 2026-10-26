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
