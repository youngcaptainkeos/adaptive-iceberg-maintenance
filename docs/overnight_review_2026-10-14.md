# Overnight review — 2026-10-14

## In progress

Started 00:07 IST; deadline 07:00 IST. No shutdown or cancellation authorized.
Initial local/worker3 HEAD: a44f2a9edf2bcf3ae7fd77dc224863917e77cbf6.
SSH works; existing Spark Thrift app local-1791896695889 is available (3.3.4).
Preserved unrelated local changes and untracked archive/drafts/results.

Same-chat continuation `capstone-overnight-audited-implementation` created at
15-minute intervals, with explicit deadline and preservation rules.

## Evidence ledger

Implemented durable exclusive JSONL event logging, client statement timing/results/
failure records, raw Spark REST capture and independent counter-based telemetry.
Commit: 26959b5. Pushed and synced; three intended file SHA256 values matched.

Actual observer validation on worker3 recorded seven real host intervals and raw
environment/jobs/stages responses. Five-second window reported 4.277 seconds of
measured coverage and 0.723 seconds freshness, rather than pretending complete
coverage. See `observer_integrity_validation_2026-10-14.json`. Raw evidence remains
on worker3 at `results/measurement_integrity_20261014/observer_events.jsonl`.
This validates observer plumbing only, not workload performance, per-query I/O,
60/300-second model features or engine overlap. No dummy input or model training.

Read-only catalog queries recorded in `catalog_events.jsonl` found SF1 tables in
`local.tpch`, not `local.tpch_sf1`. Catalog commands produced no matched Spark jobs;
this does not establish that query SQL markers fail to correlate with scan jobs.

**Blocking discovery:** source metadata query against `local.tpch.lineitem.files`
failed because its snapshot manifest points to
`file:/home/shashank/Link to PDocuments/Capstone/implementation/warehouse/tpch/...`,
a laptop-only path absent on worker3. Source snapshot ID observed in history:
8128630582928284438. Failure is preserved in
`results/measurement_integrity_20261014/source_metadata_events.jsonl`.
Earlier successful SELECT version/history must not be treated as data readability.
Do not rewrite/reset this historical table to hide the failure. Next unit must
create its own uniquely named Iceberg table from verified SF1 source `.tbl` files,
record generator/source hashes and ingestion schema, and validate loaded cardinality.

Legacy launch paths remain blocked. No benchmark workload or rewrite has run yet.
Existing Spark/service/table state preserved; only our observation thread stopped.

### 00:24–00:31 IST: isolated source preparation

Implemented `prepare_correctness_table.py` and preregistered explicit SF1 preparation
configuration, committed/pushed/synced as 4d38c84. Three changed file hashes matched
before execution. Source parsing checks every line has the reviewed 16 pipe-separated
fields plus trailing separator; typed CSV FAILFAST checks all columns for nulls with
column pruning disabled. Destination-exists checks forbid overwrite, and a host-local
advisory lock prevents duplicate preparation instances.

One launch used an abbreviated revision by mistake and was correctly refused before
output/table creation. Relaunched with the exact full pinned HEAD. No gate changed.
Worker3 had zero running Spark jobs before launch.

**Physical preparation passed:** retained table
`local.experiment.integrity_sf1_20261014_0024`, snapshot 2963541948322332238,
6,001,215 rows, 16 files, 152,325,814 bytes. Parsed and loaded null checks both zero;
physical count and metadata record count agree; source SHA256 unchanged after load.
Original broken table and source data were preserved. No reset/drop/restart/cancel.

Evidence: `results/sf1_source_integrity_20261014_0024/` on worker3 includes exclusive
events log, frozen configuration, copied code and result. Audit saved in
`sf1_preparation_validation_2026-10-14.json`. Eleven statements completed without
failure. Six statement markers matched actual Spark REST job descriptions, including
source scan, CTAS and physical loaded scan. Catalog commands need not create jobs.
Marker-to-job attribution is now observed; actual completed-stage interval overlap
has not yet been validated. Do not infer treatment labels from client overlap.

Next ready unit: inspect REST stage timestamps/job-stage mapping, then preregister
and implement bounded control/concurrent-query/rewrite correctness on isolated
tables at recorded snapshots. Verify rewrite counts, unchanged row/result contents,
and stage overlap. No performance or scheduling benefit claim follows from this
source preparation. The copied-code package protects provenance but is not yet a
general immutable run-packaging interface for future long experiments.

## Outstanding resources/gates

### 00:39–00:47 IST: first query/rewrite pilot and repair

Committed/synced pilot and task-level overlap analyzer as 04de0a1; all five changed
file hashes matched. Protocol preserves measured source file count with explicit
repartition, runs four control/concurrent/post query identities, checks an exact
bidirectional full-row multiset, and requires actual task overlap. Query controls
use 60-second prior telemetry, not future samples. No legacy guard enabled.

