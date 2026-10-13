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
