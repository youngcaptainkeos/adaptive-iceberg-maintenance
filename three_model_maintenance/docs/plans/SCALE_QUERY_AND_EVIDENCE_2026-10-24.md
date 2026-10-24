# Scale, query structure and evidence improvement plan

User authorizes SF10 testing, SF100 as the larger-scale target and systematic
repair of previously identified scientific shortcomings. Do not equate this first
capability unit with completion of the research programme.

## Current evidence and scope

The22October first fit used335rows/one known family:16A all16files,319B all1file.
It is exploratory, layout/state-confounded, and has no heldout accuracy result.
Models and old source/evidence/schema remain frozen; no retroactive plan features,
original-Snowflake-SQL attribution, test reuse or runtime/calibration promotion.

Read-only worker3 admission inventory24October13:58UTC: RAM67249111040bytes,
available46943571968, canonicaldatafree465042763776, homefree22474706944.
No active Main/queue Python collector/trainer found. Existing dbgen binarySHA
`03b46c1f9196fe4f24fdc3ba4bf47dad104cca75a0b4de4d2aec7950985d29f2`,
distsSHA `4dc56300de1e5ac5e1900519794538e2b5d1b6caf5cd55703bf53000dd748876`.
SF10 absent. ExistingSF100typed-source audit is historical field-format evidence,
not full relational/Iceberg/capacity admission. Both data/home disks are localext4;
large directory name does not prove NFS. No services/configuration restarted.

## Unit1: actual SF10 capability pipeline — implement and launch

New isolated `experiments/scale_query.py`, `preparation/query_plan.py` and protocol
`sf10_plan_capability_20261024.json`; leave existing SF1 live collector untouched.
Parent/eachstage worker3nohup/unique failure wrappers; stop at firstfailure, retain
partial files/tables and unattempted stages. Full sourceAST/hash and generator/
distribution/schema provenance checked before work. Acquire all shared experiment
locks; no new operation after18:30UTC24Oct (00:00IST25Oct), inflight natural finish.

1. Resource admission: observe availableRAM/datafree, Spark environment and no
   running Spark jobs. Floor16GiBavailable,100GiBdatafree; registered operational
   budgets, not guaranteed future allocations.8GBDuckDBmemory/4threads reserves
   headroom; no runtime-prediction constants. Currentengine3.3.4/local16 retained.
2. Run existing proper TPC-H generator with `-s 10`, fresh dataset path, noforce/
   overwrite. Pin binary/distribution digests, retain generator log, full-fileSHA.
   Recorded binary provenance does not claim independent compiler certification.
3. DuckDBfull-field typed/lexical/null/terminator checks, all primary keys and8FK
   relations; exact known scale cardinalities for7tables, measured lineitem count.
   Build typed reference tables on disk and run all6registered query references.
   No approximate lineitem count or sampled source substitute.
4. Spark typed ingestion all8fresh Iceberg tables; count/null/physicalmetadata and
   bidirectional EXCEPTALL full-row multiset validation for every table.64lineitem
   files are an explicit controlled-fragmentation intervention, not natural ingest.
  100GiBbudget covers~11GBraw+typedDB+Iceberg+substantialspillmargin, not peakproof.
5. Capture `EXPLAIN FORMATTED` and `COST`, persist raw plans/feature receipts before
   each actual query, bind exact SQLhash/all snapshot IDs/layouts and actual RPC
   clocks. Sixcustomqueries: filteredrevenue, groupedscan,2tablejoin,3tablejoin,
   high-cardinality grouping+sort,5tablesupply/geographyjoin. SQLsemantics/dates/
   TOP20 are registered benchmark inputs, not predictions. Compare each result
   exactly with independently executed DuckDBreferences. Repeat after actual useful
   lineitemrewrite; require fewerfiles/new snapshot/unchanged full-row multiset.
6. Reconstruct operator features from persisted raw plans, bind them to actual
   EXPLAIN and query calls, check availability before RPC and cross-engine results.
   This is12closed-loop capability queries, no real-arrival replay or A labels.