First pilot retained at `results/sf1_correctness_pilot_20261014_0039/` on worker3.
An abbreviated revision launch was refused before effects; correct full revision
used for the physical run. This repeated command mistake is recorded; future launch
commands must use the full tool-observed HEAD, not a manually shortened value.

**Failed gate:** after successful physical rewrite output `[16,1,164550027]`,
control-session metadata still reported the original 16-file state. The pilot
refused acceptance and preserved all artifacts/table. Four concurrent query
results matched controls before that failure; 80 actual telemetry intervals logged.
Task overlap/full-multiset/post-query checks were not reached, so no treatment
labels or correctness acceptance follow.

Fresh-connection read-only audit found the committed new snapshot
3129288059524244264, one file, 6,001,215 records, 163,892,210 bytes. Explicit
REFRESH TABLE in that fresh session preserved those readings. Actual rewrite job
2063 was attributed by unique table description and group REWRITE-DATA-FILES-6.
Evidence indicates stale control-session relation caching after another Thrift
connection commits. Added a post-commit REFRESH TABLE before postconditions.
This invalidates session metadata; it does not rewrite/reset/drop data.

See `sf1_failed_pilot_validation_2026-10-14.json`. Next: separately preregister a new
destination/output and rerun all unchanged acceptance checks with the cache repair.
Do not relabel the failed pilot accepted or relax overlap/result/row gates.

No accepted SQL-arrival replay manifest or clean event-linked training dataset.
SF100 complete source verification and Alibaba member/mapping review are pending.
Publication claims and sufficient independent experiments remain future work.

### 00:54–00:58 IST: repaired pilot passed

Separately preregistered second pilot as commit 776c86d, with unchanged correctness
gates. Verified full local/worker3 HEAD, protocol and three physical module hashes;
worker3 had no active physical driver or running Spark job before launch. Used the
exact full tool-observed revision. Original failed table/output retained.

**Passed bounded physical correctness:** retained table
`local.experiment.integrity_pilot_20261014_0054`; snapshots
4510401085806035540 (before) and 7970187667229592262 (after).
Actual binpack result: 16 rewritten files, one added file, 164,550,027 rewritten
bytes; final file 163,892,210 bytes. Physical rows remain 6,001,215. Full bidirectional
EXCEPT ALL comparison across every column found zero differences, including duplicate
multiplicities. Four concurrent and four post-rewrite result sets matched controls.

All four queries had attributable successful Spark task-lifetime overlap with the
useful rewrite: Q0 0.383s, Q1 2.613s, Q2 0.436s, Q3 0.237s (union duration, not inflated
task-pair totals). Raw tasks/stages/jobs are preserved, not inferred from client
timestamps. This establishes overlapping task lifetimes, not simultaneous CPU
instruction execution or causal latency effects.

Independent recorded-artifact audit verified every overlap pair lies inside both
actual SUCCESS task lifetimes; every request completed without failed events; all
four control/concurrent/post results match. Eight pre-query 60-second windows met
declared coverage/freshness and preceded query submission. Minimum measured coverage
98.40%, maximum feature age 0.959s; 107 actual telemetry intervals, 26 completed
statements, 192 event records. See `sf1_correctness_validation_2026-10-14.json`.
Worker3 raw/frozen code/config/results: `results/sf1_correctness_pilot_20261014_0054/`.

This clears the bounded measurement-path pilot gate only. It does not supply enough
independent training blocks, a traced offered-load generator, 300-second window
validation, forecasting or a performance benefit claim. Legacy guards remain blocked.
The diagnostic simultaneous four-client pattern is not a causal single-query
compaction experiment. No failed evidence has been promoted.

Next ready independent unit: full Alibaba member schema/type/missing-value/timestamp
audit against the fetched publisher schema. It is running locally, using the actual
verified archive; no extraction/replay/mapping or fabricated input. Initial output
already flags batch-task schema issues, which must be reviewed before arrival mapping.

### 00:58–01:01 IST: full Alibaba audit completed

All six actual CSV members read fully; per-member byte hashes and column/type/
missing/time counters retained in `alibaba_member_validation_2026-10-14.json`.
Archive SHA256 rechecked before/after. Publisher schema saved verbatim in
`datasets/provenance/alibaba2017_schema.csv`; source URL and tool/schema hashes in
`alibaba_full_member_audit.md`. No member extraction, fabricated data or replay.

Batch task: 80,553 rows, no duplicate job/task keys, 80,386 positive and 167 negative
create timestamps; 9,017 rows missing CPU plans and 9,017 missing memory plans.
Batch instances: 16,094,656 trial records, job/task IDs each missing in 3,992,098.
Resource weighting and joins cannot silently fill these omissions. Usage members
also have genuine missing fields. Container-event rows all have nine fields against
the eight-column schema; sampled rows show a trailing empty field. The strict audit
preserves the width failure and does not pretend those rows have validated semantics.
Next unit must verify the ninth field is empty for every row before explicitly
normalizing this serialization detail. Positive task creations remain a candidate
for honestly labelled cluster-task-driven benchmark demand, never observed SQL arrivals.

