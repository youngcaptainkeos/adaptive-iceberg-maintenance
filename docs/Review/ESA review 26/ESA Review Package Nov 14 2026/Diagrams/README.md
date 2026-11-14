# Project diagrams

These standalone PNGs are exported from editable PowerPoint shapes on slides 8 and 23 of `../ESA Review Presentation Short - Architecture and Milestones.pptx`. The original short deck remains unchanged.

- `Project Architecture.png` shows the complete workload-to-decision pipeline: Snowset arrival timing and TPC-H/SF10 data, FIFO request queue, Spark/Iceberg work, raw evidence capture, candidate A/B service-time estimates and C arrival forecasts, the proposed start/wait/no-maintenance controller, and whole-cohort outcomes. Solid boxes identify the testbed/evidence foundation; dashed boxes identify candidate or proposed components.
- `Research Milestones.png` shows six evidence-gated phases. Phase 1 is current and partial. The matched timing experiment, independent model data, calibration, queue-aware policy evaluation, robustness and publication-level claim remain future gates.

The diagrams summarize project design and saved evidence as reviewed on 14 November 2026. They do not establish a calibrated model, a scheduling benefit, or publication readiness. The direct-capture integration remains 5 passed / 1 failed / 0 unattempted because two dependency-stage records are missing, even though all six query outputs matched their expected results.
