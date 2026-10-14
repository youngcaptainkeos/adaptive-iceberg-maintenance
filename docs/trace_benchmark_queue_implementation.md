# Trace-driven benchmark queue implementation

Status: server compilation and real source mapping audit passed; the first
physical diagnostic is running under nohup, with queue audit/results pending.

`prepare_trace_benchmark_mapping.py` verifies the audited cohort receipt and
source byte hashes, scans real arrivals, selects the first nonempty complete
training bin, and retains every identity/timestamp. Tied arrivals sort by numeric
source ID. Existing four custom SF1 query templates cycle by arrival ordinal;
this is an imposed controlled mix, not inference of missing Snowflake SQL.
`audit_trace_benchmark_mapping.py` independently reconstructs the chosen window,
source identities, exact spacing and declared mapping before replay registration.

`offered_queue_ledger.py` records actual offered, queued, dispatched, completed and
failed transitions with original source identity, scheduled/actual/durable times,
measurement UUID and session. It never generates service times or load curves.
`run_trace_queue_diagnostic.py` implements one FIFO physical query client with
independent arrival and boundary threads, real statement recorder, telemetry,
query result references and Spark task evidence. It retains unfinished queued
identities and permits active queries to finish naturally. It reports boundary
observer lateness separately from retrospective counts using actual transition
stamps. The source table is read-only and snapshot pinned. No maintenance, cache
clearing, ingestion, label generation or scheduling prediction occurs.

Before launch, register a real mapping-record hash, the verified source receipt,
actual four query-result ledgers, engine, complete telemetry warmup, explicit
operational cutoff and fixed no-dispatch-after-horizon rule. The runner refuses
missing evidence or a dirty/revision-mismatched experiment checkout. Audit binds
query SQL, actual client clocks, queue/session/FIFO conservation, exact offered
coverage, raw expected results, source state, windows and attributable engine
work. Failures remain failures; no reduction of offered demand to meet capacity.

This unit establishes intake accounting only. It cannot establish original SQL
workload reproduction, stable interference costs or a publishable scheduler.
Common-horizon action blocks, independent splits, scale/provenance and stronger
query mixes remain necessary. Cost-model candidate implementation is gated and
cannot consume these diagnostic exports as accepted training data.