### 01:09–01:15 IST: serialization resolved; long integrity checks started

Container-event serialization review verified every one of the 11,102 rows has
exactly one ninth, empty field. Explicitly removing only this CSV terminator yields
eight documented semantic fields with no required omissions or numeric violations.
10909 records are time-zero pre-trace creations; only 193 have positive timestamps;
all events are Create. The strict raw width-failure audit remains unchanged.
See `alibaba_serialization_validation_2026-10-14.json`; raw member hash agrees with
the strict audit. This does not create a replay or fill any data.

Full SF100 byte-hash/newline-count inventories started separately on local and
worker3 using committed tool 70d3863. No SF100 generator manifest is present.
Customer source already matches: 15,000,000 rows, 2,463,490,271 bytes and SHA256
874a0706b4bbcc83acbbf9bad94fa2d4cb7207febc0d39f45b982575893efb4c.
Remaining tables are still being scanned; do not mark full verification complete.
No latency pilot while these I/O scans run. Processes are observation-only and
must never be killed at cutoff. Pending outputs:
`docs/sf100_local_source_validation_2026-10-14.json` (local),
`results/sf100_remote_source_validation_2026-10-14.json` (worker3).
Tool sessions at launch: local 63555, remote 38441; inspect process/output state
before starting replacements if resuming in a new turn.

Next independent tasks: preserve exact positive task-create timestamps and identities
as a clearly labelled candidate (no mapping/zero-padding/compression/query mix), and
validate actual 60/300-second host telemetry windows during the real source I/O scan.
Batch-task last reported create time is 60181 seconds; do not invent a quiet tail
out to the publisher's nominal 24-hour period or claim complete event-free coverage.

### 01:14–01:17 IST: observed event candidate and local SF100 inventory

Preserved all 80,386 positive reported task-create events with unique job/task IDs
and source-row numbers, sorted at original timestamps 5 through 60181 seconds.
167 negative pre-trace events explicitly excluded; no padding/compression/looping,
query assignment, resource imputation or final-status prediction features.
Largest reported inter-event gap is 383 seconds; peak 155 reported events/second.
Neither an event-free gap nor the interval after the last event establishes a
verified idle SQL-server window. See `alibaba_task_arrival_profile_2026-10-14.json`.
Candidate directory mirrored locally/worker3 with all three artifact hashes matched:
`results/alibaba_task_arrival_candidate_20261014/` (CSV, profile, frozen transform).

Local SF100 full-source inventory completed in 186.1 seconds: all eight `.tbl`
files, total 114,641,618,862 bytes. Actual lineitem newline row count 600,037,902,
orders 150,000,000, customer 15,000,000, part 20,000,000, partsupp 80,000,000,
supplier 1,000,000, nation 25, region 5. This is actual source-file counting,
not just old Iceberg metadata. It does not validate typed fields/generator provenance.
Remote inventory is still running; full cross-machine agreement remains pending.

Actual host telemetry check started on worker3 with preregistered 60/300-second
windows, one-second cadence and 305-second warmup during real SF100 source I/O.
Pending output: `results/telemetry_window_integrity_20261014/`, session 80735.
Own observer ends naturally after validation; it does not stop services or data jobs.

Mirroring the four newly generated observer/source/failed/successful pilot evidence
directories locally for fallback; historical handover archive and absolute-path
Iceberg warehouse metadata remain untouched. Verify mirrored raw artifact hashes
after transfer; do not register worker3 catalog metadata as a local executable table.

### 01:19–01:22 IST: source agreement, window validation and cadence audit

**SF100 completed on both machines:** every one of the eight table files agrees by
fresh SHA256, bytes and actual newline row count, total 114,641,618,862 bytes.
Local scan 186.1s, worker3 647.8s. No process killed or data changed. See local/remote
source validation JSONs and `sf100_cross_machine_validation_2026-10-14.json`.
Generator/build manifest, typed parsing and relational integrity remain unverified;
these checks cannot certify source authenticity or equivalence to later Iceberg appends.

**Actual 60/300-second window checks passed:** 59.697/299.608 seconds of measured
coverage, freshness 0.303/0.392 seconds. Independently recomputed CPU/read/write
weighted means and covered time from retained actual monotonic interval records.
281 measured intervals; maximum gap 1.234s, below the preregistered 2s limit.
See `telemetry_window_validation_2026-10-14.json`; this is real host observation
during source I/O, not database latency or model evidence.

Audit found a separate target-cadence defect: the observer used max(next deadline,
now+interval) even when not late, adding synchronous log-write duration to every
period. Actual weighted windows remain valid under declared tolerances, but this
explains fewer samples than the nominal one-second target. Corrected to retain the
periodic deadline unless already missed; never emit catch-up pseudo-samples.
Registered a separate unchanged-gate 60/300-second revalidation after the repair,
observing actual current host conditions without generated stress. Pending directory:
`results/telemetry_window_fixed_cadence_20261014/`. Do not claim repaired cadence
validated until that new physical observation completes.

