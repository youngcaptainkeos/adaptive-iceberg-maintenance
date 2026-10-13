#!/usr/bin/env bash
# The legacy pilot cannot satisfy the physical evidence contract.
set -euo pipefail
printf '%s\n' 'BLOCKED: legacy pilot is retired pending event logging and validated configuration.' >&2
printf '%s\n' 'Use scripts/phase6-live-evaluation/preflight_experiment.py for read-only checks.' >&2
exit 2
