# Repaired sample-frontier guard: regression and actual launch

Implementation revision `f6e9149064ad52d8e07c2288d209d09b6249bc28`.
Protocol `protocols/live_collection_repair_20261022.json` SHA256
`525e4396794ef9ace1c9cee5afa9efc50b744788e6fc681bfbf628c852128c9b`.

Actual detached worker3 launch22October2026 09:37:46UTC (15:07:46IST),
parentwrapper1258147/orchestrator1258148. Physical stage09:38:05UTC
(15:08:05IST), physicalwrapper1258244/collector1258245. No competing physical
job observed at launch; reservation locks acquired. Fresh table02 created;
real telemetry warming at09:39:32UTC checkpoint. Physical outcome pending.
Check approximately15:30–15:40IST; estimate20–30minutes, not a guarantee.

## Actual regression result

Stage09:37:46.267–09:37:46.773UTC passed on all297actual failed-run queries.
The repaired pure predicate rejects exactly7previously diagnosed stale IDs and
allows290actual fresh query-clock cases. No synthetic measurements, SQL or
training in regression; it does not establish counterfactual timing or repair the
old failure. Parser/import checks passed current collector/registered sources.
Result `results/three_model_frontier_regression_20261022/result.json` SHA256
`89b427d18e15e4572105575cfe51c4ff610f6be354ca8c0025a7fd7a783ff935`.

Mapping preparation passed09:37:57UTC and independent audit09:38:05UTC.
Actual recovery physical registration SHA256
`aa8ce335ef619cf8a4f912d144acec53c02c4ca4173e2f39ad0f29f23b8a0ff2`.
Completed regression and immutable physical registration mirrored locally with
hashes matching the recorded server receipts. Active raw files are not claimed
fully mirrored or accepted.

## What changed

Use actual prepared-window input sample endpoints at the real query call boundary,
not the time a window was recalculated. Wait for sample age<=1s before preparation
as registered headroom. Actual acceptance remains<=2s. After durable intent, stale
sample means no SQL; record a single terminal refusal and leave that request/rest
of offered FIFO queue intact. Existing original result/correctness/telemetry/engine
and executed-query gates remain, plus exact proof checks for the new no-SQL case.
No repeated physical attempt until favorable result, no labels for refused queries,
no workload thinning and no relaxed freshness threshold. See the registered plan
for the deliberate terminal-refusal limitation and lack of full-drain claims.

Parent results/three_model_live_collection_repair_20261022/progress.json and
physical.log; raw results/sf1_three_model_publication_20261022_02/events.jsonl,
feature_publication.jsonl and frozen source. Parent and each child stage use ntfy
failure wrapper; successful terminal measurement notification also configured.
Previous attempt01/failure/data retained. No current model fit, calibrated runtime
acceptance or independent test claim. Same known day6 development family; repeats
do not create independence. After terminal raw validation, export actual complete-
history A/B support and establish source-/receipt-bound training permission before
starting models. Do not recycle old consumed-test outcomes as fresh validation.