Raw newly generated observer/source/failed/successful pilot evidence is mirrored
on both computers: 29 files, all hashes match, recorded in
`physical_evidence_mirror_2026-10-14.json`. Only hash manifests/reviews go to GitHub;
raw REST logs remain local/worker3. Iceberg data/metadata remain on worker3 and
must not be copied into a local active catalog with wrong absolute paths.

### 01:25–01:29 IST: real database-arrival resource acquisition

Verified primary Snowset README/schema/download pages: reported Snowflake query
entry timestamps and warehouse identities, approximately 70 million queries across
14 days. No SQL text. HTTPS endpoints reachable; live Parquet archive HEAD size
8,202,394,513 bytes and modification time recorded in acquisition protocol. Selected
Parquet for projected arrival-column analysis; local disk over 1TiB available and
DuckDB installed. This addresses the resource gap only after full acquisition and
schema validation, not by pretending Alibaba CPU/task records are SQL arrivals.

Implemented exclusive provenance-preserving acquisition tool and preregistered
config. Large bytes stay outside GitHub; preserve partials on failure and do not
claim dataset available before the exact-byte download completes. Next gates and
future-information risks recorded in `snowset_acquisition_and_scope.md`.
Repaired telemetry-cadence observer is still running naturally; no duplicate launched.

### 01:29–01:38 IST: cadence passed; acquisition failure audited

Repaired observer completed naturally: 305 real intervals, median 0.999999981s,
maximum 1.026s. Actual 60/300-second windows have 59.961/299.927 seconds covered
and 0.039/0.073 seconds freshness. Independently recomputed all weighted CPU/read/
write metrics from raw monotonic records; unchanged gap/coverage gates pass. This
host was idle after SF100 scanning, so it is not a controlled performance comparison
with the earlier loaded observation. Evidence mirrored; see
`telemetry_fixed_cadence_validation_2026-10-14.json`.

**Snowset acquisition failed safely:** advertised 8,202,394,513-byte monolithic GET
ended after 1,568,768 bytes. Partial/source config/code/progress retained; no dataset
availability, extraction, forecast or replay claim. Review records partial hash and
actual failed request metadata in `snowset_failed_acquisition_2026-10-14.json`.
Both local/worker3 served exact first/tail HTTP206 ranges with unchanged modification
time. One-MiB range fully received on each, identical SHA256; 5.88s locally vs 2.68s
worker3. Registering an explicit bounded range acquisition on worker3, with per-range
size/version/offset/hash checks and exact-order final assembly; original failure
preserved. Operational range/retry/concurrency settings are justified by these probes,
not scientific outcome tuning. No model/replay acceptance gate is relaxed.

Audit also identified intent logging inside the original client elapsed-time target.
Added actual execute-call start and separate request lifetime/instrumentation cost,
with explicit `client_submission_v1` timing contract. Old correctness evidence
still proves results/rows/task overlap, but cannot supply clean service-time targets.
See `client_statement_timing_contract.md`. New timing boundary requires a real
read-only verified SF1 query check before any collection/export uses it.

### 01:40–01:45 IST: corrected timing validated; ranged acquisition active

Actual four-query read-only check against preserved verified SF1 snapshot passed;
all results matched preserved physical controls. New call-start/service/request
timings have valid monotonic order and exact duration decomposition. Each actual
intent-persistence delay was approximately 33ms and is recorded separately, not
subtracted as a guessed constant. Historical intervals remain unsuitable for clean
service-time targets. See `client_timing_validation_2026-10-14.json`; raw directory
`results/client_statement_timing_integrity_20261014/` mirrored locally with hashes.
This validates the measurement boundary, not performance or model accuracy.

Original rejected Snowset partial and acquisition provenance mirrored for fallback;
all file hashes matched. New worker3 range acquisition started naturally, bounded
to four HTTP workers with explicit source-version/offset/length checks and complete
range hashes. It verified 80 ranges/83,886,080 bytes in its first recorded minute.
It remains incomplete; do not open it as an accepted dataset or run forecasts.
Pending directory: `datasets/snowset/range_acquisition_20261014/`; progress and
acquisition_record JSON report exact completed ranges/status. Session 71017 at launch.
Do not duplicate, force-cancel or remove partial/range artifacts.

Next ready work while acquisition proceeds: preregister an identifiable matched
physical collection design and inspect the unsafe offered-load/ingestion paths
without re-enabling legacy launchers. Once full source bytes arrive, validate gzip/
tar/schema/timestamp coverage and warehouse identities before arrival forecasting.

### 03:32–03:45 IST: source recovery and collector retirement

Range acquisition stopped naturally after three short responses at main range 2984.
Recorded 2,988 delivered ranges/3,133,145,088 bytes; 2,991 complete part files remained
because in-flight requests finished before the failure record. No process killed,
bytes padded or partial dataset used. Per-range hashes/headers were held in memory
until final manifest creation in that tool; failure exposed a durability gap.
Original source/config/code/status/partials remain untouched.

