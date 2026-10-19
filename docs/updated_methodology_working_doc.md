# Methodology & Master Working Document
## Learned, Uncertainty-Aware Scheduling for Lakehouse Storage Maintenance

**Status:** Living Master Document. Updated September 30, 2026.  
**Audience:** Peer Researchers, Advisors, and Project Collaborators.

---

## 1. Executive Summary & Research Question

### 1.1 Core Research Question
> **Given that lakehouse storage maintenance (e.g., Apache Iceberg `rewrite_data_files` compaction) must be performed, *when* should it be executed to maximize storage efficiency while minimizing interference with concurrent analytical query workloads?**

### 1.2 Key Differentiation
- **What this project IS:** A dynamic, uncertainty-aware timing and scheduling decision engine.
- **What this project IS NOT:** A new compaction algorithm or table-layout optimizer.
- **Novelty:** Existing work (e.g., AutoComp, Smart Compaction, PTO, Karim et al. 2026) determines *what* or *whether* to compact, or optimizes layout statically. None model maintenance interference penalty as an explicit function of **concurrent workload state**, and none provide **calibrated, distribution-free uncertainty bounds (conformal prediction)** to trigger fallback mechanisms when predictions are unreliable.

### 1.3 Decision Space
At any evaluation timestep, the scheduling agent outputs:
- `NOW`: Execute maintenance immediately (workload interference is low).
- `DEFER`: Postpone maintenance to a predicted lower-interference window.
- `FORCED_OVERRIDE`: Execute maintenance despite high predicted interference due to **starvation protection** (preventing indefinite storage degradation).

---

## 2. Comprehensive Progress Summary (Phases 0 through 5)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PROJECT TIMELINE                               │
└─────────────────────────────────────────────────────────────────────────┘
  Phase 0-2: Baseline & Layout Characterization          [COMPLETE & VALIDATED]
    ├── Spark 3.3.4 + Iceberg 1.4.3 setup
    ├── Noise-floor baseline (CV = 3.25%)
    └── Task-level telemetry proof of parallelism vs overhead
  
  Phase 3A-3B: Interference Measurement & Point-in-Time ML [AUDITED & REBUILT]
    ├── 528 query + 44 compaction physical trials
    ├── Rigorous audit: fixed scaling leakage & timestamp leakage
    └── Out-of-Distribution (OOD) test: proved point-in-time models fail 
        under heavy fragmentation (MAE 117%, conformal coverage collapse)
  
  Phase 4: Temporal Workload Modeling & 4-Hour Run       [AUDITED & REMEDIATED]
    ├── Built 1Hz telemetry collector & 5-regime NHPP query generator
    ├── 4.13-hour continuous physical experiment executed
    ├── Director's Audit: caught stochastic compaction bug (13s active) 
        and conformal training contamination
    └── Fixes verified via 15-min mini-experiment: 6 compaction events,
        true conformal math confirmed (25% coverage on short sequence)
  
  Phase 3C-3F Audit & Phase 5 Architecture               [DESIGNED & READY]
    ├── Audited 34 legacy scripts: uncovered hardcoded offsets & path errors
    └── Designed clean Phase 5 scaffold: 8 policy suite, dynamic conformal
        calibration, and bounded starvation protection
```

---

## 3. Detailed Phase Accomplishments & Scientific Insights

### Phase 0 – 2: Environment & Physical Layout Characterization
- **Infrastructure Standardization:** Standardized on Apache Spark 3.3.4 and Apache Iceberg 1.4.3 runtime over TPC-H SF1/SF10 benchmarks.
- **Statistical Hardening (Phases 2F–2I):** Established a 20-repetition noise floor (workload coefficient of variation = 3.25%). Applied Shapiro-Wilk normality testing, Wilcoxon signed-rank tests, and Holm-Bonferroni corrections.
- **Mechanistic Task-Level Verification (Phase 2J):** Proved using Spark task telemetry that file compaction improves performance primarily by eliminating task launch and serialization overhead rather than raw I/O throughput gains.

### Phase 3A & 3B: Concurrent Interference & Point-in-Time Modeling Audit
- **Interference Metric:** Defined Query Interference Ratio:
  $$\text{QIR (\%)} = \frac{\text{Duration}_{\text{treatment}} - \text{Duration}_{\text{control}}}{\text{Duration}_{\text{control}}} \times 100$$
- **Phase 3B Remediation:** Audited the initial ML pipeline and fixed two critical flaws:
  1. *Scaling Leakage:* Moved `StandardScaler` strictly inside cross-validation folds (`GroupKFold` by configuration).
  2. *Timestamp Leakage:* Excluded monotonic timestamps (`client_start_time_concurrent`) that allowed models to memorize execution order.
- **OOD Extrapolation Proof:** Tested trained point-in-time models on severe fragmentation regimes (`frag100`, `frag350`, `frag750`). Point-in-time MAE spiked to **117.74%**, and conformal coverage dropped from $95\%$ to **$24.60\%$**. This provided empirical proof that point-in-time snapshots are insufficient for dynamic environments, mandating Phase 4 temporal modeling.

### Phase 4: Temporal Workload Infrastructure & Experiment Audit
- **Telemetry & Workload Generator:** Built `unified_telemetry_collector.py` (sampling CPU, Memory, Disk I/O, and Spark REST API metrics at 1Hz) and `workload_generator.py` (simulating Non-Homogeneous Poisson Process query arrival across LOW, MODERATE, HIGH, BURST, and RECOVERY regimes).
- **Physical Continuous Run (4.13 Hours):** Executed a continuous trace generating 14,867 telemetry rows and 778 successful queries.
- **Director's Audit & Vulnerability Discovery:**
  - *Bug 1 (Stochastic Compaction Bug):* Compaction scheduling recalculated random intervals every 0.5s inside a sleep loop, causing compaction to execute for only **13 seconds** across 4.13 hours (0.09% of runtime).
  - *Bug 2 (Conformal Data Contamination):* RidgeCV was fit on `Train + Validation` combined, then conformal $\hat{q}$ was calculated on `Validation`, violating split-conformal exchangeability.
  - *Bug 3 (Trivial 100% Coverage):* The 100% coverage claim was an artifact of an extremely wide interval ($\pm 375.50$ ms on an $85.75$ ms mean target) accompanied by negative $R^2$.
- **Remediation & 15-Minute Vindication:**
  - Fixed compaction scheduling to use deterministic countdown timers.
  - Fixed conformal splitting (`RidgeCV` fit strictly on `Train`).
  - Added baseline regressors (`DummyRegressor`, `LinearRegression`, `RandomForestRegressor`).
  - Verified via a 15-minute mini-run: generated **6 real compaction events**, conformal offset dropped to a realistic $19.26$ ms, and conformal coverage correctly fell to $25.00\%$, proving that short sequences fail to capture non-stationary temporal dynamics.

### Phase 3C–3F Pipeline Audit & Phase 5 Architecture
A comprehensive code audit of 34 legacy scripts in `scripts/phase3c` through `phase3f` revealed:
1. **28 out of 34 scripts** contained stale workspace path references.
2. **Zero scripts** loaded the clean Phase 3B `best_regressor.joblib`, repeatedly re-implementing a flawed hand-rolled `SimpleTreeRegressor`.
3. The nonconformity score `+8.5%` was hardcoded as a constant across 10+ files.
4. Phase 3F audit scripts synthesized predictions directly from ground-truth labels (`qir + random.gauss(0, 3.0)`).

**Decision:** Supercede the Phase 3C–3F scripts by creating a fresh, modular **Phase 5 Adaptive Scheduling Agent** framework.

---

## 4. Phase 5 Architecture: The Adaptive Scheduling Agent

The newly designed `scripts/phase5-adaptive-scheduling-agent/` framework decouples scheduling policy evaluation from ML training:

```
scripts/phase5-adaptive-scheduling-agent/
├── agent/
│   ├── scheduling_agent.py          # Core decision engine
│   ├── conformal_predictor.py       # Dynamic conformal quantile computation
│   └── state_tracker.py             # Tracks maintenance debt & deferral streaks
├── policies/
│   ├── policy_interface.py          # Abstract Base Class for all policies
│   ├── always_run.py / always_defer.py / random_policy.py / cron_policy.py
│   ├── heuristic_policy.py          # Resource threshold fallback
│   ├── point_prediction_policy.py   # Sklearn mean prediction policy
│   ├── conformal_risk_policy.py     # Dynamic Conformal Upper Bound vs SLA
│   └── temporal_conformal_policy.py # Temporal model + Conformal policy
├── evaluation/
│   ├── offline_evaluator.py         # Trace replay harness
│   └── metrics.py                   # SLA violations, completion %, starvation
└── config/
    └── agent_config.yaml            # SLA thresholds, risk budgets (alpha)
