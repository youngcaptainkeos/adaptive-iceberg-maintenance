# Alibaba 2017 full-member audit

The existing publisher-matched archive was read completely against the downloaded
[publisher schema](https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2017/schema.csv).
Schema SHA256: `4b60a8a90b57e3f3afbb67c4aadaf4906470b86e3dc8bc939e0f0992474ea77f`.
Audit tool SHA256 at execution:
`7f977ca9026fa1615245a01d1ac38a72a729ffe1196ab2a48f9a647df1139d40`.
Raw audit: `alibaba_member_validation_2026-10-14.json`; each member has a full-byte
SHA256, row/column counts, type/finite-value checks and missing-value counters.
Archive SHA256 was rechecked before and after the audit. No member was extracted,
transformed to replay, imputed or replaced by generated data.

| Member | Actual rows | Main findings |
| --- | ---: | --- |
| batch_task | 80,553 | Eight fields throughout; unique job/task keys; 80,386 positive create times and 167 negative pre-trace times. CPU and memory plans each missing in 9,017 rows. |
| batch_instance | 16,094,656 | Twelve fields; job/task IDs each absent in 3,992,098 rows, machine IDs absent in 1,342,871; extensive optional resource omissions. These are trial records, not necessarily unique instances. |
| server_event | 1,352 | Seven fields; required fields conform; optional event details absent for initial add events. |
| server_usage | 187,963 | Eight fields; five mandatory field omissions in total. |
| container_usage | 1,480,906 | Twelve fields; 18 mandatory field omissions and five optional disk omissions. |
| container_event | 11,102 | All rows have nine CSV fields against eight documented. Sample rows end with an extra empty field/trailing comma. Strict audit rejects the width and therefore does not yet parse timestamp/type semantics. |

The audit's `schema_violations` sums field-level violations plus malformed row widths;
it is not the number of distinct bad rows. No numeric/nonfinite violations occurred
in members whose widths matched the schema. Container events need a separate full
check confirming the ninth field is empty everywhere before an explicit serialization
normalization can be accepted. Do not silently discard a nonempty ninth field.

The [publisher's known issues](https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2017/trace_201708.md)
include missing IDs and resource measurements. Zero/negative timestamps represent
pre-trace/censored events, not arrivals to invent at time zero. CPU usage is a
cluster resource series, not a SQL-arrival trace. Missing CPU plans prevent complete
task-resource-demand weighting. Positive task-create times could support a labelled
cluster-task-driven diagnostic after reviewed transformation; they do not establish
SQL text, query mix, ingestion demand, or original database arrivals.

Next gate: review serialization and timestamp completeness/gaps/duplicate handling
for any selected member, preregister the exact transformation and justified workload
mapping, and preserve original elapsed time. No replay is authorized by this audit.

## Subsequent explicit serialization review

`alibaba_serialization_validation_2026-10-14.json` confirms every container-event row
has exactly one extra empty trailing field, with full member bytes/SHA matching the
strict audit. Removing only that serialization terminator leaves eight documented
fields with no missing required values or numeric violations. All 11,102 events are
Create; 10,909 are pre-trace time zero and only 193 are positive-time events. The
strict audit remains unchanged. No semantic values were padded, dropped or imputed.

`alibaba_task_arrival_profile_2026-10-14.json` records the separately preserved
80,386 positive task creations at original times 5–60181 seconds, excluding only
167 explicit negative pre-trace records. It is an event candidate, not an executable
replay manifest. No claim of complete SQL-server idle coverage follows from its
largest inter-event gap or its unobserved tail.
