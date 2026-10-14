# Overnight learned-cost implementation queue —2026-10-15

Authorized2026-10-14 by user to work autonomously until06:00IST on2026-10-15
(2026-10-15T00:30:00Z). Existing same-chat15-minute heartbeat updated, no duplicate.
Read clock first each wake. At/after deadline stop work and pause automation;
leave all services/in-flight work running. No new physical episode after04:45IST;
no new Spark/SQL/maintenance operation after05:15IST. Reserve last45minutes for
read-only audit/mirror/documentation/sync; save morning review before06:00.

## Starting evidence

Seven successful physical arms yielded489query rows,4rewrite rows, one connected
source-time family, no fully observed300-second offered history. Candidate export
and independent raw round trip passed, not calibrated training. Prior longer
cohort remains1passed/1failed/7unattempted. Boundary preparation v1is implemented
and compilation/passed-arm regression passed; real opt-in branch still needs
registered recovery. No cost model accepted or scheduler deployed. No active
Spark/own physical run at overnight starting inspection.

## Larger job queue, with dependency gates

1. **Reliable diverse collection.** Register fresh tables and the boundary contract,
   full-window actual source arrivals and named initial layout candidates. Use
   immutable worker3 execution checkout/source so future trainer code edits cannot
   mutate active experiments. Keep six matched groups (three disjoint source-time
   windows × two initial physical file counts), all three arms per group, rotated
   order,18episodes maximum for first matrix. Original data/cases remain preserved.
   Initial layouts are controlled real repartitions of verified source rows,
   not natural ingestion or fabricated file-growth. Named16/32file candidates are
   baseline source count and two waves of existinglocal[16]parallelism, not policy
   predictions; actual row/byte layout measured and matched within each group.
2. **Demand-history exposure.** Register10-minute actual source windows:300seconds
   to expose real offered history plus300seconds to observe full-history query
   features. Count all600seconds in episode/debt outcomes; no free excluded work,
   time compression, thinning or fake warmup demand. The separate305-second host
   history warmup remains. Source-day indices0/1/2 use first nonempty complete
   windows before outcomes; one warehouse/custom SQL mix remains a limitation.
3. **Audit then export.** Every arm/raw audit passes before next; stop on failed
   gate, inspect and repair, never blind retry until desirable. Preserve failures,
   no-ops, unattempted counts and occupied tables. Re-audit matched groups; mirror
   complete raw packages/hashes, include all attempt inventories. Update candidate
   export/readiness using only successful complete packages, missing values intact.
4. **Exploratory new-schema trainer.** Implement shared and separate query latency
   estimators, per-query training-median and simple regression baselines, and a
   distinct measured rewrite-duration model. Predeclare features/parameters/seed,
   source-family/whole-episode chronological split and train-only preprocessing.
   No original query IDs/arm/outcomes/task-overlap in X. Use fully observed demand
   histories only when they exist; report excluded rows, never impute. Produce
   per-query/state/layout/episode metrics and saved actual predictions. No automatic
   winner or deployment. Mark bundle uncalibrated/diagnostic/no scheduler permission.
5. **Acceptance audit and next collection.** If data/fitting gates fail, report and
   repair or register necessary diversity, rather than inventing labels. Three
   source families are not enough for independent90%conformal calibration; refuse
   promotion. Register independent calibration/test and precision requirements
   when justified by observed evidence. Prioritize scientific blockers, not more
   identical pilots. No SF100physical run before unresolved provenance gates.
6. **Fallback and morning handover.** During no active physical query/rewrite,
   preserve needed new table bytes with unchanged-source hash checks and raw/code/
   model artifacts. Absolute metadata paths mean byte fallback is not a portable
   local catalog. Final review distinguishes done/running/failed/unvalidated,
   records hashes/log/PID/state, negative results, what to inspect next and limits.

## Dynamic audit rules

A repeated cutoff/logger/SQL/cache/schema/split issue takes priority over dependent
collection or fit. Do not weaken actual timing/freshness/row/task gates. No fabricated
CPU/intensity/small-file counts, fixed uncertainty, artificial data, counterfactual
penalty or post-hocSLA. All validation/model/physical runs on worker3 detached.
Avoid concurrent physical arms or heavy model fitting/backup during query windows.
Source/code/config must be immutable for active run. Compare layouts within named
matched groups; across groups intentionally different source/layout is metadata.

After each major job append methodology working ledger and updated-master pointer,
update this queue and overnight review. Targeted commit/push, worker3fast-forward,
HEAD/intended SHA256checks; preserve unrelated dirty/untracked archive/stashes.
Notify only meaningful completion/failure/human action and morning handover.
The local app/computer and campus/VPN connection must remain available for heartbeat
execution; detached server jobs persist across SSH disconnects. No promise of
calibration/publication just because overnight time is available.

## Dynamic priority at14:55UTC

Initial18matrix stopped0passed/1failed/17unattempted on task-retention retrieval.
Repair archive-first actual successful task-frame selection and validate raw
checkpoint/historical successful arm before fresh recovery IDs/runtime launch.
Do not upgrade failed original or use its497diagnostic rows for fitting. Trainer
implemented8de48a6, server syntax checked; actual fit still blocked by diversity.

