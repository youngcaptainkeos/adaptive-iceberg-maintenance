# SF10 matched collection and model comparison — 26 October 2026

Implement the user-authorized comparison, without choosing architecture from
insufficient data or manufacturing pending-state examples. Existing firstfit
and all historical tests remain frozen. Typed SF10 capability passed separately;
it is not a trained cost model.

## Registered pipeline and gates

1. **Preflight on worker3:** source/AST/input digests, actual12saved SF10 SQL and
   typed result reconstructions through the new multi-table contract; estimator
   constructors only. No dummy data, model fitting or SQL. This does not validate
   the new live collector or prove a model beats another.
2. **One matched training pair:** fresh lineitem tables, same actual SF10 source
   rows/64file fragmentation, no maintenance vs real compaction at600s.1200s
   genuine Snowset arrivals, six custom SQL mappings,1query client. Preserve exact
   spacing and all queued/completed/failed/residual IDs; no thinning or full-drain
   claim. Seven other benchmark tables use immutable verified snapshots.
3. **Independent raw/publication/plan export:** exact typed references, original
   raw host windows/2s freshness and gaps/95%coverage, direct pending state, actual
   task evidence, exact snapshots and full-row initial/final comparisons. Matched
   initial per-file row/byte distributions must agree. First300s offered histories
   remain missing and excluded. Cached metadata describes the intervention table;
   supply-only SQL does not scan it and must not be described as doing so.
4. **Support gate:** require at least10eligible real A and10B rows in the training
   pair before spending on dependent pairs/fitting. This is only an engineering
   floor(2×registered minleaf5), not independent sample-size/statistical adequacy.
   If insufficient, stop with actual support counts and ntfy; no favorable retry.
5. **Registered chronological families:** original cohort training days0/1/2,
   origin+3600s,1200s per window and300s expanded dependency bounds. Roles are
   train/validation/test; paired arms stay in the same family. Check no overlap
   with known consumed intervals. Same warehouse/one family per split remains
   exploratory, not independent-dataset or replicated causal evidence. Original
   forecast calibration partition untouched.
6. **Fit only on train:** shared and separate A/B log-target Ridge and histogram
   gradient boosting, plus query/query-layout/query-layout-state medians. Same
   frozen per-estimator settings; no search or row-based early stopping. Query ID
   categorical; train-only scaling.22actual features=existing14+8plan counts.
   Separate models have higher total capacity; acknowledge it.
7. **Validation then one-time test:** select by equal-episode MAE on common support,
   freeze selection before test predictions, never refit/tune from test outcomes.
   All seven comparators and unsupported coverage reported. Missing/OOD predictions
   remain None, zero common support gives missing score/selection, never fallback.

## Implementation structure

- `runtime/sf10_collect.py`: explicit fork of the proven capture collector;
  historical collector unchanged. Keeps original queue/host/metadata/engine/task/
  boundary/publication gates. Uses explicit SF10 source proof, six multi-table SQL,
  independent typed results and actual pre-execution plan capture.
- `runtime/sf10_contract.py`: exact snapshot SQL, decimal-safe results, actual
  FORMATTED/COST capture before feature publication; no hand-weighted complexity.
- `runtime/sf10_observation.py`: explicit multi-table SQL binding; original exact
  metadata/window checks retained, including maintenance-only freshness gate.
- `preparation/sf10_candidates.py`: reconstruct raw/publication/plans and join
  actual pre-execution features; no post-query outcomes in X or invented histories.
- `training/sf10_comparison.py`: shared/separate models and medians, whole families,
  train-only preprocessing, one-time validation selection/test, coverage and artifacts.
- `experiments/sf10_campaign.py`: detached sequential source/mapping audits,
  isolated collection, checksum archive/export, support gate and comparison.
  Any failure stops dependent work; failed/unattempted counts retained.

## Operational registration

Protocols `sf10_models_preflight_20261026.json` and
`sf10_models_campaign_20261026.json` freeze all named settings and sources.
No new episode after27Oct02UTC07:30IST; no new SQL after04UTC09:30IST; inflight
operations finish naturally. Estimated six-arm campaign4–6hours after launch,
uncertain; preflight roughly1minute.3parent locks plus child physical lock;
inspect both Spark apps for idle work. Existing persistent10001/UI4050 data-disk
scratch backend, original10000/UI4040 retained. No services/tables deleted,
restarted or cancelled. Systemdisk evidence has8GiB initial/2GiB per-arm floor,
100GiB datafs and8GiB MemAvailable floors; four fit threads. Floors are budgets,
not peak guarantees. Retain working originals and checksum canonical archives;
laptop mirror acceptance remains separate.

First physical pair may fail or reveal inadequate A support. That is an observed
result, not authorization to relax gates or repeatedly run until favorable.
A completed comparison is exploratory: no calibration, causal maintenance penalty,
SF100 admission, scheduler deployment or publication-readiness claim. Subsequent
research needs more independent training/calibration/test blocks, resource/scale
variation and physically tested scheduling benefit against declared baselines.
