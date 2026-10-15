# Project workflow

- Send failure notifications for every future test/run to the user-authorized
  `https://ntfy.sh/shashank_capstone_alerts`. Launch standalone tests/jobs through
  `scripts/phase6-live-evaluation/run_with_failure_alert.py` under nohup on worker3
  with an explicit label, unique receipt path and actual command after `--`.
  The detached collection runner also alerts failed child stages/orchestration.
  Preserve original exit status, logs and failures even if notification delivery
  fails. No dummy run is needed to test alerts; use actual failed-run evidence.

These are the user's standing project requirements. Later explicit user instructions
and applicable higher-priority instructions take precedence.

- Target defensible forecast-aware Iceberg maintenance timing research. Be critical
  about correctness, novelty, independent evidence and publication limitations.
- After every major implementation, experiment, audit, model or pipeline job,
  append to `docs/methodology_working_doc.md`. Preserve existing text. Include
  purpose/rationale, protocol/code revision, data provenance, pipeline changes,
  raw artifact paths, checks, observed/negative results, failures, limitations and
  next gate. Supersede old claims explicitly; never rewrite history to fit results.
- Keep `docs/updated_methodology_working_doc.md` as an append-only summary/pointer.
  Read `docs/learned_cost_model_implementation_plan.md` for current model milestone
  and `docs/daytime_review_2026-10-14.md` for historical execution evidence.
- No dummy runs/data, fabricated labels, synthetic fallback demand, fixed policy
  predictions or weakened acceptance gates. Missing evidence remains missing.
  Named operational/experimental parameters require registration and rationale.
- Run validation, model fitting and physical experiments on worker3 using nohup
  or another detached process. Record log, PID and estimated check time. Inspect
  active work first; respect each registered cutoff, preserve running operations.
- Never shut down/restart/kill/cancel services/processes or delete tables/data.
  Preserve all failed attempts and unattempted counts; do not retry until a
  favorable result appears. Use fresh isolated experiment tables.
- After each repository unit, audit, commit only intended files, push GitHub,
  fast-forward worker3 and verify HEAD/intended file SHA256 agreement. Preserve
  unrelated dirty/untracked files and the unapproved local-only handover archive.
- Distinguish candidate data, exploratory fits and accepted calibrated models.
  Whole experiments/source-overlap families must govern splitting; no post-decision
  outcomes in predictors, no invented counterfactual cost or scalar/SLA objective.