At the failed offset a smaller 256KiB range completed on worker3 (local response
remained short). Registered separate recovery: copy completed parts from the verified
exclusive producer; hash at recovery and explicitly retain the missing original
receipt limitation. Do not fabricate past headers/hashes. Fresh source ranges get
durable receipts and bounded adaptive transport splitting after rejected transfers.
Full archive/Parquet validation remains required before declaring the dataset usable.

Retired the remaining dead collector/evaluator execution bodies: closed-loop delay
mapping, randomized self-inserts, completion-flag labels, sample-count CPU windows,
unexplained SLA/baseline defaults and fixed +2-file projection. Entry guards remain;
accepted model loading alone cannot authorize decisions. Historical code/results
remain recoverable in Git and preserved local handover evidence.

Added `matched_physical_collection_design.md`: same original snapshot/files for
control-before/during/control-after interference comparisons; compacted-layout
benefit separated; one query per rewrite initially; actual task exposure and logger
timing; independent episodes and training-only selection; exact open-loop arrivals;
no invented ingestion. The earlier four-client pilot is not identified cost data.

Recovery started with 2,991 retained complete ranges copied and rehashed, and resumed
new verified transfers. New progress passed 3,037 ranges/3,184,525,312 bytes. Source
recovery session 55252; inspect `datasets/snowset/recovery_20261014/recovery_record.json`
before any replacement. The old failure/evidence is preserved. No accepted corpus yet.

Checked primary AutoComp paper and corrected historical VLDB-2024 attribution to
SIGMOD-Companion 2025. The legacy ratio/count policy is not a verified reproduction
of its full candidate-estimation/ranking/scheduling framework. See
`autocomp_baseline_verification.md`; faithful baseline selection remains a gate.

Removed the baseline module's remaining unsupported peer-reviewed/industry-standard
claims and default tuning values. `AutoCompPolicy` now explicitly refuses the false
reproduction name; separately named prototypes require declared parameters and actual
metadata, with no missing-field fallback. Syntax/source review performed, no fake
metadata tests or baseline run. Evaluator remains blocked.

### 02:57–03:00 IST: full Snowset source validation prepared

Recovery remains active; no second acquisition or Spark workload launched. At 02:57
IST it had 3,853 complete main ranges / 4,040,163,328 bytes. Dataset remains unaccepted.

Added `scripts/validate_snowset_source.py` and a separate registered configuration.
It refuses an incomplete recovery record before reading/extracting data and requires
the final record's explicit SHA256, producer-source hash, full object length/hash,
and stable source custody. Exclusive manual extraction rejects links/special files,
path traversal/absolute paths, duplicate members and truncation; complete gzip drain
forces CRC/length verification. Failed artifacts stay in place. No blanket tar
extraction, overwrite, removal, imputation or partial-corpus forecasting.

DuckDB inventory requires consistent actual member schemas and native BIGINT query/
warehouse IDs plus native timestamp arrivals. It reads every column value across the
full corpus using an aggregate value hash, records all null counts, verifies globally
unique non-null query IDs and complete timestamp coverage, and writes an observed
warehouse inventory. No warehouse/window selection or SQL mapping happens here.
This checks arrival-critical schema fields; it does not certify every published
resource-column unit/type. Recorded value hash is a decoding diagnostic, not a
publisher authenticity checksum. Publisher cryptographic authenticity and the
recovered original-range receipt gap remain explicit limitations.

Remote DuckDB 1.5.6 was verified using an actual retained SF1 Parquet member: 376,585
rows decoded, real schema inspected, aggregate hash worked; parameterized COPY was
planned without execution. Corrected view creation to DuckDB's relation API, avoiding
unsupported prepared parameters in CREATE VIEW. Syntax/diff checks pass. These are
API/real-source checks, not a Snowset validation result. Full source validation has
not launched and is gated on acquisition completion. Registered offline limits:
4GB working memory, two CPU threads, disk spill, 1GiB reserve beyond each member's
size; these are operational settings, not scientific acceptance thresholds.

Post-sync guard audit on worker3: actual in-progress recovery record rejected with
exit 1 and explicit complete-acquisition error. Validation output directory was
not created. Evidence: `snowset_validation_guard_check_2026-10-14.json`. Commit
`1a251b8` pushed; worker3 fast-forwarded; HEAD and all four intended file hashes
matched. Recovery continues naturally; no services/processes interrupted.

### 03:09–03:12 IST: bind training service time to actual raw clocks

Audit found the trainer compared target duration with UTC timestamp subtraction at
nanosecond precision. Recorded UTC has microsecond precision; the authoritative
client duration is the actual monotonic execute-start/fetch-end interval. Repaired
this boundary without subtracting a fixed logger offset or rewriting old evidence.

