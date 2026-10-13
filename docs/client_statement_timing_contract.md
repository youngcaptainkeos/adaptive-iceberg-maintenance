# Client statement timing contract

The first correctness pilot's client interval began before durable intent logging,
so it included that instrumentation I/O. Its verified task overlap, row preservation
and result equality remain valid; its client duration is not a clean service-time
target and must not be silently exported as one. No pilot was approved for training.

New records carry `timing_contract: client_submission_v1` and distinguish:

- `request_start`: client request intent before durable logging.
- `client_execute_start`: immediately before invoking the real Thrift execute call,
  after the intent record is persisted.
- `execute_return`: execute call returns; `fetch_end`: result fetching completes.
- `client_elapsed_ns`: monotonic fetch-end minus actual client execute-start.
- `request_to_result_ns`: monotonic fetch-end minus request intent.
- `instrumentation_before_execute_ns`: execute-start minus request intent.

These client service times still include RPC/planning/execution/fetch overhead; they
are not pure engine CPU time. Spark task records separately establish task lifetimes.
For future workload replay, offered arrival, queue entry, dispatch and completion
must remain distinct. Do not shift offered arrivals to hide admission/queue delays.
Training exporters must require the timing contract and actual start, and explicitly
review clock units/UTC versus monotonic elapsed time. Historical records without
these fields cannot be repaired with an invented logging offset.

Logger overhead also affects host CPU/I/O and must be measured consistently across
policies. A service-time interval excluding intent persistence does not remove that
resource overhead from the physical system.

## Raw binding before model fitting

The trainer now requires `timing_contract: client_submission_v1`, four observed
integer clock columns named `<request_start|client_execute_start|execute_return|
fetch_end>_monotonic_ns`, and the three integer duration columns above. Monotonic
fetch-end minus actual execute-start is the latency target. UTC timestamps identify
chronology and must equal the raw actual-call/result timestamps; UTC subtraction
cannot manufacture nanosecond precision or replace monotonic duration.

Training declarations must add `raw_statement_events`, a nonempty list of checked
JSONL artifact references. Before fitting, each CSV row binds by experiment and
measurement ID to a completed raw physical statement with the same query identity,
timing contract, clocks and decomposed durations. The ledger requires one durable
intent and one completed/failed outcome per request, without conflicting identities
or unfinished requests. Metadata statements cannot become training queries. Raw
ledgers remain part of the published bundle's checked execution evidence.

Verified against the six actual statements/four actual query projections from the
client timing-boundary check; the older correctness pilot was rejected for missing
actual-call timing. This is timing/identity validation only. Telemetry, snapshot,
maintenance result and task-overlap label cross-references still require a reviewed
exporter. No accepted training dataset or model fit follows from these checks.
