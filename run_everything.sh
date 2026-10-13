#!/usr/bin/env bash
# No automatic Spark startup, table reset, model promotion or benchmark execution.
set -euo pipefail
printf '%s\n' 'BLOCKED: master pipeline is retired pending the physical measurement gate.' >&2
printf '%s\n' 'Use scripts/phase6-live-evaluation/preflight_experiment.py for read-only checks.' >&2
exit 2
