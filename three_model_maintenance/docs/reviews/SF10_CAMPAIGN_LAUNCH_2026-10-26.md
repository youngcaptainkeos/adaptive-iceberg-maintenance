# SF10 matched model campaign: actual launch — 26 October 2026

Implementation plan: ../plans/SF10_MATCHED_MODELS_2026-10-26.md.
Code/preflight/collection/fitting are distinct states; do not call constructors
or a running physical episode a trained or accepted model.

## Preserved failure

Original01 failed source admission before any SQL:0passed/0failed/6unattempted.
Fixed origin+3600s windows were empty. Real source-bin inventory2746467 and original
protocol/raw/ntfy preserved; worker3 HTTPS push128preserved, failure appendcommit
b044979 was fetched/fast-forwarded/pushed from laptop. No favorable physical retry.

## Fresh02 preflight

Detached wrapper2747802/controller2747803 passed at16:08:59UTC21:38:59IST:
source/AST/input digests, registered estimator constructors,12actual saved SF10
multi-table SQL/typed-result reconstructions, and all three full real source
schedules including exact source rows/bin totals. No SQL or fitting in preflight.
Source windows are prospective cost-data roles, selected by nonempty starting
arrival bin/complete1200s/purged consumed-source exclusions only:

| Role | Actual Snowset window (UTC) | Arrivals per arm |
|---|---|---:|
| Train | 2018-02-22 20:00:00.286–20:20:00.286 |3131|
| Validation | 2018-02-23 20:00:00.286–20:20:00.286 |2977|
| Reserved test | 2018-02-24 20:15:00.286–20:35:00.286 |3057|

These are real arrival times mapped round-robin to six declared benchmark SQL
queries, not original Snowflake SQL. No thinning/time compression, outcomes used
for window selection or claim that a low-load bin proves actual server idleness.
One warehouse/one family per split and nearby consumed engineering windows limit
independence; this remains an exploratory comparison, not population calibration.

## Actual live campaign

Nohup/failure wrapper2748171, coordinator2748173 launched16:09:36UTC21:39:36IST.
Frozen revisiond9935f380dd72f7d9846e23a21a8f9a2e66c3d0a.
Campaign protocol392814943fe2f768b8f0509a852af052cd60cfb4dadbdf2ef413349d17b16d03;
preflight result1263ff9f11e70843ab79d19dddf6d197505ad810adbf4126d12172cee1712f51.
Before launch client/server HEAD and11implementation/protocol/methodology SHA256s
matched. At16:10:42UTC, first null-arm wrapper2748515/client2748516 was alive and
its actual fresh64-file CTAS had started. Parent:0passed/0failed/5unattempted,
model_fit_performedFalse. Live SQL collector is being validated by this genuine
first episode; no completed physical/audit/model result yet.

Root results/sf10_models_20261026_02; launch log
results/sf10_models_20261026_02_launch/campaign.log; actual working evidence
/home/ccbd/capstone_three_model_evidence/sf10_models_20261026_02.
Same SF10 source and immutable snapshot references; existing services/tables
untouched. Fresh lineitem per arm, original full-row/raw-task/host/publication/
queue gates retained. First training pair must pass matching and ≥10real eligible
A/B rows before the other4arms/fitting; this engineering floor is not statistical
sufficiency. A source/preparation/telemetry/layout/support failure stops dependencies
and alerts, with no favorable retry or made-up labels.

After collection/export gates: shared/separate log-Ridge and histogram boosting
against3median baselines;22real pre-execution features. Train-only transforms,
fixed specs, no internal random early-stopping split, whole-family validation
selection before one-time test, no refit/test tuning. Unsupported predictions
remain None and common-support scores can be missing. No C forecast, calibration,
causal maintenance penalty, SF100 admission or scheduler-benefit acceptance.

Estimated first pair60–120minutes; six arms plus exact audits4–6hours, uncertain.
No new episode27Oct07:30IST/no new SQL09:30IST; active calls finish naturally.
Failure alerts use the authorized ntfy topic. Next useful check around22:30–23:30IST
for the first arm, then the training-pair support gate.

## Transport and fallback

Worker3 lacks unattended GitHub HTTPS credentials. No tokens/deploy keys copied.
Local ops/sync_relay.py performs only transport: ff-only Git, raw checksum mirror,
HEAD/methodology SHA proof, acknowledgement and authenticated push with existing
laptop setup. Remote computational jobs remain under nohup and never get cancelled;
subsequent units wait for acknowledgement+GitHub commit. Laptop sleep/disconnection
or divergence may pause progress between units and alert; this is explicit rather
than claiming autonomous server push. Relay launch metadata/status are saved under
results/sf10_models_20261026_02_relay_launch and
results/sf10_models_20261026_02_sync_relay. PID to be read from actual launch JSON;
relay not claimed alive before its launch. Old source/preflight/failure and fresh
preflight/launch small evidence mirrored; live/future raw is not fully mirrored yet.

Actual transport relay started16:12:15UTC21:42:15IST, local PID85134, nohup log
results/sf10_models_20261026_02_relay_launch/relay.log and launch.json. This is
transport only, not a local scientific run. At16:12UTC the remote first arm had
completed CTAS and was persisting real1s host counters during305s warmup. No query
outcome, completed episode, A/B support or trained model is claimed yet. Relay
actual first Git/raw synchronization remains to be observed; its launch is not
proof of future credential availability or a complete future raw mirror.

First actual transport roundtrip observed16:13:33UTC21:43:33IST: PID85134 alive,
statussynced, HEADf932ee57121b4fc1b6397304d82128263cd07a2a, checksum differencesFalse;
remote client_sync_f932ee57121b4fc1b6397304d82128263cd07a2a.json exists. This
supersedes the earlier unobserved-launch note for this snapshot only. Current
canonical metadata is mirrored; active home working evidence and future completed
packages remain pending. No scientific acceptance follows from transport success.
Parent2748173/child2748516 alive,0passed/0failed/5unattempted, modelFalse; real
305s host warmup in progress. No new code/config edits while physical work runs.

First actual replay clock recorded16:16:47.533279UTC21:46:47IST after real host
warmup. Raw statement_completed records observed for all six query IDs0–5,
including2/3/5table joins, followed by further cycles. Example first query UUID
 eb38c47b48e848ada980dcbbb28e10e4 and first supply-join UUID
 d4cdfa6571ab405c91c278b627d04e4b. This confirms actual client execution and live
plan/capture integration, not yet exact terminal raw/result acceptance, usable
A/B support or fitted-model accuracy. First300s offered-history records remain
ineligible for fitting. Complete episode audit/export and matched support gates
remain pending; no frozen source/config changed during this observation.
