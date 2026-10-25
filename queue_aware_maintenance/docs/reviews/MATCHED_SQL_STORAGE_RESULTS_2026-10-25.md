# Matched SQL evidence-storage comparison: completed result

All four registered arms passed, with3,094 actual queries per arm (12,376 total), zero failed and zero unattempted arms. Independent complete raw reconstruction and original decision replay also passed for every archived episode. Completion was24October2026 18:52:40UTC,25October00:22:40IST. Actual checks on25October01:26UTC found no matching active Main/queue Python jobs. No process/service was stopped, no dataset/table deleted and no additional run launched by this review.

## What the comparison says

The same no-maintenance workload ran on fresh matched16-file SF1 tables, changing only its durable evidence-storage device. Order was evidence/system/system/evidence. Both are local disks. All original per-record fsync, telemetry publication/coverage/freshness, source/SQL/snapshot/result/task/FIFO and whole-cohort accounting gates were retained. No compaction or fitted scheduler was compared.

| Order | Evidence location | Mean arrival-to-result response(s) | Time until final query result(s) | Foreground SQL calls(s) | Time outside foreground SQL calls(s) |
|---|---|---:|---:|---:|---:|
|1|Evidence disk|1436.028|3993.059|2753.344|1239.715|
|2|System disk|834.301|2879.328|2663.931|215.397|
|3|System disk|827.970|2867.744|2658.822|208.922|
|4|Evidence disk|1201.646|3567.895|2745.454|822.441|

The two preregistered paired contrasts show41.90% and31.10% lower total response on the system evidence device. Because every arm has the same query count, the corresponding mean response reductions are identical. The final query result arrived1113.73seconds and700.15seconds sooner. Of those elapsed reductions,1024.32seconds and613.52seconds lie outside foreground SQL calls; foreground call totals fell by roughly89 and87seconds. This is principally an observer/client-overhead finding, not41.9% faster SQL execution.

Arrival-to-result response includes waiting behind earlier requests. Reducing overhead between consecutive calls allows the serial client to serve the queue sooner, reducing many requests' waiting together. It does not change their original arrival schedule or remove their evidence. Actual SQL calls, archive overhead, freshness waiting and client scheduling are retained in the measured system; outside-call time is an accounting category rather than an exact per-component causal timer.

Both system-disk observations are close in this session, whereas the two evidence-disk observations retain appreciable drift. Forward/reverse placement balances early/late position but cannot eliminate cache/host/time drift, establish statistical power or supply an independent source family. Do not infer significance, universal speedup or stability bounds from two runs per device. The experiment is positive engineering evidence for using the faster working-evidence location in a newly registered study; it does not automatically promote a model or scheduling policy.

## Implication for the research

The earlier small maintenance-timing differences must remain interpreted cautiously: the previous observer path had material overhead and drift. Those historical outcomes remain intact; no overhead is subtracted and no unfavorable run is discarded. This study supports a more credible measurement setup but does not establish that waiting/forecasting/queue-aware compaction improves performance. All four arms intentionally performed zero maintenance.

Next gate: register a maintenance-enabled timing comparison using the system evidence device and the same verified terminal archive publication, first retaining actual maintenance metadata/freshness/correctness/task checks. Preserve the chosen source/SQL/scale/trace and all failed/unattempted scope. Separate that measurement/timing gate from a subsequent independent-source/whole-episode policy evaluation against declared baselines. Suitable quiet-period/capacity and ongoing-ingestion coverage remain missing; three-model layout/state confounding and rewrite/demand calibration are not repaired by this result. No new physical work is authorized by this progress review alone.

## Implementation and evidence

- Coordinator revision `f4a35a299fcc3d84f6fd45576ee5441760ca752a`, frozen `/tmp/capstone_queue_storage_20261024`; unchanged physical revision `790f4f89d1d8cbe821903af79392134bfb1c6bbb`.
- Registration `queue_aware_maintenance/protocols/matched_sql_storage_20261024.json`, SHA256 `9d49a6e05bfed4952982bb29bb8ddc3883db773923f6216c6ab2f9d326d63546`.
- Parent wrapper2017932/coordinator2017935; first physical wrapper2018079/client2018081. Final independent analysis wrapper2090853, return0. No stage was retried.
- Canonical root `results/queue_storage_sql_20261024/`; each immutable full package is in `episodes/`. Original working copies are retained on their respective devices.
- Parent terminal result SHA256 `4e2ac1fc2f916bbf81d5ad073d35f3c05d0c1cd849892693ee4df576df532fdd`.
- Complete analysis `analysis/result.json`, SHA256 `9cf8ee70b1da33bcfbe4ce0e019676f80e3036b80e584a90b8cecd19ea50e276`; human report `analysis/report.md`; each independent raw reconstruction and its own failure-wrapper log are retained alongside it.
- Episode01 result `743a5935a7205dc3b874c0a4a77b5179349f7f90238aa291c43b487ec9d16a30`, events `452b03314f1bd763b48bea18276149b2d90e43089ab6766796c9047461eefab8`.
- Episode02 result `37cac388303d1f5bef681608ebb8ff5114e65dd77473bc32955c6083fa989864`, events `5b0a2d808da86bf97574db4e935f7411b1f5adc9ec0a118af978d45e23e82d74`.
- Episode03 result `18b6eadfcbe59020813d45e0db1dc2c96fd621afb33a6acfba0b3fceae722a7d`, events `e0bfbe02a6da16cb9d5e13446e4a340a0d8c5117fdb07a0183e628adfc55fc1b`.
- Episode04 result `4e29d727455c659472e7782f3c7d344487acf38f2b8b43c7b9040878260d3e4a`, events `1d93be4579516a4c284c49a24b4956b64a6b98b8f9520aa257a09beedda524d7`.
- Terminal ntfy deliveredHTTP200, id `bKWCUlXkgNgD`; all per-arm completion receipts retained. Initial failed VPN connections remain transport incidents before launch, not hidden scientific failures.
- Autonomous per-arm/terminal methodology commits `c611f64`, `710dbe1`, `a2cdb1a`, `9fbf068`, `fcfccbf` fetched to laptop and published GitHub during this check. Later synchronization/mirror receipts follow below; no complete backup of the separate older eight-arm cohort is implied.

For functions and the pipeline in plain language, see `docs/plans/MATCHED_SQL_STORAGE_2026-10-24.md`: the coordinator starts the same old physical runner, waits for its independent gates, verifies terminal copies, then rebuilds all four raw episodes and reports both contrasts. No observer or physical source patch was made during this check.

## Synchronization and backup status at this check

Terminal parent/analysis files copied locally and their SHA256 match worker3 exactly; launch-directory rsync and itemized checksum dry run returned0 with no differences. Full canonical raw archive copy is still running (transport215988/rsync215990, exec session1935); it includes all four `episodes/` and analysis/receipts, excluding only duplicate `working_evidence/` originals retained remotely. Completion and itemized checksum result have not yet been observed: do not claim a full raw mirror or start a duplicate transfer. Separate earlier eight-arm raw backup is not covered by this copy. See `results/queue_storage_sql_20261024_backup_status/status_20261025_0129.json`.
