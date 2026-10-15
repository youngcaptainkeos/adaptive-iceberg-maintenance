# Detached collection handover — 15 October 2026

Launched08:33IST (03:03:16UTC) onworker3 undernohup. CoordinatorPID1804667,
parentPID1 verified afterSSHsessionended. This server-only process and its serial
children survive laptopclosure/SSHdisconnect. The old Codex overnightautomation
remainspaused; it is not required for this job.

## Scope and guardrails

- Prepare and independently audit newreal source-day3/4/5arrivalwindows, checking
  they do not overlap prior sourcefamilies. Preserve everyactualarrival/spacing.
- Save actualmapping/audit hashes and all18freshphysicalprotocols **before SQL**.
- Run18episodes:3sourcefamilies ×16/32initialfilelayouts ×baseline/now/later.
  Same frozenmeasurementpipeline, rotatedarmorder/alternatinglayoutorder, strict
  source/task/logical/freshness/gap/history/debt gates unchanged.
- Stop on the first failed gate; keep failure/unattempted counts and all tables.
  Export/independentlycheck only successful candidate evidence when rewrite labels
  exist. No fake missing rows, physical retry, service restart, cancellation or deletion.
- Do not automatically fit/tune models or inspect future test errors to choose a
  model. Source3/4development,5prospectivefuturetest. Oldnegativefit unchanged.
- Finishwith progress.json, result.json and handover.md, including failure details.

This is a reliability/coverage pilot with oneepisode per cell, not calibrated or
publication-ready model evidence.3families/oneengine/SF1/customSQL limitations stay.

## Server locations

Canonicalrepo: `/mnt/nfs-storage/shashank_prafullathta/implementation`.
Frozenruntime: `/tmp/capstone_consistent_runtime_20261015`, revision
`ea2b6e69eeeeb34d6a41c8212f544334dba046d0`.

- Launcherlog: `results/consistent_collection_20261015_launch.log`.
- Progress/terminalhandover: `results/consistent_collection_20261015/`.
- Realaudit-source receipts/logs: mapping_* logs inthatdirectory and
  `results/snowset_consistent_day3_20261015` throughday5.
- Pre-SQLregistration: `execution_manifest.json` and `protocols/` underjobdirectory.
- Physicalprogress/logs: `cohort/progress.json`, `cohort_launch.log`, per-armlogs.
- Rawtables/measurements: `arms/sf1_consistent_20261015_01` through_18.
- Successfulcandidateexport: `candidates/`; independentreceipt
  `candidate_independent_verification.json`, if raw/data gatespermit.

Estimated totalruntime5–6hours, roughly13:30–14:30IST if healthy. Sourcepreparation
and raw gates can fail or extend runtime; this is not a completion guarantee.
No newepisode after16:00IST, no newSQL/maintenance after16:30IST. In-flight finishes
naturally. Stopping dependent work does not kill services or active SQL.

## Check after reopening the laptop

```bash
ssh ccbd@10.10.3.232 'cat /mnt/nfs-storage/shashank_prafullathta/implementation/results/consistent_collection_20261015/result.json 2>/dev/null || head -n 12 /mnt/nfs-storage/shashank_prafullathta/implementation/results/consistent_collection_20261015/progress.json'
```

Read the serverhandover before resuming. Mirror raw/results/hash manifests once
connected; newresults cannot be mirrored onto a closed laptop. Re-audit failures
before any new dependent collection/fit. Do not reuse occupied tableidentities.

## Setup health check completed before laptop closure

Allthree source mapping/audits passed, intervals disjoint from earlierfamilies,
and18actualSHA-bound episodeconfigs saved beforephysicalwork. Coordinator advanced
tophysical_collection, strictcohort/firstepisode started without reportedfailure at
setupcheck. Executionmanifest mirroredlocally, SHA
`0ed30bb68f8a8ccec8849828fa2e256fb7b0e33c3ed57043ce0dc18910064c10`.
This validates launch/setup, not completedphysicalepisodes or statisticalmodels.
Laptopmayclose now; no appheartbeat needed. Serverjob willsaveactualfinished/failure
status andpreserve allpartialevidence; reconnect toreview/mirror before furtherwork.