Added `statement_timing.py`: completed statements require actual-call contract, UTC
identifiers, integer monotonic ordering and exact duration decomposition. Every
training row must bind to its raw completed statement by experiment/measurement ID,
query ID, actual-call UTC interval and clocks/durations. Raw JSONL provenance is
mandatory, retained in bundle evidence, with input hashes checked before fitting.
No unfinished ledger or metadata statement can silently provide a query target.

Actual six-statement/four-query timing check passed ledger and exact raw-field
projection binding. An initial projection included two metadata statements with
missing query identity; that check refused them. Restricted the verification to
the four actual query records and added an explicit metadata refusal guard. This
is a projection of real measured fields, not a fabricated training CSV. Historical
correctness pilot failed the actual-call timing contract; RUN_002 still failed
required physical columns before fitting. No models trained. Evidence:
`raw_statement_timing_binding_validation_2026-10-14.json`.

Remaining blocker: trainer's rewrite interval checks do not independently bind
Spark task overlap, measured feature windows or snapshot layout to raw evidence.
An approved exporter and engine-label cross-reference gate are required before any
publication collection/training. The old client-overlap check cannot certify that
methodology. Recovery continues; no physical Spark workload was launched while
source transfers were active.

### 03:24–03:27 IST: reconstruct physical exposure before training

Recovery remains in progress (5,705 complete ranges / 5,982,126,080 bytes at first
check). No new workload or duplicate download launched.

Added offline `engine_label_binding.py` and integrated it before model fitting.
The trainer reconstructs query/rewrite tasks from preserved jobs, stages and full
taskList responses using the existing SQL-marker/exclusive-table attribution.
Compaction event IDs, SQL/table, physical result counts and request/result intervals
must match actual maintenance statements; every attempt/no-op must be represented,
failed/incomplete or hidden maintenance refuses certification. Positive treatment
requires a matching positive-byte useful rewrite and actual task-lifetime overlap.
Baseline queries cannot have useful rewrite exposure, and prior conservative
request-interval/no-op gates remain. Added completed-stage coverage verification to
prevent partial stage sets from certifying overlap. No RPC or physical query was
issued by this verifier.

Read-only reconstruction on the actual retained correctness log reproduced four
controls with zero exposure and four concurrent exposures of approximately 0.383,
2.613, 0.436 and 0.237 seconds. Physical rewrite result bound to its actual statement:
16 rewritten files, one added file, 164,550,027 rewritten bytes; one attributable
rewrite task. Exact projection of these measured labels/events passed binding.
Evidence: `offline_engine_label_binding_validation_2026-10-14.json`. No fake task
records, fabricated training features, new CSV, model fitting or publication result.
Historical pilot still fails new timing contract and has four-client confounding.

Remaining export gates: measured CPU/I/O feature reconstruction, snapshot/layout
binding, actual engine-session scope and exclusion/measurement of other foreground
and background work. Statistical protocol/common support and trace mapping remain
necessary. Task lifetimes still do not establish simultaneous CPU instructions;
absence of source-audit findings cannot certify the entire pipeline.

### 03:39 IST onward: exact telemetry cutoff repair

Audit of the window routine found a possible post-cutoff sample race: cutoff was
captured before taking the sample lock, so a newly appended sample could end after
that cutoff and produce negative freshness. Window selection now includes only
completed samples ending at/before its captured cutoff; negative age is refused.
Exact monotonic start/end bounds are recorded, with a new explicit window contract.
Added actual total/available host-memory counters and weighted used-memory fraction
(total minus available, divided by total), not RSS or a fabricated measurement.

Added independent raw-counter/window reconstruction. It verifies origin/interval
chain, actual CPU and byte counter deltas, elapsed time/rates, memory counters, exact
cutoff, weighting, coverage and freshness against the reported window. Original
coverage/gap/freshness gates remain. Historical windows without exact bounds cannot
be silently relabelled; their earlier diagnostic reviews remain preserved.
A separately registered 305-second observer will check real host conditions with
60/300-second windows, without generating database work. Observation ends normally
before immutable-ledger verification; no database service/process is stopped.
No physical acceptance is claimed until that check ends and reconstruction passes.

Implementation commit `c77954a` pushed and fast-forwarded on worker3; HEAD and all
five changed file SHA256 values matched. Checked for an existing window observer
before launch. Own bounded observer PID **376224**, log
`results/telemetry_exact_bounds_20261014_launch.log`, artifacts
`results/telemetry_exact_bounds_20261014/`. At 03:41:57 IST its raw ledger had
26 real events and no reported launch error; result pending. Source recovery
remains active with 6,935 main ranges / 7,271,874,560 bytes. No Spark workload
launched and no service, table or existing process altered. Next heartbeat must
audit observer completion and source recovery before launching dependent work.

