# Queue timing: repeatability and clock accounting

The registered read-only diagnostic passed on worker3 on 22 October 2026. It hashes the complete original ledgers and reconstructs actual foreground SQL calls against the previously audited request results. This is post-hoc development analysis, not a new policy evaluation or causal overhead experiment.

## Observed results

| Intervention | Repeat | Foreground SQL calls (s) | Outside those calls (s) | Outside-call share of elapsed time |
|---|---:|---:|---:|---:|
| Immediate | 0 | 2714.68 | 1106.61 | 28.96% |
| Wait60s | 0 | 2718.38 | 1089.75 | 28.62% |
| Wait600s | 0 | 2723.38 | 868.19 | 24.17% |
| No action | 0 | 2727.50 | 861.32 | 24.00% |
| No action | 1 | 2742.77 | 821.43 | 23.05% |
| Wait600s | 1 | 2725.60 | 827.08 | 23.28% |
| Wait60s | 1 | 2706.05 | 813.73 | 23.12% |
| Immediate | 1 | 2704.20 | 812.72 | 23.11% |

For immediate compaction, the second repeat's time until the last result fell by304.36seconds. Actual foreground SQL call total fell by10.48seconds, while outside-call time fell by293.89seconds. Thus approximately96.6% of that elapsed-time difference lies outside foreground calls. This is an exact accounting location, not proof of a cause or removable overhead. Metadata calls, telemetry freshness waiting, archival work, client preparation and OS scheduling may occupy these gaps; a competing maintenance call can overlap them too.

The first two runs had median outside-call gaps around204–206ms; subsequent runs around153–158ms. Request waiting makes up about99.93% of summed arrival-to-result response. That percentage uses accumulated request time, whereas the table uses elapsed walltime: they must not be conflated. Only1.311seconds per run precedes the next scheduled arrival across the reconstructed gap partition; almost all remaining gap time occurs after the next request is due. The source is therefore continuously backlogged in this serial-client benchmark after initial arrival, rather than yielding a long quiet server interval.

These observations weaken an interpretation of the original tiny60second-delay differences as demonstrated scheduling benefit. They do not invalidate measured results or justify subtracting unexplained gaps, changing an old result, dropping telemetry gates or treating SQL-call-only time as the original objective.

## Source inventory

The same SHA-bound selected-warehouse export contains2,760,971 arrivals in894 nonempty20minute source-clock bins. Their counts range1688–3370. The inventory preserves per-minute counts without manufacturing unlisted/empty intervals or selecting new experiment windows. It does not establish completeness of every boundary window, untouched source families, available host capacity or idleCPU. A warehouse originally selected for maximum training activity may be a poor source for evaluating genuine quiet-period decisions. Future source selection must be newly registered, use only permitted development/history information, and coordinate overlap exclusions with the three-model track.

## Next gate before another physical campaign

1. Read recorded REST request spans, telemetry-availability waits and archival checkpoints to measure their temporal overlap with outside-call gaps. Use interval unions to avoid double counting. Missing spans remain unexplained; overlap is not a causal removal estimate.
2. If a concrete measurement bottleneck is identified, prepare an isolated observer change and a real-evidence validation protocol. Preserve durable evidence, freshness/coverage, snapshot/result/task/FIFO and full-drain gates. Frozen experiments remain untouched.
3. Establish repeatability of that measurement boundary before declaring a small policy effect. Predeclare precision/repetition criteria from development variability; do not tune to obtain favorable repetitions.
4. Register prospective source/SQL-mix/scale coverage and independent blocks only after capacity and source-family exclusions are audited. Do not compress demand or infer original query mix. No large physical batch is launched by this review.

## Evidence

- Implementation revision `5d46ce744a526270c91874e9fec09c3c0b1fec78`; source `analysis/analyze_timing_repeatability.py`, SHA256 `16d50afe241bf51a216b1e99ee0d9281944437b2fadce8f7e0a1a5716dffb677`.
- Protocol `protocols/posthoc_queue_clock_inventory_20261022.json`, SHA256 `b27a42de95d59697b062bce151780ea5d8b846f86a486f968328f8fab16c248b`.
- Wrapper/client1177468/1177469,22October04:18:19–04:18:38UTC; log `results/queue_repeatability_clock_20261022/analysis.log`.
- Result `results/queue_repeatability_clock_20261022/analysis/result.json`, SHA256 `8d8ffdcddb288d266f37316d0348d25b0ba9491460b418777e82bd86f33e0e9f`.
- Source inventory SHA256 `a00c9429069b3559480839d8a8955da35d1b86314ab0fdb3a35cd378d3bb5d2c`.
- No SQL, fitting, physical rerun, changed historical result or new causal/calibration/novelty acceptance. Diagnostic evidence mirrored with an itemized checksum dry run.

The previous full raw timing-evidence transport was absent and the laptop held only1.7GB of the roughly2.5GB server directory. A separate detached transport was resumed as PID39793, with copy/checksum logs and terminal receipt under `results/queue_backup_resume_20261022/`. Until that receipt confirms no itemized differences, the complete raw mirror remains unverified; source originals are preserved on worker3.
