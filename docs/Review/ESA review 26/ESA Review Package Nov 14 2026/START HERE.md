# ESA Review Package — 14 November 2026

**Project:** Workload-Aware Scheduling for Data Processing Systems

This dated package refreshes the short ESA presentation and Phase 1 report using the latest Nov 14 SF10 execution and audit evidence. It preserves the original full deck, prior short deck and earlier report in their existing locations.

## Files

- `ESA Review Presentation Short.pptx` — original 25-slide short presentation, retained as delivered.
- `ESA Review Presentation Short - Architecture and Milestones.pptx` — separate 25-slide derivative with the editable end-to-end architecture diagram on slide 8 and gated research roadmap on slide 23.
- `ESA Review Presentation Short 2.pptx` — separate 25-slide screenshot-expanded derivative. Slides 15–18 pair additional captured results, audit, Spark UI and dashboard evidence with plain-language explanations. Earlier decks remain unchanged.
- `Diagrams/` — standalone PNG exports of both diagrams plus their scope and evidence notes.
- `ESA Phase 1 Report.docx` — updated report with the latest execution/audit progress addendum; earlier results and failed-campaign status remain intact.
- `ESA Phase 1 Report.pdf` — rendered reading copy of the updated report.
- `Presenter Guide.md` — slide-by-slide speaking points and important interpretation boundaries.
- `Teammate Slide by Slide Guide.docx` — detailed learning and rehearsal guide for all 25 slides, including slide screenshots, plain-language explanations, technical inputs and metrics, sample speaking notes, likely panel questions, and evidence boundaries.
- `Evidence/` — frozen Nov 13/14 result JSONs, the labelled Nov 14 results and audit screenshots, Spark UI capture, provenance manifests and preserved failures.
- `SHA256SUMS.txt` — checksums for package deliverables and frozen evidence.

## Evidence boundary

The Nov 13 passed checks are saved-history engineering regressions, not new query executions, model fits or physical timing experiments. The old SF10 campaign remains 0 passed / 1 failed / 1 unattempted. In two different checks, the number 308 refers to different units: disputed job links matched, and stage attempts without saved task lists. Do not combine these counts.
