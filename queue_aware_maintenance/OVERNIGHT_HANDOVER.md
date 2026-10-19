# Queue-aware feasibility handover

Updated2026-10-19 13:35UTC. Goal incomplete.

## Active real physical study
- Recovery root results/queue_aware_maintenance_20261019/cohort_container_repair. Wrapper203577/coordinator203578/first arm wrapper203582 confirmed live13:34UTC. First arm passed initial zero-difference gate and is gathering305s warmup telemetry. Expected replay starts about13:38:30UTC.
- Frozen runtime /tmp/capstone_queue_aware_20261019_container_repair revisionaf274dba5fc59b0c2acc3892d8c46d34d144928b. Do not edit it. New canonical analysis code may be added separately.
- Log results/queue_aware_container_repair_20261019_launch.log; per-arm logs and progress.json in recoveryroot. Protocol physical_study_container_repair_20261019.json SHA57a00d643553ad37f1493f218dcc849d4a91e8bb5b3310fa5e4553be30499b5b.
- Eight arms, two actual source windows3067/3211queries,1200s arrivals plus full drain. Estimated8.4h plusaudit (~22UTC/03:30IST). No new episode after22:15UTC, no new SQL after23:45UTC, deadline20Oct00:30UTC. Preserve natural in-flight operations.

## Preserved failure and repair
Original cohort 0passed/1failed/7unattempted, no workload queries. Table queueaware_20261019_01 occupied and retained. Frozen oldruntime8f8c3ee retained. Actual read-only SQL proved list-of-tuples countzero; repaired exactshape/value predicate, no weakened equality. Receipt multiset_container_repair/result.json SHA73642eef95c9bcce01dd2906e5c30099cd730d2c0c100c7911a420df2a8692da. New runtime preflight passed SHAe937d74818a2149c0ebfa13a1cd0d621f4e9c97c2956db32095c76c771b84126.

## Remaining work
Postcohort compare_study.py now implemented: requires8/8, reruns raw task/result/telemetry/FIFO/responsearea audit; reconstructs each actual decision backlog and lastoffered from past raw transitions, replays saved past-only forecast/model without refit, verifies matched inputs/layout and reports perwindow contrasts. Current analysis source preflight pending. Full comparison protocol must bind actual terminal cohort SHA after completion; do not invent hash or run on partial survivors. Need independent full evaluation, feasible/negative interpretation, runnable README commands and all completed raw mirrors/hashes local+remote. No publication novelty/performance/calibration claim. Initial model choices immediate on both windows. Keep full goal active.

Scheduler queue-aware-iceberg-feasibility-until-6-am ACTIVE every10min, updated recovery PIDs and rules. Original old automation remains paused. Original local drive restored808files; unrelated archive/dirt preserved. All tests worker3 detached wrapper with unique label/log/failure receipt and ntfy. Commit/push/ff/SHA afterunits; preserve frozen running code.


## Verified execution update13:39UTC
First arm completed actual maintenance and14tracequeries, with controller actual decision at elapsed0.089164217s choosing immediate. Initial table equality and305s telemetrywarmup passed. This is progress, not completed physical PoC. Source finalpreflight wrapper205380 passed atcanonical74897f1; receipt analysis_final_preflight/result.json SHAd8aef2de4d161f5b2def2506152d168bb368a7355c405c1324357f5ba6e85ec7. Final comparator SHA865f2fc246bdc15e2f2063129b0054e6f0977de4b6b8098913f1296cf31ea140; terminal-registrationutility f855e8bdcfa709741b1ba65c77a2f2fdd75eb5498c0a77540e2232356d8704b4. README has actual worker3-only registration/comparison commands; do not execute onpartialcohort. All completed evidence mirrored withchecksum-onlytransportcomparison zero differences, excluding live recovery. No competing physical run.