```

### Core Guardrails Built Into Phase 5:
1. **Zero Hardcoded Offsets:** Conformal bounds ($\hat{q}$) are computed dynamically at runtime from calibration residuals.
2. **Bounded Starvation Protection:** Mandatory tracking of consecutive deferrals (`max_consecutive_deferrals = 3`) to force maintenance before storage health degrades irreversibly.
3. **Multi-Policy Comparison Suite:** Evaluates 8 distinct policies side-by-side to quantify the exact Pareto frontier of SLA protection vs. maintenance completion.

---

## 5. Immediate Execution Roadmap

| Step | Action Item | Target Window | Objective |
|------|-------------|---------------|-----------|
| **1** | Build Phase 5 Scaffold | Day (Pre-Run) | Execute Prompts 1–5 to build clean policy & evaluator harness |
| **2** | 4–8 Hour Physical Experiment | Night | Run continuous physical workload trace with fixed compaction scheduling |
| **3** | Temporal Model Training | Day + 1 | Train RidgeCV & Random Forest models on clean 4-hour dataset; verify $R^2 > 0$ |
| **4** | Offline Policy Evaluation | Day + 1 | Replay 4-hour dataset through Phase 5 offline evaluator across all 8 policies |
| **5** | Paper Write-Up | Day + 2 | Draft Methods, Audit Results, and Policy Pareto Evaluation for paper submission |

---

## 6. Final Evaluation Results (Phase 5)

The final offline evaluation of the 8-policy suite was conducted on the 4-hour chronological test dataset using dynamically calibrated, data-driven thresholds (SLA threshold = 492.48 ms, derived from the 90th percentile of the training target). The dynamic conformal quantile ($\hat{q}$) was successfully computed as 244.37 ms on the strict validation split.

### Final Policy Comparison

| Policy | Completion Rate | SLA Violation Rate | Mean Observed Target | Deferral Rate | Forced Override Rate | Starvation Events |
|--------|-----------------|--------------------|----------------------|---------------|----------------------|-------------------|
| `AlwaysRun` | 100.00% | 0.00% | 99.44 ms | 0.00% | 0.00% | 0 |
| `AlwaysDefer` | 0.00% | 0.00% | 0.00 ms | 100.00% | 0.00% | 0 |
| `PointPrediction` | 100.00% | 0.00% | 99.44 ms | 0.00% | 0.00% | 0 |
| **`ConformalRisk`** | **83.23%** | **0.00%** | **93.34 ms** | 16.76% | 0.00% | 12 |
| **`TemporalConformal`** | **87.00%** | **0.00%** | **94.77 ms** | 12.99% | **4.50%** | 83 |

### Key Scientific Conclusions
1. **Conformal Uncertainty Enables Safe Deferrals:** With the data-driven SLA threshold, the `ConformalRiskPolicy` successfully identified periods of high uncertainty and safely deferred 16.76% of the time. When it did execute, it achieved the lowest mean interference cost (93.34 ms vs 99.44 ms baseline), proving it successfully schedules during the quietest periods.
2. **Effective Starvation Protection:** The `TemporalConformal` policy safely forced execution (4.50% override rate) to break unacceptable starvation streaks, lifting the completion rate from 83.23% to 87.00% without compromising the mean interference cost significantly (94.77 ms).
3. **Data-Driven Calibration is Mandatory:** The transition from Phase 3 to Phase 5 proved that hardcoded heuristic thresholds and static conformal offsets break down entirely under out-of-distribution or non-stationary workloads. The success of Phase 5 strictly relies on dynamic, data-driven calibration.

---

## 7. Project Artifacts & Key Documents

- **Master Methodology Document:** [updated_methodology_working_doc.md](file:///home/shashank/.gemini/antigravity/brain/5e14b653-0a3b-4484-b6b2-f8b697861d3b/updated_methodology_working_doc.md)
- **Director's Audit Report (Phase 4):** [phase4_audit_report.md](file:///home/shashank/.gemini/antigravity/brain/5e14b653-0a3b-4484-b6b2-f8b697861d3b/phase4_audit_report.md)
- **Phase 3C-3F Audit & Phase 5 Architecture:** [phase3cf_audit_and_phase5_design.md](file:///home/shashank/.gemini/antigravity/brain/5e14b653-0a3b-4484-b6b2-f8b697861d3b/phase3cf_audit_and_phase5_design.md)
- **Phase 5 Execution Prompts:** [phase5_execution_prompts.md](file:///home/shashank/.gemini/antigravity/brain/5e14b653-0a3b-4484-b6b2-f8b697861d3b/phase5_execution_prompts.md)

---

## 8. Current append-only methodology reconciliation —2026-10-14

The current continuing evidence ledger is `docs/methodology_working_doc.md`,
Section12, appended without rewriting historical text. Its2026-10-14evidence
corrections supersede incompatible success/novelty/safety claims in this master
snapshot. Historical Phase5tables/conclusions above are not accepted evidence for
a calibrated deployed scheduler under the current raw physical contracts. In
particular no universal novelty exclusion, distribution-free safety or fixed-SLA
policy benefit is asserted from the current audited artifacts.

Current verified pipeline: actual Spark/Iceberg execute/fetch clocks and raw task
attribution; exact available60/300-second telemetry; fresh pre-action state;
source/snapshot/files/full-multiset/query-result conservation; dedicated client
sessions; SHA-pinned actual Snowset arrivals mapped explicitly to custom benchmark
SQL; offer/queue/dispatch/outcome accounting and common-horizon residual debt.
Alibaba/Borg are not original database SQL replay implementations. SF100 raw
lineitem count is600,037,902, with remaining generator/relational/large-table gates.

Four order pilots and four null controls passed raw integrity audits; controls
show31–73ms middle-query variation without maintenance. One-minute queue screen
retained113arrivals with41in-horizon completions,1natural completion afterward and
71queued. Six three-arm common-horizon episodes passed; none41/39, now41/37,
later41/39in-horizon completions show no robust throughput winner. Five-minute
source mappings718/762/744passed; larger9-arm collection stopped after1passed,
1boundary-bookkeeping failure,7unattempted. Original failures are preserved, and
boundary preparation repair awaits real registered recovery. Services/tables remain.

No learned cost model or calibrated temporal scheduler is accepted. Separate A/B
and opt-in shared candidate code exists; fitting waits for raw-verified candidate
export and sufficiently diverse independent collection. The complete next milestone
and gates are in `docs/learned_cost_model_implementation_plan.md`: measured query/
rewrite/episode export, collection matrix, exploratory comparison, chronological
independent calibration/test, then held-out physical forecast/policy benefit.
Model count is an empirical choice; learned future demand must improve scheduling.

For paper writing use the append-only working ledger, current raw reviews and
frozen protocol/code/source hashes. Append purpose/pipeline change/evidence/failure/
limitations after every major job; preserve earlier prose as history. Unsupported
older tables must not be promoted to current Results. This file keeps a synchronized
append-only summary/pointer; the working ledger records detailed job history.

### 8.1 Major job: cost-candidate pipeline implemented —2026-10-14

Appended detailed Job13to the continuing methodology ledger. A preregistered raw-
verified exporter now separates query service targets, rewrite duration/work and
whole-episode debt, with a strict pre-query predictor allowlist and retained
failed/unattempted inventory. Incomplete offered histories remain missing; future
engine overlap and arm/outcome fields cannot enter predictors. Export completion
will be logged after worker3's detached real-artifact run. This is candidate data,
not accepted calibrated training or a deployed learned scheduler.

### 8.2 Major job: verified candidate export completed —2026-10-14

Working ledger Job14records detached worker3 export and independent raw CSV
verification:489actual query observations,4real rewrites,7successful episodes,
with failed/unattempted inventory. Current corpus has1overlapping source-time
family and0fully observed300-second offered-demand rows; incomplete demand remains
missing. These are candidate engineering data, not independent calibrated training
or accepted scheduler evidence. Full export/frozen dependency/proof package mirrored
and hashes matched. Next collection must add disjoint windows/diverse physical
state and correct history exposure; next trainer compares separate/shared costs
under explicit exploratory and later held-out gates. No synthetic labels or fit.

### 8.3 Persistent append workflow

Root `AGENTS.md` now records the user's standing requirement to append methodology
after every major job, alongside real-data/server-validation and preservation /
Git-integrity practices. Detailed record is in the continuing working ledger.

### 8.4 Overnight end-to-end milestone authorized —2026-10-14/15

Working ledger Job15records new user authorization until06:00IST tomorrow,
updated existing automation and audit-driven18-arm diverse collection / actual
demand-history / exploratory estimator queue. Execution and morning ledgers are
`overnight_execution_plan_2026-10-15.md` / `overnight_review_2026-10-15.md`.
No success or calibration claim follows from authorization. Services/failed data
are preserved, and append-only evidence gates continue after every major job.

### 8.5 Overnight diversity collector implementation

Working ledger Job16records explicit real layout candidates, within-group strict
matching, ten-minute actual offered-history exposure, server compilation and
historical raw regression. New paths await registered physical execution; active
collector will use an immutable checkout separate from later model development.

### 8.6 Raw engine retention support

Working ledger Job17records actual stage-count motivation, in-run preservation of
raw completed tasks and actual-frame merging for longer episodes, with strict
final gates and uniform instrumentation limitations. No engine restart/fake history.

### 8.7 Registered overnight cost matrix

Working ledger Job18records18fresh real arms, three audited600-second source
windows, two controlled layouts, equal within-group conditions and immutable
runtime plan. New paths require live raw audit; no calibration/policy claim.

### 8.8 Immutable overnight matrix launched

Working ledger Job19records18planned real arms launched on worker3 under nohup
PID1031940 at20:07:27IST, frozen detached code/config checkout, identical intended
file hashes and canonical source/results links. First baseline running, outcomes
unestablished. Fifteen-minute audit/repair automation continues to06:00ISTOct15;
no simultaneous heavy fitting, fabricated labels or automatic calibration claims.

2026-10-14 evening: canonical working methodology Section20 records new exploratory
candidate-schema shared/separate latency and rewrite-duration trainer, chronological
whole-source-family gates, training-only processing, missing-history exclusions
and explicit no-promotion outputs. Preregistration appended to learned-cost plan.
Implementation pending real fit; immutable18episode physical collection continues.

2026-10-14 evening Section21: first overnight baseline failed Spark UI task-retention
retrieval;0passed/1failed/17unattempted preserved. Implemented raw complete-frame
adapter for archived tasks; real regression validation pending. No promotion/retry
of occupied tables. Next fresh registered recovery after evidence checks.

Section22 registers fresh18episode recovery after identified task archive reader
bug; same scientific matrix/gates, original failed/unattempted inventory unchanged.
Historical raw regression passed; checkpoint diagnostic receipt awaiting inspection.

Recovery launch confirmedPID1068198 at15:12UTC, immutable8a11a71runtime. Actual
checkpoint247queries/741tasks verified; all23registration filesSHA256 agree. No
recovery arm or learned model accepted yet; see Section22 launch evidence.

Section23 trainer audit adds matched shared/separate UUID comparisons, family error
groups, artifact hashes and durable failed-fit receipts. Implementation only; no
model accuracy/calibration claim; physical recovery runtime remains immutable.

Section24 first recovery ten-minute baseline passed physical+raw gates:1478offered,
497completed,981queued,125.599992ms boundary observation lateness retained. Second
arm running; receipt hashes mirrored. One family is not train/test or calibration.

Section25 recovery compaction arm failed missing archived rewrite tasks:1passed/
1failed/16unattempted preserved. Uniform midpoint checkpoint extended to completed
maintenance calls with existing strict raw task attribution; validation pending.

Section26 saved real compaction-task checkpoint validation and recovery2 fresh
matrix registration; same source/layout/gates/cutoffs, failed counts unchanged.
Saved-evidence check is not live-path/model approval; real collection gate next.

Recovery2actual launchPID1130786, immutabledd4ebf5runtime;23registeredfileSHA match.
Saved real query+maintenance checkpoint passed; live collection/fitting pending.

Section27 recovery2failed actual2s freshness (2.179098077s sample age);0/1/17retained.
Opt-in serialized durable pre-submission preparation implemented without relaxing
raw gates; validation/new protocol needed. Logging contention suspected, not proved.

Section28 fixes submission/ledger lock inversion before physical use, preserves
pre-dispatch failure states, registers fresh recovery3same strict matrix/gates.
Instrumentation scheduling change remains explicit limitation; live validation next.

Recovery3nohupPID1177256 confirmed, immutablec93f13f/all26unitSHA agree. Historical
raw regression passed; firstlive serialized path validation still pending.

Section29 recovery3baselinepassed actual strict freshness/raw audit:1478offered,
506ultimatelycompleted/972queued; boundary observer lateness73.220066ms retained.
Compaction02running. Receipts mirrored; no whole-cohort/model approval yet.

Section30 recovery3compact_now passed live maintenance archive/physical/raw gates;
1478offered/509finalcompleted/969queued. Deferred03running. No causal benefit or
model approval from small count contrast; one family/layout remains limited.

Section31 first matched source_day_0/files16three-arm group passed; finalcompleted
506/509/509, no winner/causal claim.32file collection started, remaining sourcefamily
and fitting gates pending.03result/audit receipts mirrored with matchingSHA.

Section32 recovery3stopped3passed/1failed/14unattempted on missingfreshtelemetry.
Successful3arm export registered with all failure inventories; no32file acceptance
or independent fit/calibration claim. Sampler diagnosis/availability repair next.

Real3arm candidate export nohupPID1261960 launched; nextcheck5min/rawroundtrip.

Section33 new1524query/2rewrite candidates independently verified,772full300s
historyrows/onefamily. Real-durable-sample wait implemented; fresh12episode remaining
source1/2matrixregistered, retaining passedsource0group. No fit/calibration yet.

Section34 recovery4remaining12source1/2episodes launchednohupPID1285378 inimmutable
0b05393runtime. Firstcheck00:30IST, estimated03:30–04:15ISTsubjectgates. No fityet.

Section35 actual2.5286s samplinggap/recovery4state1/1/10preserved. Independent real
counterreader/FIFOdurablewriter implemented, onlyfsyncedfeatures, gatesunchanged.
Fresh11recovery5 prioritizessource2, keepsalreadyacceptedsource0/1episodes.

Recovery5launchPID1334649confirmed, immutable95a5548/19unitSHAagree. Historical
source1rawregressionpassed, liveindependentsamplingneedsaudit. Firstcheck01:20IST.

Section36 third disjointsourcefamily/liveindependentsamplingpassed.01source2later
1501offered/528finalcompleted/973queued; baseline02running. Threefamilies enable
possibleexploratorysplit afterexport, not calibrated/acceptedmodels. Receiptsmirrored.

Section37 recovery5stopped2/1/8 onlock-acquisition telemetry freshness; allfailures
preserved. Sixsuccessfulthree-family exportregistered;16fileonly/versionconfounding
explicit. Prioritize independentroundtrip/exploratoryfit, no modelpromotion.

ThreefamilyexportPID1396241nohup launched; nextcheck5min/independentroundtrip.

Section38 threefamily3103query/4rewrite export independentlyrawverified/mirrored;
actualhashchronological fitregistered (train0/1,test2,alpha1,realhistoryonly).
Exploratoryfit pending; no calibration/modelpromotion/generalizationclaim.

FirstexploratoryfitnohupPID1411927launched; full20candidatefileSHA agreeincluding
verification. Actualoutcomeaudit next, no acceptedmodel/calibrationclaim.

Section39 firstfitcompleted withsevereheldoutbaselineerror/negativependingpredictions,
not acceptedmodel. Independentread-only savedprediction auditimplemented, runnext.
No test-outcome tuning or calibrationclaim; rewriteoneheldoutrow insufficient.

IndependentfitroundtripnohupPID1427023launched; no modelpromotionpendingaudit.

Section40 independentfitroundtrip passed butlatencymodels failmedianbaselines;
no schedulerapproval/calibration. Fitbundle6files mirroredSHA-identical; sixraw
packagecopy underway. Learnedcostplan records next independentcollection gates.

Section41 all144rawfilesfrom6successfulpackages mirrored/SHAverified;20candidate/
6modelbundlefilesalreadyverified. Physicaltablebytes/portablecatalogfallback still
missing. Negativefit unchanged; submissionavailabilityrace repair remainsnextgate.

Section42 sampleexpiredafterlock acquisitionnowexplicitunsubmitteddeferral/release/
realwait opt-in; raw chronology/sourcebinding added, gatesunchanged. Livepathpending.

Section43 fresh32filethree-armdiagnosticregistered forlive layout/submissionpath,
allgates/cutoffsunchanged. Source2overlap notindependentfuturetest; no modelrefit.

32filematchedgroupnohupPID1486932alive, immutable1fa3d3d/8SHAagree. Firstcheck03:50,
fullestimate04:20–04:30ISTsubjectgates; no modeltuningor acceptedlivebranchyet.

Section44 complete32filethree-arm grouppassed, finalcompleted535/522/530 no policy
claim. Separate diagnosticexportregistered, no refit; branchcoveragecheckedseparately.

All332fileepisodes0deferrals/0waits: newdeferralbranch remainsunexercised, not
livevalidated. SeparatecandidateexportnohupPID1550562launched; rawroundtripnext.

Section45 separate32fileexport1587queries/2rewritescompleted/independentchecklaunched;
9successfultablebyteinventoryregistered, idle/read-only/actualrawpaths, noportability
or bytefallbacksuccessclaimbeforetransferverification.

ByteinventorynohupPID1565619launched; read-onlyactualhashmanifest beforetransfer.

Section46 actual9table/516file/2.486GB bytecopystarted (session81303), outcome/hash
verificationpending. Approvaltimeoutbeforefirstcommand, narrowerretry succeeded.
No portablecatalog/completebackupclaim yet; preservepartialcopy atcutoff.

Section47 tablecopyexit0, independentworker3local-vs-originalandunchangedsources
verificationnohupPID1595507launched.32raw/candidatecopy session95731stillpending.
No portablecatalogclaim; finalhashreceiptsrequiredbeforebackupapproval.

Section48 all9successful tablebytes516files/2.486GB copiedandunchangedsourcesSHA
verified; final32evidence117filesverified. Concisemorningsummary saved
morning_review_2026-10-15.md, no calibratedmodel/policyclaim. Pauseautomationat06:00.

Section49 new user-authorized detachedread-only failure/scaling/coverage/pipeline
versionauditregistered; realSHA-bound negativefit, no refit/SQL/promotion. Freeze
worker3runtime/nohup, actualreceiptandfindings next; unexercisedbranchstillunvalidated.

Section50 detachedfailure/pipelineauditcompleted onworker3, training-onlyscalers
reconstruct,3instrumentationversions/sparseconditional-rewriteblocks documented.
7reportfiles mirroredSHA-identical; concise cost_failure_audit_summary_2026-10-15.md.
No SQL/refit/promotion, alreadyfinished beforelaptopclosure; automationstaypaused.

Section51 new userauthorized detached18episode consistentcoveragepilot registered,
newsource3/4development/5futuretest, realmappingaudits/frozenruntime/strictgates/
stoponfailure/candidateexport/handover, no automaticmodel fit. New boundeddaytime
cutoffs, pilotnotpowerclaim. Modelcomparisonprospectivelyregistered forlaterreview.

Section52 actualdetachedPID1804667/PPID1launch08:33IST, frozenea2b6e6/8SHAagree,
sourcepreparationrunning. Estimated5–6h/gated, laptopcancloseaftersuccessfulsetup.
Handover/checkcommand saved; no automaticfit or offline-localmirrorpromise.

Section53 server sourceaudits/disjointness/18actualhashregistrationspassed beforeSQL;
physicalcollectionrunningnohupPID1804667/PPID1, laptopcanclose. Executionmanifest
mirrored/SHAverified; no acceptednewrawepisode/modelclaim. Reviewserverhandoverlater.

Section54 latestdetachedreview:1passed/1failed/16unattempted, stopped09:07IST.
Actualcall67.927msafterhorizon despitepre-horizondispatch; failedarmpreserved/export
skipped. Detachedorchestratorworkedbutcollectionfailed; no automaticrestart/modelchange.

Section55 userauthorizedntfyfailurealerts implemented/defaultfuturetestwrapper and
runnerhooks, no retries/statusweakening. Worker3idle. Verifyonactualexistingfailure,
not dummyexecution; persist HTTPresponse andsync intendedfiles.

Section56 actualfailedrunalert deliveredntfyHTTP200/eventoqZkPibiuhmG; codeparsedon
worker3nohup, no dummytest. Futurewrapper/hooks configured; no projectrunsactive.


2026-10-16: Actual RPC deadline guard and real-evidence regression registered; see canonical methodology and rpc_guard_regression_20261016.json. Historical batch remains 1/1/16; validation and live branch pending.

2026-10-16: Conditional fresh guarded18cell collection registered with preserved failures/source-family overlap and16:30/17:00IST cutoffs; no automatic fits. See detached_consistent_collection_20261016.json.

2026-10-16: Real archive regression passed4accepted/1correct rejection; resultSHA 90c74f1a447ae349aad6da5182311a64251e6e0e7f8d582ba5c48043032bf7a8. New live branch pending.

2026-10-16 09:43IST: Guarded18episode collection launched detached, wrapper3213486/PPID1 coordinator3213487, frozen3fa7e52; source preparation running. See canonical methodology; firstcheck20–30min, total5–6h estimate, no automatic fits.


## Consistent cost development fit registration — 2026-10-17

Completed Oct16 corpus18/18passed,9923query/12rewrite labels, independent raw roundtrip verified. Register consistent_cost_development_20261017.json before fitting: source families0train/1validation/2reserved untouched; wholeepisodes, complete60/300s demand history for query comparison. Four latency candidates: querymedian,query/layoutmedian with learned SQL fallback, compact logRidge alpha1 and depth3 absolute-error tree seed20261015. Predecision features only SQL/filecount/clientpending. Rewrite extension uses filecount only with trainingmedian/logRidge/tree; only4train/4validation labels anticipated, insufficient for accuracy claims. Training-only transforms and same validation rows. Save models, predictions, excluded UUIDs and row/equalepisode/sliced MAE. No automatic winner/refit/test/promotion, all negative outcomes preserved. Script/protocol committed before server nohup fitting; raw input hashes verified at runtime. Laptop repository mount unavailable, temporary checkout cloning; authoritative code change made on server preserving unrelated dirty files. New unsubmitted live-guard branch did not occur in18episodes and remains unverified.


## Consistent development fit observed results — 2026-10-17

Worker3 nohup wrapper3662879, revision055f001091502db7e69593b52cbdd340320a32b3, fit10:05:27UTC (15:35IST), completed; log results/consistent_cost_development_20261017_launch.log. Real raw-verified corpus; query train1591/validation1672 after complete history eligibility; third family3351query rows reserved, not evaluated (includes early rows not yet filtered for future test). Rewrite4train/4validation/4reserved. Equalepisode query MAEms: SQLmedian20.3197, SQL/layoutmedian19.0400, logRidge21.1091, shallowtree20.1904. Simple layout baseline best on development; no learned-model win claim. Rewrite median440.6151/logRidge387.3421/tree383.9604ms, only4validation labels, no accuracy claim. Negative old model results remain history. No winner refit, test evaluation, calibration or scheduler promotion.

Detached saved-prediction audit wrapper3663160 checked real target identity, uniqueness, validation-only membership, artifact SHA and reconstructed row/equalepisode errors. Source archived scripts/phase6-live-evaluation/audit_consistent_fit_20261017.py; runtime source /tmp/audit_consistent_fit_20261017.py; log results/consistent_cost_development_20261017_prediction_audit.log. Does not independently reconstruct fitted transforms. Raw receipt and saved models/predictions/exclusion UUIDs/audit mirrored to temporary client checkout because original laptop mount unavailable. Fit receiptSHA e00e08ca3938e4668b9dfd897d532e43d49d7af4247da077992f871566e01de0.

Next gate: inspect training/validation regime support and freeze development choice/protocol before one reserved whole-family evaluation. Only one train and one validation source family; no independent calibration. More independent blocks and substantially more rewrite/overlap evidence needed. Completed18/18physical collection is engineering success, not forecast-aware scheduler acceptance.


2026-10-17 15:47IST: User authorizes scheduled implementation until18:00IST. Registered docs/execution_plan_until_1800_2026-10-17.md and evidence ledger execution_review_until_1800_2026-10-17.md: independent development audit, freeze evaluation, one reserved-family test, research-resource plan, final report. Stages gated; no new physical work or test-directed tuning. Prior AGENTS instructions revoked. Deadline12:30UTC; preserve services, pause scheduling at cutoff.


2026-10-17 15:59IST Queue A: register independent reconstruction audit before worker3 execution, consistent_development_audit_20261017.json. SHA-bound real saved fit/models/predictions/protocol; independent design/scaling and NumPy logRidge solve, empiricalmedians, deterministic tree reconstruction, targets/metrics/eligibility. Inventory development-only slices including zero pending states. Tree uses same sklearn implementation, not independent algorithm. No reserved-family evaluation or new physical operations. Outcome pending.


2026-10-17 Queue A first reconstruction passed all6700predictions and raw training/scaling/closed-form Ridge/medians/tree/metrics checks. Actual pending-True support22eligible train/25validation, not zero. Found an erroneous fixed limitation sentence claiming zero support; first receipt retained, explicitly superseded by measured coverage. Register v2 output/report with corrected limitation only; no gate/input/model changes or fitting. This is a reporting repair, not retrying a failed model. Excluded3309development queries due incomplete histories. Auditwrapper3669334. Gate A waits corrected report; reserved family still untouched.


2026-10-17 Queue A complete: corrected independent reconstruction report passed, wrapper3669781, revisiond9b01fc. Receipt results/consistent_development_audit_20261017_v2/result.json SHA256 1e1f059fb7360fbd733f345fea0f6287c9c03bc78c025eb64f8c686ffaad2f87 mirrored. Registered input/artifact hashes, training-only transforms/closed-form logRidge/empiricalmedians/tree predictions and all6700saved predictions reconstructed;3309development queries excluded by unchanged history eligibility.22train/25validation eligible pendingTrue queries, from dependent episodes, limited support. Query layouts1/16/32 all represented. Reserved-family predictions absent. First audit report retained with incorrect fixed zero-support sentence explicitly superseded. Queue B now ready; no reserved test run/output exists. Next scheduled turn freeze model/code/protocol before single evaluation. No new physical work.


2026-10-17 Queue B freeze: consistent_reserved_evaluation_20261017.json SHA-binds original family0trained model bundle, fit receipt, passed independent audit, source export and evaluation code before test. Primary query/layoutmedian selected by development equalepisodeMAE; all preregistered candidates reported, rewrite primary median with sparse evidence. Same complete60/300s histories, one family2evaluation, no refit/search/winner selection after test. Output results/consistent_reserved_evaluation_20261017 exclusive; code saves protocol/source/predictions/metrics/eligibility and preserves failures. Queue C permitted only after protocol published/synced.


2026-10-17 Queue C one-time evaluation executed under frozenedec1a6, wrapper3672206, no refit.1663eligible reserved queries (3351total),4rewrites. Equalepisode MAEms query/layoutmedian20.3430, SQLmedian21.2335, tree20.9283, logRidge21.5426; simple primary still best. Rewrite median274.8958/logRidge258.2338/tree263.5033 on4labels only. No learned-query win or established rewrite accuracy. Test family now consumed; no posttest tuning. Registered read-only independent audit of saved target/model/metric binding before advancing C. Raw result/predictions/code/protocol mirrored locally. Audit outcome pending.


2026-10-17 Queue C complete: independent saved-test audit passed6664predictions, 1688excluded test-query IDs; wrapper3672653, revision80f18b8. ReceiptSHA a40b1a5fbbb2bb53b3507d684e984f611be420817bc62358366b9538bfdd2f32, evaluationreceiptSHA c0fbd8cbda0d509e5f41bb6711693850a1911a80e0b4cc341ae26496efc009a4. Verified raw targets/family/eligibility, frozen model inference, reconstructed medians/fallbacks and all row/equalepisode/sliced errors. No refitting or second model selection. Query primary median remains lowest heldout equalepisodeMAE20.3430ms; learned alternatives do not beat it on this family. Four rewrite test labels insufficient for reliability. Artifacts mirrored and hashes checked. B/C finished ahead of target windows; dependency gates, not clock slots, governed advancement. Next D resource/independent-evidence protocol and final review. No services stopped or tables deleted.


2026-10-17 Queue D research/resource assessment completed: docs/next_independent_evidence_protocol_2026-10-17.md. Existing compact models contain no forecast features; complete history is eligibility only. Whole-horizon objective, debt/censoring, independent blocks, rewrite/overlap support, larger-table provenance, resource setting and calibration remain gates. Source-day6 candidate not yet verified; forecast partition roles cannot be silently repurposed. Server snapshot445GiB storage/44GiB availableRAM; no new physical launches. Register completed_evidence_manifest_20261017.json to hash completed18arm/source/model/test archives before mirror; new physical table bytes/catalog excluded explicitly.


## Final review — 17 October 2026,16:29IST

A–E queue complete ahead of18:00deadline, after gated audits rather than waiting for target windows. Independent development reconstruction passed6700saved predictions (corrected report preserves first inaccurate limitation sentence as history). Frozen primary selected on development before test; single reserved family evaluation completed1663eligible queries/4rewrites without refit. Independent heldout audit passed6664prediction rows and1688excludedqueryIDs. Query/layoutmedian20.3430ms equalepisode heldoutMAE, tree20.9283, SQLmedian21.2335, logRidge21.5426; learned query models do not beat strong baseline on this family. Rewrite median274.8958/logRidge258.2338/tree263.5033ms, only4testlabels, exploratory. Test family consumed; future tuning needs new untouched physical-cost families. No model calibrated/accepted, no scheduler or temporal-demand benefit established. No new physical collection or service/table changes.

Completed evidence manifest workerwrapper3675259,808files/714774503bytes, SHA b9e945b96f9b4524df253f8e0ba3a71086e71fc4c7f4689b2fcee07a9ffe13f6. SCPsession71592 exited0. Every copied file path/size/SHA matched locally,0mismatches; local byte comparison is a transport-integrity check, not scientific model validation. Client verification results/completed_evidence_client_verification_20261017.json SHA 73e27d1142fd0618ce34a0089cc0b3bdf3e07f72506ccbbe50f67e8869722462 copied to worker3; raw/source/fit/test/audit archives all in /tmp/capstone_training_20261017/results and original server results. Original client mount remains unavailable: temporary copy is NOT a verified persistent mounted fallback. New18Iceberg table bytes/catalog portability not backed up in this package. Previous physical table fallbacks cover earlier tables only. Final server inspection showed no projectPythonjobs and Spark runningjobs empty; services remain intact.

Next work: restore persistent client mount and move/verify fallback; settle whole-horizon objective/debt/censoring; preregister independent source blocks, stronger rewrite/interference coverage, verified scale/resources and temporal ablations. See docs/next_independent_evidence_protocol_2026-10-17.md. No invented sample-size/power guarantee or publication readiness. All intended code/docs commits pushed and repositories fast-forwarded, unrelated dirty files preserved. Pause existing heartbeat now because all ready work finished; final pause confirmation follows.


## Literature-based novelty audit — 2026-10-17

User requests proper primary-literature analysis. Saved docs/novelty_comparison_2026-10-17.md with linked section/page evidence, access limitations and rejected claims. AutoComp4.4 explicitly discusses offpeak deferral; NoisePage section3/thesis4.4/chapter5 already combine forecasts/interference/planning; SOPHIA4.3 and6 noisyforecasts cover future-horizon reconfiguration tradeoffs. Corrected prior imprecise Pareto description: weightedscore is implemented, frontier discussion futurework. SmartCompaction structuralutility is not economic/query objective. PTO main PDF inaccessible; authorabstract/appendix read, missing timingcapabilities remainunknown. Existing episode CSV shows958–1056queued of1526–1610offered,62.8–65.9percent backlog: future arrivalquietness is not serveridleness. No scientific runs, fits or new test use. Recommendation: freeze decisionobjective and small real physical timing-headroom protocol before newlargecollection; detailed mechanism must beat strong generic forecastcostplanner, not merely a fixedschedule. Novelty remainsunestablished; automation remainspaused. Originaldriveabsent, temporaryclientcheckout used.


## Queue-aware maintenance feasibility initiated — 19October2026

User authorizes full PoC/feasibility implementation by20Oct06:00IST, substantial real remote runs, new isolated source folder and ntfy updates. Created queue_aware_maintenance with study requirements, explicit accounting/cutoff/support gates and copied SHA-bound legacy instrumentation (old files unchanged). Original local drive available again; local fast-forwardedfc6211d→f0f506e and remote caughtupf0f506e, unrelated dirt preserved. Server inspected idle, no Pythonjobs/Sparkjobs. First automatic SSH approval review timedout; narrower retry succeeded (not safety rejection). Registered input_audit_20261019.json for real prior9923query/12rewrite candidates and chronological day6source capacity; no SQLrun yet. Proposed two20minsourcewindows×4physical policies+drain, conditional on observed support/capacity. Current cost family2now consumeddevelopment, not future blindtest. Client-pending empirical labels observational, simulator estimates not causal physical labels. No acceptedmodel or provennovelty assumed. Next gate: server audit source/support, implement full-drain runner and controller, preregister objectives/parameters before physicalwork.


2026-10-19 Input audit first attempt preservedfailed: Python3.10 datetime.fromisoformat rejects actualsource UTCZ. All20query/layout/pendingcells observed (no missing coreconditionalcells); source capacity audit notcompleted. Failurewrapper195609, receiptHTTP200ntfyj0XaFFRqnpKI. New explicit UTCparseracceptsZ onlyas+00:00, rejectsnonUTC; repairregistration input_audit_20261019_utc_repair.json usesexclusiveoutput, unchangedinputhashes/sourcewindows. No physicaloperations. InitialGitHubpush01c2f68 remainslive; exactcommit transferredSSHbundle and fast-forwardedworker3 withmatchingSHAs forread-onlyaudit, publicationpending, notdeclaredsyncedGitHub. Added unvalidated costs/forecast/simulator: empiricalconditionals, measuredbusyclientturnaround, piecewiseexpectedwork model and past-onlyseasonalcounts. No counterfactualprediction usedasphysical label; modelacceptancependingserverrealtests.


2026-10-19 Corrected input auditpassed (wrapper196149,d57c466), actualprospective20minwindows3067/3211arrivals, day6beforeforecasttrainingend; all20conditionalcells supported,17–21pendingrowsperoriginalquery/layoutcell overprior18episodes. Initialfailurepreserved. Restored all808priorcompletedraw/source/model/testevidencefiles714774503bytes fromverifiedtemporaryclientcopy tooriginaldrive, exactmanifestSHA checks; see results/original_drive_restore_20261019.json. Bound core_preparation_20261019 protocol: allrealpriorcostfamiliesdevelopment, busy-clientturnaround, empiricalmodelroundtrip/independentmedians, causalseasonalforecast6pastdays×60sbins, fullreal20minFIFOrecurrence andallactionconservation. No freshphysicaltargetoracularlabels in model. InitialGitHubpushstilllivebut boundedHTTP1pushd57c466succeeded; local/remote01c2→d57c466syncSHAverified. Oldpendingpushmaylaterrejectnonfastforward; no experiment restart. Newcore remainsunvalidateduntilserverjobpasses.


2026-10-19 Core preparationpassed (wrapper197408,670d9ab), fiveactualdata checks including complete6278arrival FIFO/accounting and causal forecast reconstruction. ReceiptSHA0837a1e8b01ae18e23c11c593c3947ba2f87ca8411b4a4c1f4b8e3b9aef12b4d; artifacts mirrored. Estimated8arms30283.85seconds beforefinalauditoverhead; both empiricalforecastplanner and perfect-arrivalmodel diagnostic initiallychooseimmediate, not evidenceofphysicaltimingheadroom. No futurearrivals enterdeployablepolicy. Implementednew full-draincohortledger, causalclient-idledecisionpolicy, incrementalactualSparkarchive, physicalrunner/auditor andboundedserialorchestrator. Objectiveintegerarea underoutstandingrequests independentlyequals allscheduled-arrival-to-resulttimes; no censorshipsuccess. Strict2s/95pcttelemetry andactualqueryresults/task/multiset gates retained. Preprepareage restrictedtoexisting1scadence, stronger than2s actualsubmission; callback deferralsbeforeSQLintent recorded. Registerednewruntimepreflight beforeactualSQL. Next physicalprotocolmust bindpassedpreflight, all8freshidentities/orders/cutoffs beforefirstCREATE. OriginalunboundedGitHubpushfinallyfailedHTTP504; boundedHTTP1pushsucceeded andremotesynced670d9ab, nophysicalrunrestarted.


2026-10-19 Fullruntimepreflightpassed(wrapper200132,9ba219a), receiptSHA52fea0d3c47e63861bc7a2dbe135b00a06e3fadf0fe1d3792ad3a8019a0b5d3d. AllnewsourceAST/imports and8actualsource/policyinitialdecisionsverified, noSQL. Register physical_study_20261019.json:8freshfull-drainarms, chronologicaltwo20minwindows3067/3211querieseach×4policies (25112totalphysicalofferedqueriesifcomplete); queueaware/null/forecastquiet/immediate thenreverse. Same16filelayout/verified6millionrows/1client; allarrivalspacingandqueuedebtretained; exactsumresponseintegral, actualtasks/results/multiset/stricttelemetryaudits. No newepisodeafter03:45IST/noSQLafter05:15IST20Oct; noforcedprocessstop. Oneoptionalrewritebudget, no arbitrarySLA/cloudprice. Data/forecast/model/codeauditSHA-bound; all8protocolsmanifestbeforefirstCREATE. Physicscopeinstrumentedbenchmark, not novelty/powerproof. Orchestratorfrozenruntimependinglaunch; no physicalepisodecompletedyet.


### 2026-10-19: physical initialization failure and container repair registration
The eight-arm queue-aware cohort at revision 8f8c3ee stopped before any workload query: 0 passed, 1 failed, 7 unattempted. Preserved table local.experiment.queueaware_20261019_01 and raw events results/queue_aware_maintenance_20261019/cohort/episodes/queueaware_20261019_01/events.jsonl (SHA256 6e73850c42d19ad0266afb56bcc29db9cd19c2a40f8152a4e5623be9616f33ce). Actual recorded symmetric EXCEPT ALL count is zero. The runner incorrectly compared client tuple rows to JSON list rows. Repair checks exact one-row/one-column/zero value independent of row container; offline JSON audit remains unchanged. Registered read-only actual-table validation in queue_aware_maintenance/protocols/multiset_container_repair_20261019.json. No workload retry or table reuse is authorized by this validation. Next gate: actual client result verification, then fresh recovery identities under unchanged study design and cutoffs. Failure notification delivered; services preserved.


### 2026-10-19 13:32 UTC: actual read-only repair verification passed
Worker3 detached wrapper202742/child202743 ran the exact recorded symmetric multiset SQL against preserved snapshots. Actual Python result is list of tuple rows; legacy predicate false, corrected exact scalar/shape predicate true, count zero. Receipt results/queue_aware_maintenance_20261019/multiset_container_repair/result.json SHA256 73642eef95c9bcce01dd2906e5c30099cd730d2c0c100c7911a420df2a8692da, log results/queue_multiset_container_repair_20261019.log. No workload queries or writes. Local/GitHub/worker3 revision4399609 and runner/verifier hashes matched. Recovery orchestrator now requires this SHA-bound receipt for its exact runner and original cohort receipt (0/1/7), preventing accidental upgrade of the failure. Next: repeat actual-source runtime preflight then fresh eight-arm registration; no design/acceptance changes.


### 2026-10-19 13:33 UTC: fresh recovery physical registration
Actual-source runtime preflight at revision b27a539 passed all source parsing/imports and all eight policy/window initial decisions; receipt results/queue_aware_maintenance_20261019/runtime_preflight_container_repair/result.json SHA256 e937d74818a2149c0ebfa13a1cd0d621f4e9c97c2956db32095c76c771b84126. Registered physical_study_container_repair_20261019.json binds both this receipt and real read-only repair proof plus original failed cohort SHA20375d8ddf6a90f6b198d473ec027a7a36887c4a843ef4b776fcc03cb35dc9f2. Fresh eight tables queueaware_20261019_repair_01..08; same full3067/3211 arrivals, initial16files, all four policies, reversed second-window order and original cutoffs. Estimated collection8.4h plus auditing; no five-minute substitute. No temporal headroom/benefit claim from model-only initial immediate choices. Next gates actual full-drain episodes and independent raw/policy comparison.


### 2026-10-19 13:35 UTC: recovery launched and postcohort analysis implemented
Frozen recovery revision af274dba5fc59b0c2acc3892d8c46d34d144928b; wrapper203577/coordinator203578/first arm wrapper203582 live at13:34UTC. Initial physical table equality now passed; warmup ongoing, no completed arm claimed. Protocol SHA57a00d643553ad37f1493f218dcc849d4a91e8bb5b3310fa5e4553be30499b5b matched worker3. Implemented compare_study.py separately from frozen runtime: requires all8complete, independently reruns raw evidence audit, reconstructs queue inputs from actual past transitions, replays fixed model/forecast policies, verifies matched inputs and reports perwindow full-population response contrasts. No refitting, survivor comparisons, confidence/promotion claims. This source has not yet passed end-to-end physical validation; that gate awaits actual terminal cohort. Registered server-only actual-source preflight for added analysis sources. Updated active10min heartbeat and handover with real PIDs, cutoffs and incomplete requirements.
