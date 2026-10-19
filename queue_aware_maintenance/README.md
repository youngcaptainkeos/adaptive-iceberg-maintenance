# Queue-aware Iceberg maintenance feasibility

New isolated implementation for the19–20October2026study. Prior scripts, raw failures, fits and archives remain intact.

Goal: a runnable external controller that evaluates start/wait/noaction using actual backlog, real historical service/rewrite evidence and causal demand forecasts, followed by a substantial real Spark/Iceberg comparison. No publication-level novelty or improvement is assumed. Counterfactual simulator predictions are explicitly estimates, never physical labels.

Source files live here, including provenance-bound frozen evidence primitives in instrumentation/. Server jobs launch via the existing failure-alert wrapper under nohup. Physical cohorts must retain all offered real trace arrivals and measure waiting plus execution until drain, with explicit administrative cutoff/censoring if incomplete; no successful full-drain claim from a partial run.

See STUDY_PLAN.md and progress.json/receipts under results/queue_aware_maintenance_20261019 on worker3. Final deliverable requires controller source, reproducible protocols, actual server tests, complete physical cohort or preserved explicit failure and feasibility report, causal-source audit, raw evidence and SHA verification on both machines. A negative result is reported honestly; it cannot be relabelled as an effective controller proof.
