# Execution Plan: Learned, Uncertainty-Aware Scheduler for Lakehouse Storage Maintenance

**Target:** PVLDB, February 2027 submission cycle
**Team:** Shashank Keshava Murthy, Shashank D, Prachi, Samarth
**Starting point:** August 2026, ~25 weeks to target

This plan turns the research plan into an actual sequence of setup steps, software
installs, dataset acquisitions, and checkpoints. It is organized so that each phase
produces a concrete, checkable artifact — not just "read papers" or "think about it."

---

## Phase 0 — Environment and Tooling Setup (Weeks 1–2)

### 0.1 Software you need to install

| Component | Version / notes | Why |
|---|---|---|
| **Apache Spark** | 3.3.x recommended (LST-Bench's default schemas target 3.3 or earlier; 3.4+ needs a regex patch — see 0.4) | Compute engine for all workload execution |
| **Apache Iceberg** | Iceberg-Spark runtime matching your Spark version (e.g. `iceberg-spark-runtime-3.3_2.12`) | Table format under test — this is the LST you're scheduling maintenance for |
| **Java (OpenJDK)** | 11 or 17, via Adoptium/Temurin | LST-Bench's Java module requires a JDK to build |
| **Maven** (via `./mvnw` wrapper, bundled with LST-Bench) | n/a | Builds LST-Bench |
| **Python** | 3.10+ | Forecaster, scheduler, ML pipeline, LST-Bench's metrics/analysis module |
| **DuckDB** | latest | LST-Bench's default telemetry sink for local/small-scale runs |
| **Docker** (optional but recommended) | latest | Containerize Spark+Iceberg+LST-Bench for reproducibility across team members |
| **Git** | — | Clone LST-Bench, CAB-gen, and your own repo |

### 0.2 Repositories to clone
```bash
git clone https://github.com/microsoft/lst-bench.git
git clone https://github.com/alexandervanrenen/cab.git         # CAB-gen (workload generator)
```
AutoComp's OpenHouse is **not required** — you're not deploying OpenHouse, only
reimplementing its MOOP ranking logic as a baseline in Python, which you'll write
yourselves from the formulas in §4.2–4.3 of the AutoComp paper.

### 0.3 Build LST-Bench
```bash
cd lst-bench
./mvnw package -Pspark-jdbc
```
This produces the JDBC-driver-bundled jar you'll use to run SQL workloads against
your Spark+Iceberg setup. Confirm the build succeeds and `launcher.sh` prints its
usage message before moving on — this is Gate 1 in miniature.

### 0.4 Known compatibility gotcha
If you use Spark 3.4+, LST-Bench's default schemas break on `SPARK-44025`. Fix:
add a regex replacement to your setup/setup_data_maintenance workload phases:
```yaml
replace_regex:
  - pattern: '(?i)varchar\(.*\)|char\(.*\)'
    replacement: 'string'
```
Document this in your own setup notes now so it doesn't cost you debugging time later.

### 0.5 Deliverable for Phase 0
A working local (or small cluster) Spark+Iceberg+LST-Bench pipeline that can run
a trivial workload end-to-end and write telemetry to DuckDB. This **is** Gate 1
from your milestone table — don't move on until this runs unattended.

---

## Phase 1 — Datasets (Weeks 1–3, overlaps with Phase 0)

You need two categorically different datasets: (a) data + queries to populate and
query Iceberg tables, and (b) a realistic concurrent-load signal to drive interference.

### 1.1 TPC-DS / TPC-H (data + query content)
- **Source:** standard TPC-DS/TPC-H `dbgen`/`dsdgen` tools, or via CAB-gen (below),
  which is already built on the TPC-H schema.
- **Role:** provides the actual table data and query templates that LST-Bench
  executes. This is the same benchmark AutoComp and PTO both use — reusing it
  keeps your evaluation directly comparable to both baselines.
- **Action:** confirm `dbgen`/`dsdgen` build cleanly, generate a small scale-factor
  dataset first (SF 1 or SF 10) to validate the pipeline before scaling up.

### 1.2 CAB-gen (workload stream generation)
- **Source:** `github.com/alexandervanrenen/cab` (already cloned in 0.2).
- **Role:** generates realistic query stream patterns (sinusoidal dashboards,
  interactive bursts, daily maintenance bursts, hourly predictable jobs) layered
  on top of the TPC-H schema — this is what AutoComp itself used for its synthetic
  evaluation, and LST-Bench has a built-in CAB-to-LST-Bench adapter (`adapters/cab-converter`
  in the LST-Bench repo), so integration is a solved problem, not something you
  need to build from scratch.

### 1.3 Alibaba cluster-trace-v2018 (concurrent-load / arrival-rate signal)
- **Source:** `github.com/alibaba/clusterdata` — download requires a short survey
  (link on the repo README), or a pre-processed mirror is available on Zenodo
  (search "Alibaba 2018 machine usage Zenodo" — includes `cpu_util_percent`,
  `mem_util_percent`, `net_in`, `net_out`, `disk_io_percent` at pre-sampled intervals,
  which saves you the initial parsing step if the schema fits your needs).
- **Confirmed schema (verified today):** ~4000 machines over 8 days;
  `machine_usage.csv` sampled at 10-second intervals; shows clear diurnal cycles —
  exactly the "realistic arrival-timing signal" your plan calls for.
- **Size:** full dataset is ~98GB — you only need `machine_usage.csv` or
  `batch_task.csv` subsets, not the whole thing. Download only what you need.
- **Action:** once downloaded, write a small parsing script that extracts a
  normalized load curve (e.g., CPU utilization over time, binned) that you can
  use to *drive* synthetic concurrent query arrival rates in your interference
  harness (Phase 3) — this is not the load itself, it's a realistic *shape* you
  impose on your own synthetic query arrival process.

### 1.4 Deliverable for Phase 1
- A validated TPC-DS/TPC-H dataset loaded into local Iceberg tables via
  Spark-Iceberg.
- A CAB-gen-generated query stream successfully converted and executed through
  LST-Bench against those tables (a trivial run — you're validating plumbing,
  not measuring anything yet).
- A parsed, cleaned Alibaba load-rate curve saved locally (e.g., as a resampled
  CSV/Parquet time series) ready to parameterize concurrent load in Phase 3.

---

## Phase 2 — Baseline Reimplementation (Weeks 3–4)

Before you can claim a "when" contribution, you need working "what"/"whether"
baselines to schedule *around*. This is Gate 2.

### 2.1 AutoComp MOOP baseline (Python)
Implement directly from the AutoComp paper's formulas (§4.2–4.3):
- File count reduction: `ΔF_c = Σ 1[FileSize_i,c < TargetFileSize_c]`
- Compute cost: `GBHr_c = ExecutorMemoryGB × (DataSize_c / RewriteBytesPerHour)`
- Min-max normalization of traits, weighted-sum scalarization:
  `S_c = w1·T'_1,c − w2·T'_2,c`
- Top-k candidate selection under a compute budget

This becomes your **candidate-selection layer** — the "what to compact" decision
your scheduler sits downstream of. You are *not* trying to improve this; you're
reimplementing it faithfully so your timing contribution has a fair, realistic
"what" decision feeding into it, rather than a strawman.

### 2.2 Off-peak deferral heuristic baseline
Implement the simple heuristic AutoComp itself mentions (§4.4/§5): defer
compaction to a fixed, pre-declared low-utilization window if usage patterns are
"predictable" (e.g., a fixed nightly window). This is your primary "current
practice" baseline for the timing dimension specifically — the one you're most
directly trying to beat.

### 2.3 Periodic / fixed-frequency baseline
Trivial: run compaction on a fixed schedule (e.g., hourly) regardless of load.
This is the naive control condition.

### 2.4 Deliverable for Phase 2
Three working, callable baseline policies (candidate-selection + timing) that can
be swapped into your evaluation harness later. Validate each against a toy
workload to confirm they produce sane output (e.g., the MOOP ranking actually
ranks more-fragmented tables higher).

---

## Phase 3 — Interference Measurement Harness (Weeks 5–8, hardest phase)

This is **Workstream B**, and Gate 3 ("is the interference signal measurable
above Spark's run-to-run noise?") is the single biggest risk to the whole project
— treat this phase as the de-risking phase, not just an engineering phase.

### 3.1 Harness design
Build a paired control/treatment experiment runner:
- **Control:** run a query workload (via LST-Bench, driven by a CAB-gen stream)
  against an Iceberg table snapshot with *no* concurrent compaction.
- **Treatment:** run the identical query workload against the identical starting
  snapshot, but with a compaction job (using your Phase 2 candidate-selection
  baseline) running concurrently.
- **Fair reset mechanism:** use Iceberg snapshot/rollback (`RESTORE TABLE` or
  equivalent Spark-Iceberg procedure) to reset table state between trials so
  control and treatment start from identical conditions.
- **Sweep dimensions:** compaction size × concurrent load level (driven by your
  parsed Alibaba rate curve from Phase 1.3) × time-of-day.
- **Repeated trials:** run each configuration multiple times to characterize
  Spark's natural run-to-run variance — you need this variance estimate *before*
  you can claim any interference signal is real.

### 3.2 Early noise-characterization checkpoint (do this before the full sweep)
Before running the full sweep, run a **small pilot**: same config, no compaction,
repeated 10–20 times. Measure the variance in query execution time. This gives
you your noise floor. Do the same with a fixed compaction treatment repeated
10–20 times. If the treatment-vs-control difference is not clearly larger than
each condition's own repeat-to-repeat variance, you've hit Gate 3 early and cheap
— better to know this in week 5 with a small pilot than in week 8 after a full sweep.

### 3.3 Output
Two labeled datasets:
- **Interference cost table:** query latency/throughput degradation as a function
  of (compaction size, concurrent load, time-of-day, table state features).
  This is your regression target for RQ1.
- **Cost-of-delay table:** fragmentation degradation (query latency increase)
  as a function of how long compaction is withheld. This lets you quantify the
  "wait too long" side of the tradeoff, not just the "compact now = contention" side.

### 3.4 Deliverable for Phase 3 (= Gate 3)
A validated interference signal that is statistically distinguishable from
Spark's run-to-run noise, backed by the pilot variance measurements from 3.2.
If this fails, this is your trigger point for **Pivot 1** (empirical
characterization paper) — see `pivot_topics_v2.md`.

---

## Phase 4 — Forecaster (Weeks 8–9)

- Train a near-future load forecaster on your parsed Alibaba rate curve (and/or
  your CAB-gen-driven synthetic arrival patterns) — start simple: a naive
  "same as yesterday" / seasonal-naive baseline first, then a real model
  (gradient-boosted trees or a small time-series model) only if it clearly beats
  the naive baseline.
- **Gate 4:** forecaster must beat the naive "same as yesterday" baseline before
  you proceed — don't let this phase run long if a simple model already works;
  resist the urge to over-engineer here, since the interesting research
  contribution is downstream (RQ1/RQ4), not the forecaster itself.

---

## Phase 5 — Motivating Study (Weeks 9–12)

Run your three workload families (steady-state, distribution-shift,
interference-heavy) through the Phase 3 harness at scale, using the Phase 2
baselines and Phase 4 forecaster as inputs.

- **Gate 5:** look for a clean, characterizable helps-vs-fails pattern for
  learned timing across these families. This determines whether you proceed to
  the full scheduler (Phase 6) or pivot (see Pivot 2 in `pivot_topics_v2.md`).
- This phase directly answers **RQ1 (predictability)** and starts building the
  evidence base for **RQ2 (generalization)**.

---

## Phase 6 — Scheduler + Calibration (Weeks 12–16)

- Build the now/off-peak/defer decision layer on top of the Phase 4 forecaster
  and Phase 3 interference-cost model.
- **Explicitly allocate time to uncertainty calibration methodology** (this was
  flagged in the earlier feasibility review as under-specified): choose one of
  conformal prediction, quantile regression, or ensemble disagreement — implement
  it, then **validate the calibration itself** (reliability diagrams, coverage
  tests) before treating the uncertainty estimates as trustworthy. Do not skip
  the validation step even under time pressure — an unvalidated uncertainty
  score is not a safety mechanism, just an unverified confidence knob.
- This phase answers **RQ4 (safety)**.

---

## Phase 7 — Full Evaluation (Weeks 16–19)

- Compare: your scheduler vs. Phase 2's three baselines (MOOP-only,
  off-peak-heuristic, fixed-period).
- Include a bounded robustness check per the reframed **RQ5**: one held-out,
  unseen interference pattern not used in training or threshold selection —
  report honestly, don't oversell beyond what you tested.
- **Gate 6:** clear, honest narrative supported by the data — this is where you
  decide whether the paper's central claim (learned timing beats heuristics,
  with safe fallback under uncertainty) is actually supported.

---

## Phase 8 — Writing (Weeks 19–23) and Submission Prep (Weeks 23–25)

Standard from here — full draft, internal review, related-work re-check
(specifically re-search for any new IBM Research or Databricks/Snowflake
publications on lakehouse maintenance timing before submitting), formatting,
submit for the Feb 2027 PVLDB cycle.

---

## Immediate Next Actions (this week)

1. Install JDK, clone LST-Bench, run `./mvnw package -Pspark-jdbc` — confirm it builds.
2. Clone CAB-gen, confirm it runs and produces output.
3. Start the Alibaba cluster-trace-v2018 survey/download in parallel (this can
   take time to process — don't leave it until Phase 3 starts).
4. Resolve the VLDB reviewer-qualification question with your CDSAML advisor —
   this is an administrative blocker, not a research one, and needs to be
   resolved by Week 4 per your own dealbreaker list, so start the conversation now.
5. Set a recurring calendar reminder for a monthly related-work check
   (first one: early September), specifically watching for new IBM
   Research/Databricks/Snowflake publications on lakehouse maintenance timing.
