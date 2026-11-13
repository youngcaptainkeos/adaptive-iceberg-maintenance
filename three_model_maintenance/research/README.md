# Metric-focused research tools

Start with [the research programme](../../docs/research_program_2026-11-13/README.md) and [implementation/handover](../../docs/research_program_2026-11-13/05_implementation_and_handover.md).

This package implements bounded plan generation, conservative source-overlap grouping, strict supplementary full-cohort response accounting and descriptive matched comparisons. It does not launch physical work, fit a model or certify a scheduler. `ownership.py` is an unintegrated reference kernel whose original SQL inventory remains unavailable locally.

Implemented CLI subcommands:

```text
python3 -B -m three_model_maintenance.research validate-program --program FILE --output NEW_FILE
python3 -B -m three_model_maintenance.research plan --program FILE --design NAME --blocks N --output NEW_FILE
python3 -B -m three_model_maintenance.research budget --program FILE --design NAME --blocks N --episode-minutes MEASURED --setup-minutes MEASURED --output NEW_FILE
python3 -B -m three_model_maintenance.research overlap-families --windows FILE --output NEW_FILE
python3 -B -m three_model_maintenance.research account --episode DIRECTORY --pins FILE --output NEW_FILE
python3 -B -m three_model_maintenance.research compare --manifest FILE --reports FILE --output NEW_FILE
```

Run genuine checks through the project's detached failure wrapper with a unique label/receipt. Do not rerun saved outputs. Outputs are created exclusively, input evidence is hash-bound, and missing resource metrics remain missing. Tests on historical evidence are explicitly supplementary; the original physical audit and campaign outcome remain unchanged.

The 34 experiment cards cover distinct hypotheses. They are not a request to execute every combination. First establish useful action value; then keep only components that improve measured outcomes.