Recovery registration: sf1_overnight_recovery_cohort_20261015.json and18fresh arms.
Inspect actual checkpoint diagnostic before immutable launch; original failed
matrix preserved. Historical raw adapter regression passed, no activeSpark15:10UTC.

Trainer reporting audit adds paired held-out UUID comparisons and failed-fit receipts.
Do not equate implementation/syntax with real fit validation. Recovery active15:25UTC;
next dependent export/fit still gated on completed raw physical evidence.

15:40UTC recovery01passed physical+frozen raw audit;1478offered/497completed/981queued.
Recovery02active; keep runtime immutable. Small receipts mirrored; full raw export/
mirror/fitting after collector inactive. No calibrated model or scheduler accepted.

15:55UTC priority: recovery02failed final rewrite-task retention;1passed/1failed/
16unattempted preserved. Repair completed maintenance archival in uniform midpoint,
validate actual historical active arm, then fresh immutable recovery registration.
No active collector; do not fit one-family dataset or upgrade failed arm.

Recovery2fresh18matrix registered; actual saved compaction checkpoint validation
then immutable launch. No physical/Spark activity16:10UTC. Keep all original
failed inventories; live midpoint maintenance path must pass actual raw audit.

16:40UTC priority freshness repair: recovery2failed0/1/17. Actual sampleage2.179s
versus strict2s. Validate serialized preparation path/error accounting and register
fresh cohort before any restart; no weakened age gate or failed labels.

Recovery3registered after lock-order/pre-dispatch audit; syntax/rawregression gate
then immutable launch. Same strict2s age/no-padding/task/results/layout gates.

17:25UTC recovery3baselinepassed strictfreshness/physical/raw;compact_now02running.
Submission repair validated once; maintenance/32file/cohort/model gates still pending.
Small receipts mirrored; avoid heavy fit/backup while collector active.

17:40UTC recovery3now02passed live maintenance archival and strict raw/physical;
deferred03running. Onefamily/layout not independent modeldata yet. No heavyfit.

17:55UTC first matched16filegroup3passed,32file04active. Near-equalfinalcounts are
negative evidence for claiming a winner, not precision/power proof. Continue
registered diverse collection; independent sourcefamily fit gates pending.

18:15UTC recovery3stopped3/1/14 onfreshsampleavailability. Register/export verified
three-arm group, retainallfailedinventories; independentfit still blocked. Diagnose
availability/wait contract before fresh physical unit; no blind identicalretry.

Recovery4remaining12episodes registered forsource1/2layouts16/32; retain already
passedsource0group. Real-sample availabilitywait (not gap/age relaxation) needs
syntax/rawregression then livevalidation. Newexportroundtrippassed772full300shistory
rows butonefamilystillblocksfit. Mirrorpackage onceinactive before fit.

Recovery4PID1285378launched remaining12source1/2episodes at00:11IST. Firstcheck
00:30IST; inspectactiveprogress before nextwork. Fullrawmirror/export/fitting after
collectorinactive; maintaincutoffs and frozenruntime. Prior groups/failures retained.

Recovery5fresh11registered; independentcounterreader/durablepublish pipeline addresses
actualsamplingstall withoutweakenedgates. Source2first thenremaining source1arms.
Passedsource0group/source1now retained, allfailuresunchanged. Regressionthenlaunch.

19:55UTC source2firstarmpassed/liveindependentsamplingvalidatedonce. Threefamilies
nowavailableinprinciple; aftercollectorstops exportallacceptedepisodes plusallfailed
inventories, rawroundtrip thenpreregisteractualhashes/familysplit andexploratoryfit.

20:25UTC recovery5stopped2/1/8 onlockedfreshness. Prioritize threefamily sixepisode
export+independentroundtrip+registeredexploratoryfit now; no blindretry.16fileonly/
incompletegroups/instrumentversionconfounding explicit. Physicalrepair remainsgate.

Threefamilyrawroundtrippassed, actualhashfirstfitregistered. Runworker3nohupfit,
retainfailedattempt/negativepredictions, independentoutputaudit beforeclaims. No
calibration/promotion; datasetlimited4rewrites/16fileoriginal layout/confounding.

Firstfitfinished butnegativeheldoutlatencyresults. Independentsavedpredictionaudit
nowimplemented; runnohup thenreportrawnegativebaselinecomparison/mirror. No
heldouttuning, promotion or scheduleruse; independentcollectionplan next.

Independentmodelauditpassed, negativeaccuracypreserved; no schedulerapproval. Verify
sixsuccessfulrawpackage mirror, preservephysicalbytes/catalogreferences duringidle,
then address lockacquisitionfreshness race/futureindependentcollectionregistration.
No heldouttuning/refit toclaimaccuracy; newmodel comparisonneedsfuturetestblocks.

Sixsuccessfulrawpackages144files mirrored/hashverified, candidate20/model6already
verified. No physicaltablebytefallbackyet. Next lockacquisitionavailabilityrepair
with unsubmitteddeferral/strictgates, orphysicalbytepreservationwhileidle; noheldoutrefit.