Plan features: node count, scan/join/aggregate/exchange/sort/filter/window counts;
these are measured properties, not hand-weighted complexity. Zero means absent
only after the physical plan parses successfully. Unknown operators remain named
in raw operator inventory; unparseable/no-supported-scan plans fail admission.
COST statistics are raw text, numeric rows/bytes stayNone/unvalidated: no enormous
optimizerdefault interpreted as true bytes, no fabricated zeros/estimatedruntime.
No actual postquery task/shuffle/spill/AQE outcomes become pre-query predictors.
The raw plan/receipt are fsynced before observing availability; planning overhead
and actual query client intervals remain separate in the append-only event log.

Output `results/three_model_sf10_plan_capability_20261024_01/`;
dataset `datasets/tpch/sf10_generated_20261024_01/`;
tables `local.experiment.integrity_sf10_20261024_01_<table>`.
Firstcheck~10minutes, provisionaltotal45–120minutes dominated by real generation,
full scans/joins/multisets/spills; not a promise. Terminal ntfy only says capability,
not accepted training/SF100/scheduler. No table deletion/physical retry onfailure.
Full database files remain server-side during run; mirror terminal evidence and
record actual source/warehouse sizes before larger collection or data backup.

## Unit2: genuine matched-layout trace collection — gate on Unit1 success

Extend a separate versioned collector to the new query registry and references;
do not silently replace the current4querySF1contract. Use actual Snowset arrival
windows with complete source/expanded-history audit and preserved spacing/IDs.
Register a1200s horizon and maintenance at600s rather than current600/300: after
first300s observed histories, this provides a genuine pre-maintenance window for
B-on-fragmented-layout queries. This duration is a proposed collection parameter,
not a guarantee of A support, a statistical sample size or a changed age limit.
Retain all missing first300s histories, queued/deferred/failed IDs and residualdebt;
no trace thinning/compression to hide overload. Register fresh tables/identities,
source-overlap families and cohort roles BEFORE outcomes; check consumed history
across both cost and demand work before choosing independent heldout windows.

Capture plans per exact SQL/snapshot/schema/planningconfiguration, bind availability
before querydecision, measure overhead/cache validity. Keep mutablehost/directstate
features under original2sage/gap,95%coverage and exact receipt bounds. Any snapshot-
static plan reuse needs an explicit new contract, not relaxed host freshness.
Original-frame B/A on the SAME eligible fragmented layout is the first scientific
support gate, not merely both condition counts. Task overlap stays diagnostic and
is not substituted for direct pending-state observation. Never synthesizeA if the
maintenance interval yields none. Replication/precision target from development
block variability must precede heldout evaluation; queries/ticks are not blocks.

## Unit3: query-aware comparison — gate on bound new corpus

Keep old14feature artifacts frozen. Introduce a versioned plan-feature training
schema and independently re-audit all new predictors/targets/availability. Current
models require knownqueryIDs/jointcells; simply adding plan counts does not enable
unseen-template prediction. Implement an explicit plan-aware candidate that uses
queryID only for grouping/evaluation, not as its only query representation, with
registered support/OOD policy and preserved refusals. Compare against queryID and
SQL/layout medians, simple plan regression, shared state-conditioned model and
separateA/B under identical whole-source/episode splits and declared budgets.
Hold out complete query templates/scale shifts for generalization; old median
methods must report unsupported unknownIDs rather than quietly substitute values.
Record separate-model parametercount differences, prediction coverage and all
negative results. No winner from trainingerror or reused old test.

## Unit4: SF100/resource generalization — gate on measured SF10 admission

