# Evidence-storage bottleneck and validated publication path

## What completed

The eight-arm recorded-gap audits passed and retained every original result. Extended intervals located290–388seconds per run between the archive's first recorded REST request and checkpoint capture, while HTTP request spans themselves covered only31–33seconds. Observation-capture→request-capture covered180–254seconds, request-capture→actual-execute104–133seconds, and completion-capture→ledger-completion114–162seconds. Categories overlap and include bookkeeping/persistence; they are not exclusive causal components or exact fsync timers. Approximately112–158seconds remained untagged. See `results/queue_gap_spans_phases_20261022/analysis/report.md`, resultSHA `8bc6663e8b4e50670588d1d4c2d809d90ee1a57d99c0cf7100ae4f3e56e5fd72`.

The storage diagnostic was not launched while Main's physical collection was active. After that process naturally completed, actual source-byte validation ran at11:21:18–11:21:24UTC (16:51IST), wrapper1284677, without SQL or fitting. It copied the first32 real submission triples from the hash-bound already-consumed development ledger, preserving all96 original records. It timed the same three separate write/flush/fsync steps per triple on two devices, with reversed location order for the second16pairs. No synthetic workload, new query observation or training label was created. Replay files are explicitly named `historical_source_bytes.replay_only`.

| Actual location | Filesystem/device | Median three-record write | Mean three-record write |
|---|---|---:|---:|
| Evidence directory `/mnt/nfs-storage` | localext4 `/dev/sdb` |127.156ms|129.825ms|
| System directory `/var/tmp` | localext4 `/dev/sdc3` |6.855ms|7.713ms|

The ratio of these medians is about18.55. This is a storage-operation comparison, **not an18.55×SQL, queue, or controller speedup**. Bytes were pre-encoded, excluding live feature construction, JSON encoding, SQL, archive traversal and workload contention. One counterbalanced session does not establish independent reproducibility. Both copied files matched the expected original bytes; original source hash remained unchanged.

Despite its name, `/mnt/nfs-storage` is not a network filesystem on this worker. `/home/ccbd` is also on the measured system device and had approximately22.13GBfree at inspection. Future capacity must be rechecked; this is not a permanent free-space guarantee or an automatic retention policy.

## What was implemented and verified

`observability/evidence_workspace.py` provides an opt-in persistent working-evidence directory and terminal archive publication. It requires a fresh explicit directory/device and byte budget, rejects reused paths, checks terminal status/SHA, stages a copy, verifies every file's bytes/hash before and after, fsyncs copied files/directories, and publishes the final archive directory while retaining the source. Failed/partial destinations are preserved. Caller-established producer termination and single ownership remain preconditions; no host-failure or concurrent-writer guarantee is claimed.

`audits/validate_evidence_workspace.py` exercised that path using the real completed storage-diagnostic directory: canonical source→fresh `/home/ccbd/capstone_evidence/workspace_validation_20261022/terminal_diagnostic_copy`→fresh canonical archive. Both actual files/127,247bytes and their terminal receipt survived unchanged; originals remain. The explicit byte budget was twice the actual source footprint,254,494bytes, an operational reservation rather than a performance threshold. No live collector, default logger, raw historical result or scientific gate was modified.

Validation ran11:25:32UTC (16:55IST), wrapper1286058, implementation `c55ff26`, status `passed_real_artifact_workspace_and_archive_roundtrip`. ResultSHA `b72df2b8469b0cb79af099eb3f67cc90f8e9a61108c6aab7af6bc9dcacd1d3dc`, file-manifestSHA `1662db5ff531ed8114503348155e152182b1db86aa50210947a0f3f12e10f44b`. This validates the storage/publication helper, not actual-SQL freshness or scheduler performance.

## Evidence and next physical gate

- Storage source/protocol: `analysis/probe_evidence_storage.py`, `protocols/real_byte_storage_probe_20261022.json`; result `results/queue_evidence_storage_20261022/result.json`, SHA `429ad52c6017bacabe861c247b18f2648814e66641cb7eecb64f2f9a7877127e`; actual launch/log under `results/queue_evidence_storage_20261022_launch/`.
- Workspace source/protocol: `observability/evidence_workspace.py`, `audits/validate_evidence_workspace.py`, `protocols/evidence_workspace_validation_20261022.json`; output `results/queue_evidence_workspace_validation_20261022/`, launch/log under corresponding `_launch/` directory.
- All actual validation used detached worker3 failure-alert wrappers with unique paths. No failure notifications were dummy-tested, no failures or physical retries occurred in these two diagnostics. Result, logs and canonical replay/publication artifacts were mirrored and checked with itemized checksum dry runs.

Next: register a matched measurement-only comparison of the two working-evidence locations with actual SQL on fresh matching tables, unchanged foreground workload, telemetry windows/freshness, per-record durability, snapshots/results/tasks and complete request accounting. Keep the storage destination as the declared intervention; do not simultaneously change sampling, query mix or cache behavior. Establish a persistent-local byte budget/retention and terminal publication contract before launch, use a frozen runtime and coordinate physical admission with Main. Preserve all attempts and negatives. Only after actual-SQL correctness and repeatability pass should the new path become the boundary for a larger queue-policy campaign. Existing eight-arm measurements remain unchanged; no policy benefit, causal interference, calibration or novelty is established by these storage tests.