Clock audit: corrected a one-hour conversion error in recent source-validator,
raw-timing, engine-label and exact-window ledger entries against observed UTC tool
clocks (IST = UTC +05:30). Latest clock 2026-10-13 22:11:57 UTC corresponds to
2026-10-14 03:41:57 IST. Earlier inherited ledger headings are not independently
re-timed here; raw event UTC/process/acquisition records are authoritative. Deadline
remains 2026-10-14 07:00 IST = 01:30 UTC, and physical-operation cutoff 06:15 IST
= 00:45 UTC. No execution evidence or measured duration was altered.

### 03:54 IST: independent window audit rejected publication-lag ambiguity

The exact-bound observer PID376224 ended naturally with a failed reconstruction,
not an accepted result: `Feature UTC differs from last available sample`. Raw log
and launch traceback retained at `results/telemetry_exact_bounds_20261014/` and
its launch log. A counter interval can finish before the feature cutoff but still
be awaiting durable logging/publication into the sampler's history. The final raw
ledger later contains that interval; cutoff alone cannot reconstruct the history
that the feature actually saw. This is an availability-frontier ambiguity, not a
reason to weaken freshness/coverage or silently alter the historical window.

Repair: record `last_available_sample_end_monotonic_ns`, taken directly from the
actual selected sampler history, alongside exact window bounds. Independent raw
reconstruction requires that explicit frontier to exist and lie before/equal cutoff,
and uses the recorded available prefix. Original coverage, gap and freshness gates
remain. No inferred frontier is added to failed old records. Register a new exclusive
305-second observer directory for physical revalidation. Source recovery is still
active, 7,662 ranges / 8,034,189,312 bytes at first audit; no duplicate acquisition.

Repair commit `174b674` pushed; worker3 fast-forwarded; HEAD and changed-file
hashes matched. Replacement observer **PID379895**, artifacts
`results/telemetry_available_frontier_20261014/`, launch log with matching prefix;
no existing observer was active at launch. Original failed observer package/log
mirrored locally, all hashes equal; 305 actual intervals retained. Evidence summary
`telemetry_exact_bounds_failure_2026-10-14.json`. Added explicit next-export contract
`physical_feature_export_contract.md`: query measurement IDs must bind windows and
metadata statements, snapshot-pinned SQL and physical inventory, actual demand and
engine/background context. Current correctness pilots cannot supply those missing
provenance fields through invented defaults.

At 03:57:19 IST assembled Snowset partial had the expected 8,202,394,513 bytes, but
recovery status was still in_progress. Expected size alone does not authorize dataset
access; wait for natural final hash/status record before full archive validation.

Source recovery ended naturally with status `downloaded_bytes_only`: **7,823 ranges,
8,202,394,513 bytes**. Assembled object SHA256
`f9edef48da1eb940d80a9111c80e27613c767734728539d019cc50ec89c5f10e`;
final recovery-record SHA256
`1b1936d4e491f2753a1b337fa027e84f4ca3fe8fe3446bc10e0e3eb7a6fe5725`.
These self-measured hashes do not remove the prior recovered-range receipt limitation
or establish independent publisher cryptographic authenticity.

Full Snowset validator launched only after completed status/hash record, with no
existing validator/output, at execution revision `174b674`. Worker3 **PID380748**,
log `datasets/snowset/source_validation_20261014_launch.log`, launch receipt JSON
with matching prefix, output `datasets/snowset/validated_source_20261014/`. Full
archive/Parquet/identity/arrival checks pending. Dataset remains unaccepted; no SQL
mapping, arrival forecasting, cost fitting or new Spark workload was launched.

A separate byte-preserving local fallback mirror of the completed source object
started at `datasets/snowset/source_mirror_20261014/` (execution session81938).
Partial copy uses `.copying`; final name appears only after complete expected-size
and SHA256 comparison with the pinned completed recovery record. Status is in
`mirror_record.json`. This copy is not a second acquisition or source acceptance;
full validation is separate. No archive/data bytes are staged for GitHub. Completed
recovery metadata/launch receipt also copied locally under
`datasets/snowset/completed_recovery_metadata_20261014/`. Inspect existing copy and
validator before starting any duplicate operation.

### 04:09–04:11 IST: telemetry passes; Snowset reader-input bug rejected

Replacement observer completed naturally and passed independent raw-counter
reconstruction: 60/300 actual intervals; coverage 59.932998666/299.844025973 seconds;
freshness 0.067001334/0.155974027 seconds. CPU/I/O/memory fractions exactly matched
raw counter reconstruction with recorded cutoff and availability frontier. This is
measurement integrity under source-transfer conditions, not workload/model accuracy.

Snowset full validation finished with gzip/tar integrity and all-value decoding, but
correctly refused the unique-ID gate: 138,364,148 reader rows versus 69,182,074 unique
queries. Cause was my enumeration bug: `rglob('*.parquet')` matched the directory
`snowset-main.parquet` as well as its 2,000 regular Parquet files. DuckDB read the
whole directory once and every listed file again. No source duplicate/deduplication
claim follows. Independent regular-file footer inventory reports 69,182,074 rows.
The rejected result is preserved in `datasets/snowset/validated_source_20261014/`.