Measure full raw/reference/warehouse/spill footprint, query/maintenance elapsed
work and actual Spark memory/resources. Verify existingSF100generator/relational
provenance and actual catalog admission, fresh isolated tables and storage margins.
Do not infer100xruntime or assumeSF100 exceeds availablecache. No OS cache flush,
service restart or fabricatedcoldcache claim; register measured cache/resource
conditions and a second feasible resource/environment setting. Multiple scales
alone do not demonstrate larger-than-memory behaviour. Expand querycoverage toward
full official22queryTPC-H where supported, with reference checks and explicit
SQLdialect adaptations;6customqueries cannot be called an officialTPC-Hscore.

## Unit5: forecast-aware scheduling and publication evidence

Arrival forecasting C remains separate from service/rewrite cost estimates. Real
Snowset arrivals provide no originalSQL: any mixture assignment is a registered
controlled benchmark mapping, not recovered real query-complexity demand. A fixed
round-robin mix cannot substantiate forecasting real SQLmix. Register transparent
workload-mix sensitivity or acquire trace SQL/fingerprints; preserve limitations.
Train rewrite duration/layout transitions from actual useful rewrites, not A-B.
Use independent calibration blocks with justified uncertainty/precision targets;
finite conformal rank alone is not statistical power. Compare actual scheduling
against no-maintenance, declared reactive and persistence/forecast variants over
common horizons including residualqueue and maintenance debt, without inventing
an SLA/scalar penalty. Query plan features are prior art; novelty requires evidence
of forecast-aware Iceberg timing benefit and failure regimes, not three models or
a new hand-written complexityscore. These gates remain open after Unit1.

Primary implementation references: Spark3.3.4 EXPLAIN and CSV documentation,
https://archive.apache.org/dist/spark/docs/3.3.4/sql-ref-syntax-qry-explain.html
https://archive.apache.org/dist/spark/docs/3.3.4/sql-data-sources-csv.html
Existing generator README/DSS_PATH/DSS_CONFIG semantics frozen in provenance.

## Resource coordination supersession before any SF10 launch

VPN dropped during intended worker3 sync; SSH exit255 before remote shell, noSF10
run or data generated. User confirmed restoredVPN. Actual24Oct14:26UTCqueue
parent2017935/firstphysical2018081 active, four-arm ABBA storage study running under
shared locks. CanonicalHEAD8d504a0; no01SF10output directory. The other chat's
published documentation included this plan's original methodology section once;
retain it without duplicate append. No messaging authorization inferred from its
coordination messages; read actual server processes/status instead.

Register fresh02prospective source/table/output paths in
`sf10_plan_capability_after_queue_20261024.json`; original01 remains unattempted.
New `experiments/deferred_scale.py` and
`sf10_deferred_after_queue_20261024.json` wait on server without experiment locks,
SQL, generation, dataset scans or fitting. Startup only checks real committed code
AST/source/generator/config digests. Poll prerequisite terminal metadata every60s
on persistenthome; no periodic notifications or physical-operation polling.

Require exact queueprotocolSHA, terminalstatuscompleted,4passed/0failed/0unattempted
and unchanged independentrawaudit result. Negative performance contrasts do NOT
block SF10: this gate concerns experiment integrity/resource release, not favourable
results. Probe sharedlocks, then let SF10parent acquire them independently. A race
fails before physicalwork rather than competing. Queue failure/auditmissing or
latestlaunch00:30UTC25Oct (06:00IST) stops with ntfy and SF10unattempted. SF10no-new-
operation cutoff03:00UTC25Oct (08:30IST); active operations finish naturally. These
new prospective cutoffs do not extend any running SF10operation. Queue's expected
end~19:55UTC24Oct01:25IST25Oct is an estimate only, not a launch timer.

Waitreceipt/progress `/home/ccbd/capstone_three_model_evidence/sf10_deferred_20261024_02/`;
SF10terminal root `results/three_model_sf10_plan_capability_20261024_02/` and fresh
`datasets/tpch/sf10_generated_20261024_02/`. Parent/child failure wrappers retain
original status/logs and unique ntfy receipts. Capability completion notification
comes from the SF10pipeline after all six stages, not from mere waiting/startup.
No existing service/process/table, activequeuecode/protocol or SF1fit is modified.
