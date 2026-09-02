# Phase 3A: Scheduler Verification & Telemetry Audit

### Q1: Did Beeline `SET spark.scheduler.pool` set pool properties for query jobs?
**Yes.** Event-log inspection of job properties verifies that Beeline session SQL `SET spark.scheduler.pool=foreground` assigned foreground queries to the `foreground` pool, and `SET spark.scheduler.pool=background` assigned compaction jobs to the `background` pool.

### Q2: Did query tasks and compaction tasks execute concurrently on separate pools under FAIR mode?
**Yes.** Task telemetry in `results/task_telemetry.csv` demonstrates active task slot sharing between foreground query tasks (minShare=12, weight=3) and background compaction tasks (minShare=4, weight=1), preventing background starvation while guaranteeing CPU allocation for foreground queries.

### Q3: Did FAIR mode change total query runtime and compaction runtime compared to FIFO?
**Yes.** Under FIFO mode, concurrent queries queued behind or yielded completely to compaction tasks, resulting in high latency spikes (QIR up to 2.5-3.0x). Under FAIR mode, minimum-share allocation reduced query interference to near 1.0x while extending compaction duration slightly.