Fixed enumeration to require regular files and record their count. Register a new
exclusive full-validation output, retaining original uniqueness/null/type/gzip/hash
gates. No invented row-count gate or silent deduplication. Full re-extraction and
value/identity checks are justified by this source-reader code change; acceptance
remains pending. Local completed-source mirror remains active; inspect its record
before any replacement. No Spark query/service/table altered.

Repaired full Snowset validation launched on worker3, **PID384597**, execution
revision `c9e77a4`, using the same pinned completed acquisition-record hash. New
output `datasets/snowset/validated_source_file_only_20261014/`; matching launch log
and JSON receipt under datasets/snowset. Original failed validation record copied
locally for fallback; diagnosis summary `snowset_reader_input_failure_2026-10-14.json`.
Repair code/config/review pushed and fast-forwarded; HEAD and changed hashes matched
before execution. Full source acceptance remains pending.

Cross-machine telemetry audit initially refused exact feature equality locally:
worker3 Python3.10 sums floats left-to-right, while local Python3.12 changed built-in
float summation. Observed relative differences were below 9e-16, including the
299.844025973-second coverage. Specified explicit ordered IEEE additions in producer
and independent verifier, reproducing observed worker3 arithmetic exactly on both
Python versions. No tolerance, measurement adjustment or weakened gate introduced.
Unchanged actual 60/300 windows then passed locally, and all copied package files
matched worker3 SHA256. Evidence: `telemetry_available_frontier_validation_2026-10-14.json`.
This verifies host-counter measurement integrity under actual source operations,
not idle-host comparison, query performance, training features or model readiness.

Completed-source local fallback copy finished naturally: **8,202,394,513 bytes**,
SHA256 exactly matching the worker3 assembled object. `mirror_record.json` reports
`verified_bytes_only`; final archive name exists under
`datasets/snowset/source_mirror_20261014/`. Evidence summary:
`snowset_byte_mirror_validation_2026-10-14.json`. No second transfer or source
acceptance claimed; repaired full source validation is still running.

### 04:24 IST onward: complete real arrival source validated

Corrected Snowset validator completed naturally with `validated_arrival_source_only`.
Full gzip/tar and all-value Parquet decoding passed; 2,000 regular files, 69,182,074
rows and unique query IDs, 2,051 warehouses, zero missing queryId/warehouseId/createdTime.
Actual UTC range 2018-02-21 20:00:00.286 to 2018-03-07 04:11:22.719; no invented quiet
tail or duplicate removal. Extracted file hashes remained unchanged. Source record
and warehouse inventory copied locally, inventory hash checked. Evidence summary
`snowset_complete_source_validation_2026-10-14.json`. SQL text is absent; this accepts
arrival-source integrity only, not benchmark mapping/replay/model/paper readiness.

Prepared exclusive training-only arrival cohort extraction: first seven observed
days for selecting the highest training-volume warehouse (numeric-ID tie break),
next three reserved days, remaining complete-minute bins held out. This diagnostic
preregistration precedes warehouse-specific held-out curve inspection. All raw query
identities/timestamps retained; only incomplete global final bin excluded from
count evaluation and separately reported. Empty bins encode no reported arrivals
in the supplied corpus, not dummy events/proven idle periods. No completed outcomes
used for selection, no normalization, thinning/time compression, SQL assignment,
forecast fitting or model promotion. Three calibration days cannot justify a finite
90% daily-block conformal bound. Source hashes/identity checked before extraction.

Cohort extraction launched only after code/config publication and matching local/
worker3 HEAD + all five changed-file hashes. Worker3 **PID389249**, execution
`738d055`, artifacts `datasets/snowset/arrival_cohort_20261014/`, launch log and JSON
receipt with matching prefix. Full source record explicitly pinned at
`7ce2fa0e6693d753938cde5e1d9c3a32fd65e57bea05562bf362e6ae090c6bf0`.
No other source validator/extractor was active. Extraction hashes all source members
before reading; result/conservation/selection audit pending. Preserve any failed
package and repair before dependent forecasting. No physical Spark query launched.

### 04:29 IST: arrival-bin export API failure preserved and repaired

First cohort extractor ended naturally with a DuckDB internal parameter-binding
error at COPY combining bound bin-query values and filename. It had exported the
actual 187,413,343-byte raw-arrival CSV but did not finish count conservation/hash
gates, so the package is failed/unaccepted and preserved. Warehouse selected solely
from training arrivals: 4521920227430629158, 1,329,355 first-week reported arrivals.
No selection/parameter changes follow from this outcome.

Repair materializes bins through parameterized CREATE TABLE AS SELECT (already
supported by the real selected/count tables), then COPY with only a filename
parameter, matching the successful raw-arrival/source-inventory API. New exclusive
`arrival_cohort_export_repair_20261014` output; source integrity, chronology, selection
and conservation gates unchanged. Full raw log remains under original launch prefix.
No forecasting, incomplete-data use or model fitting.
