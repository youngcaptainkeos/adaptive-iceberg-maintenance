# Methodology & Working Document
## Learned, Uncertainty-Aware Scheduling for Lakehouse Storage Maintenance

**Status:** Living document. Updated as the project progresses. This is not paper prose —
it is the working record of *what we are doing and why*, from which the eventual paper's
Methods section will be drafted. Sections marked **[TBD]** are open decisions, not gaps
in understanding; they should be resolved and updated here before being treated as settled.

**Last updated:** Phase 0 complete. Physical-layout characterization (Phases 2F–2J) is
complete and methodologically validated. **Phase 3A (concurrent interference
measurement) and Phase 3B (predictive modeling) are complete** — this is the project's
first real evidence on its actual core research question. Proposed Phase 3C
(uncertainty-aware scheduling policies) has been critically reviewed and is
conditionally approved with required prerequisites — see Section 7.4. Alibaba trace
acquisition still blocked — see Section 5.3.1.

---

## 1. Research Question and Scope

**Core research question:**

> Given that lakehouse maintenance needs to be performed, when should it be executed so
> that its storage benefits are obtained while minimizing interference with concurrent
> query workloads?

**What the project is NOT:** a new compaction algorithm, a new table-layout optimizer, or
a general-purpose lakehouse tuning system. Compaction is the *maintenance operation under
study*, not the *contribution*. The contribution is the timing decision — when to execute
a maintenance operation relative to concurrent workload state — made under explicit,
calibrated uncertainty.

**Decision space the eventual scheduler outputs:**
- `NOW` — execute maintenance immediately
- `OFF-PEAK` — defer to a predicted lower-interference window
- `DEFER` — postpone indefinitely / re-evaluate later
- Fallback to a conservative heuristic when model uncertainty is too high to trust the
  learned prediction

**Relationship to existing literature (from the literature survey):** AutoComp and Smart
Compaction address *what/whether* to compact; PTO addresses *what layout*; a recent
RL-based preprint (Karim et al. 2026) addresses *what action* to take at each timestep
without modeling concurrent query interference. None of these model maintenance cost as a
function of *concurrent workload state*, and none provide calibrated uncertainty for a
fallback mechanism. This project's differentiation rests specifically on those two facts —
every methodology decision below should be traceable back to preserving that
differentiation, not drifting toward "another compaction system."

---

## 2. Experimental Design — Conceptual Structure

```
                  SAME QUERY WORKLOAD
                         │
              ┌──────────┴──────────┐
              │                     │
           CONTROL               TREATMENT
              │                     │
       no maintenance       concurrent maintenance
              │                     │
              └──────────┬──────────┘
                         ▼
              difference in performance
                         │
                         ▼
                 interference cost
                         │
                         ▼
                  learned model
                         │
                         ▼
                    uncertainty
                         │
                         ▼
                maintenance timing
```

The same query workload is replayed twice against an identical starting table state: once
with no concurrent maintenance (control) and once with a concurrent maintenance operation
injected (treatment). The measured difference in query performance between the two runs is
the **interference cost** of running that maintenance operation under that workload
condition. Repeated across many combinations of workload intensity, table state, and
maintenance characteristics, this produces a labeled dataset that a model can be trained to
predict from — and whose prediction uncertainty can be calibrated.

This structure is the backbone of the whole project. Every infrastructure decision in
Section 4 exists to make this comparison valid, repeatable, and free of confounds.

---

## 3. Research Pipeline (End-to-End)

```
TPC-H
  ↓
Iceberg lakehouse
  ↓
LST-Bench workload  +  maintenance workload
  ↓
query/maintenance telemetry
  ↓
interference-cost dataset
  ↓
prediction model
  ↓
uncertainty calibration
  ↓
maintenance scheduler
```

---

## 4. Development Environment (as of this update)

| Component | Version | Status |
|---|---|---|
| OS | Ubuntu | — |
| Java | 11 (`java-11-openjdk-amd64`) | ✅ |
| Apache Spark | 3.3.4 (standalone, `bin-hadoop3` build) | ✅ |
| PySpark | 3.3.4 | ✅ |
| Apache Iceberg (Spark runtime) | 1.4.3 (`iceberg-spark-runtime-3.3_2.12-1.4.3.jar`) | ✅ |
| DuckDB | 1.5.5 | ✅ (telemetry sink, not yet receiving data) |
| Microsoft LST-Bench | cloned + built (`mvnw package -Pspark-jdbc`) | ✅ built, integration in progress |
| CAB-gen | cloned | ✅ cloned, not yet run |
| Hive JDBC | 3.1.3 | ✅ verified end-to-end |
| Spark Thrift Server | running on `127.0.0.1:10000` | ✅ |

**Version decision:** Standardized on Spark 3.3.4 / Iceberg 1.4.3, not the originally
discussed Spark 3.5.9. This was a deliberate choice, not drift: 3.3.4 is the version
LST-Bench's stock schemas were validated against, avoiding the `SPARK-44025` regex patch
that 3.4+ requires. All team members should build against this exact pin.
**[TBD — confirm all four team members (Shashank D, Prachi, Samarth) are on this same
pin before Phase 1 work is distributed.]**

**Known environment quirks (documented so they aren't re-discovered):**
- The dev machine has a full Hadoop/HDFS install present; relative warehouse paths can
  silently resolve to `hdfs://localhost:9000` instead of local disk. The Iceberg warehouse
  path is therefore forced to `file:///...` explicitly. **Do not change this to a
  relative path.**
- The project root path contains spaces (`Link to PDocuments`), which breaks Spark's
  daemon shell scripts (`ambiguous redirect` on Thrift Server startup). Worked around via
  `SPARK_LOG_DIR` / `SPARK_PID_DIR` / `SPARK_IDENT_STRING` pointed at `/tmp`, rather than
  modifying Spark. **[TBD — consider whether to relocate the project root to a space-free
  path before the team scales up work in parallel, to avoid every team member hitting and
  re-solving this.]**

---

## 5. Data Layer

### 5.1 TPC-H SF1 (current)
Generated via official `dbgen` (TPC-H Tool V3.0.1, Generator 3.0.0 build 0, scale factor 1).
Row counts validated against known SF1 cardinalities (customer 150,000; lineitem 6,001,215;
orders 1,500,000; part 200,000; partsupp 800,000; supplier 10,000; nation 25; region 5).
A manifest with SHA-256 checksums exists; source `.tbl` files are treated as immutable
ground truth — not to be regenerated.

**Why SF1 first, not SF1000:** SF1 is deliberately small so that infrastructure
correctness can be validated cheaply and quickly, before scaling up. This is a plumbing
validation dataset, not the dataset the actual interference experiments will run on.
**[TBD — decide target scale factor(s) for the actual interference-measurement sweeps in
Phase 2/3. AutoComp and the Smart Compaction paper both use larger scales; our synthetic
interference harness will need enough data volume that compaction operations and query
scans have realistic, non-trivial durations. This should be revisited once Phase 1
baseline-variance numbers are in hand — see Section 7.]**

### 5.2 Iceberg catalog
Local Hadoop-type Iceberg catalog (`local`), warehouse forced to `file:///` for the
reason noted above. All 8 TPC-H tables loaded with explicit schemas (proper date types,
decimal monetary fields — not inferred, not floats). Loading script is idempotent
(drop-if-exists → recreate → load), so re-runs cannot silently duplicate data.

Row-count and join validation (customer↔nation, orders↔customer, lineitem aggregation)
all confirmed exact matches against source SF1 cardinalities.

### 5.3 Future datasets **[TBD, not yet started — explicitly deferred]**
- CAB-gen-driven query streams (cloned, not yet run)
- Alibaba cluster-trace-v2018 — **BLOCKED**, see 5.3.1 below.

#### 5.3.1 Alibaba trace acquisition — blocked, resolution plan

**Status: blocked, not on the critical path yet.** The survey-gated download link on the
official `alibaba/clusterdata` GitHub repo is not producing a working download for either
the 2018 or 2017 trace. Confirmed this is not specific to our setup or network: this is a
long-standing, widely-reported problem with this dataset's release infrastructure —
GitHub issue #93 ("Not able to download traces," open since 2021) describes the identical
symptom, and issue #57 documents users hitting `AccessDenied` on the underlying Alibaba
OSS storage bucket even after completing the survey. The gate is unreliable/broken
upstream, not a configuration issue on our end.

**Why this is not urgent right now:** per the phase progression (Section 7), the Alibaba
trace is only needed starting in Phase 2/3, to provide a realistic diurnal load-intensity
*shape* that drives synthetic concurrent query arrival rates in the interference harness.
It is not required for Phase 1 (baseline variance measurement) at all. This gives real
runway to resolve it properly rather than needing an emergency substitute today.

**Resolution plan, in order of preference:**

1. **Try the documented no-survey fallback path first.** The trace's own documentation
   (`cluster-trace-v2018/trace_2018.md`) states explicitly: *"If you do not want to do the
   survey, you could have the trace too"* — two direct download links are provided (one for
   Chinese users, one for overseas), each with published SHA-256 checksums for all six
   `.tar.gz` files (`batch_instance`, `batch_task`, `container_meta`, `container_usage`,
   `machine_meta`, `machine_usage`). This bypasses the survey entirely and should be tried
   before anything else — **[TBD: someone should visit the `trace_2018.md` file directly on
   GitHub and pull the current non-survey links, since the ones referenced in older issues
   may have rotted; verify against the published checksums after download to confirm
   integrity]**.
2. **File a GitHub issue directly on `alibaba/clusterdata`**, as the repo's own README
   recommends over emailing (recommended specifically because "the discussion would help
   all the community"). Given issue #93 has sat open since 2021, do not expect a fast or
   any response — treat this as a low-probability, non-blocking action to take in parallel,
   not a plan to wait on.
3. **Check for community mirrors.** Several forks/mirrors of the repo exist (e.g.
   `CrazyLeaner/clusterdata`, `aFang-share/clusterdata-alibaba`) — these mirror the
   documentation but not necessarily the actual data files (which are hosted on Alibaba's
   own OSS buckets, not GitHub, and are too large for a git repo regardless). Worth a quick
   check for a Zenodo/academic-mirror re-upload of the processed trace before ruling this
   out, but do not spend more than an hour on this before moving to option 4.
4. **Pivot to `cluster-trace-v2017` instead of v2018**, if all of the above fail. It uses
   the same survey-gated mechanism and may have the same problem, but it's worth a quick
   check since it's a separate release pipeline. Smaller (1,300 machines, 12 hours) but
   still provides a real diurnal-adjacent load signal, at reduced fidelity.
5. **Fallback: synthesize a realistic diurnal load curve instead of using a real trace.**
   If none of the above produce usable data within a reasonable time box **[TBD: set a
   concrete deadline here, e.g. "by the start of Phase 2," so this doesn't silently stall
   Phase 2/3 planning]**, the project can construct its own synthetic diurnal load-intensity
   curve (e.g. a sinusoidal or piecewise base pattern with realistic peak/off-peak
   ratios and noise, calibrated against published summary statistics from cloud-workload
   literature rather than raw trace data — CAB-gen's own query-stream patterns, already
   in use, are one available reference point, as are the load-curve descriptions in the
   AutoComp and Smart Compaction papers). This is a legitimate, defensible substitution —
   plenty of systems papers construct synthetic diurnal patterns rather than relying on a
   single real trace — but it should be explicitly disclosed as a synthetic input in the
   eventual paper's Methods section and Limitations, not silently substituted. **This
   option should not be treated as inferior busywork; if reached, document the specific
   parameters chosen and their justification here in this doc before implementing.**

**This is not currently blocking any active work** — Phase 1 does not depend on this
dataset. Revisit before Phase 2 begins.

---

## 6. Workload Execution Layer

### 6.1 Why LST-Bench, and what it is/isn't being used for
LST-Bench is treated as **workload execution + telemetry infrastructure**, not as the
research contribution. It provides a SQL workload runner with pluggable connection configs
and captures execution telemetry. The stock TPC-H workload (`W0`) is built around SF1000,
Spark 3.3.1, Iceberg 1.1.0, and Azure infrastructure assumptions — it will **not** be run
unchanged. Custom configuration lives entirely outside the LST-Bench repo
(`scripts/lst-bench-config/`), so the upstream repository is never modified.

### 6.2 Integration architecture
LST-Bench's Spark connector expects a Hive-compatible JDBC endpoint
(`org.apache.hive.jdbc.HiveDriver`, `jdbc:hive2://...`). Rather than modifying LST-Bench
internals to talk to Spark directly, the integration path is:

```
LST-Bench → JDBC → Spark Thrift Server → Spark → Iceberg
```

This has been validated end-to-end via a manual JDBC test (`SELECT COUNT(*) FROM
local.tpch.lineitem` → exact match, 6,001,215) before attempting the LST-Bench-driven
version, isolating "does the JDBC chain work at all" from "does LST-Bench's YAML
configuration exercise it correctly" — these were deliberately tested as separate layers.

### 6.3 Scheduling mode under the Thrift Server — ✅ RESOLVED (Phase 3A)

This was flagged as an open, must-resolve-before-Phase-2 question. **It has now been
directly resolved with real evidence, not just decided in principle.** Phase 3A ran the
full interference experiment under both FIFO and FAIR scheduling (FAIR configured with
explicit foreground/background pools: minShare=12/weight=3 foreground, minShare=4/weight=1
background, on a 16-core host), verified via Spark event-log inspection that pool
assignment actually happened as configured (not just assumed), and measured interference
under both. Result: **no statistically significant difference in overall interference
between FIFO and FAIR was found** (paired t-test p=0.16689, Wilcoxon p=0.21106, small
effect size dz=−0.32) in this environment. This is reported with appropriate hedging by
the team (not claiming FAIR is universally ineffective, just that this configuration
didn't show a detectable benefit here) — see Section 7.4 for a caveat on whether this
might be a statistical power issue rather than genuine absence of effect.

**Practical implication for the interference harness:** since neither scheduling mode
showed a significant difference, the earlier concern that FIFO might understate
interference via serialization rather than genuine contention appears **not to have
occurred** — FIFO measured *more* interference than FAIR on average (+10.38% vs
comparable), not less, which is inconsistent with the failure mode originally worried
about (queueing delay being mistaken for contention would tend to show FIFO with
artificially *higher* apparent latency from queueing, which is actually what we see —
worth being aware this doesn't fully rule out queueing effects, just that the FIFO/FAIR
comparison itself doesn't show FAIR "fixing" a queueing artifact in the way that would be
diagnostic). Current data supports proceeding with either scheduling mode for further
Phase 3 work; FIFO is simpler and can likely be the default going forward unless a
specific reason to prefer FAIR emerges.



### 6.4 Current task: minimal smoke-test configuration
A project-specific LST-Bench configuration directory is being built
(`scripts/lst-bench-config/`) with a minimal smoke workload — a single query
(`SELECT COUNT(*) FROM local.tpch.lineitem`) run through the full LST-Bench → JDBC →
Thrift → Spark → Iceberg → DuckDB telemetry chain. This is **not research data** — its
only purpose is proving the full chain works end-to-end before any real workload
experiments begin.

**Smoke-test success criteria:**
- LST-Bench starts and connects via JDBC without error
- Query executes and returns exactly 6,001,215
- DuckDB telemetry database is created and records at least one execution
- No existing Iceberg tables are modified
- No stock LST-Bench files are modified

**Status: ✅ Phase 0 complete.** The full chain (LST-Bench → JDBC → Thrift Server →
Spark → Iceberg → DuckDB telemetry) is validated end-to-end. Infrastructure is ready for
Phase 1.

---

## 7. Planned Phase Progression

| Phase | Description | Status |
|---|---|---|
| 0 | Infrastructure: Spark + Iceberg + LST-Bench + DuckDB telemetry | ✅ **Complete** |
| 1 | Baseline workload variance ("noise floor") | ✅ **Complete — delivered as Phase 2F, see 7.2** |
| 2 | Maintenance interference: controlled CONTROL vs TREATMENT (query workload alone vs. + concurrent maintenance) | ✅ **Complete — delivered as Phase 3A, see 7.4** |
| — | *(interstitial)* Physical-layout characterization: three-state (control/fragmented/compacted) comparison, methodologically validated | ✅ **Complete — Phases 2F–2J, see 7.2 and 7.4** |
| 3 | Interference-cost dataset construction | ✅ **Complete — delivered as Phase 3B, see 7.4** |
| 4 | Prediction — train a model on the Phase 3 dataset | ✅ **Complete — Phase 3B, see 7.4. Regression solid (RF MAE 5.38%); classifier weak (AUC 0.531), see open item 18** |
| 5 | Uncertainty calibration | ⚠️ **Not yet done properly — quantile model exists but uncalibrated, see open item 13. This is the current critical path.** |
| 6 | Scheduler — final NOW / OFF-PEAK / DEFER decision logic with fallback | 🔄 **In progress as proposed Phase 3C — conditionally approved, see Section 7.5 for required prerequisites** |

**Why Phase 1 (baseline variance) comes before Phase 2 (interference):** we cannot claim a
measured latency difference between control and treatment is *caused by* concurrent
maintenance unless we first know how much query latency varies run-to-run under
*identical* conditions with no maintenance at all. This is the "noise floor" pilot
described in the original execution plan (Gate 3) — Phase 1 here *is* that pilot, just
described at the infrastructure-build level rather than the gate-check level. The two
documents should be read together.

**Interference metric — current working form, not finalized:**
$$ I = \frac{L_{treatment} - L_{control}}{L_{control}} $$
where $L$ is a query latency measure. **[TBD — the exact final metric needs design and
validation. Open questions: latency of which queries specifically (all 22 TPC-H queries?
a subset chosen for scan-heaviness?); mean vs. tail (p95/p99) latency, given that
interference is likely to show up more in tail behavior than in means, per AutoComp's own
candlestick-plot evidence of wide latency spread under compaction; per-query or
aggregate-workload level.]**

---

## 7.1 What Was Actually Run (Team Update, Post-Phase-0) — and Why It Needs Rework

### What happened

Rather than running Phase 1 as scoped above (repeated baseline runs to measure
**natural run-to-run variance with no changes to the table at all**), the team proceeded
directly into a fragmentation/compaction lifecycle experiment, internally labeled
"Phase 1B" through "Phase 2E":

1. **Baseline workload characterization** (their "Phase 1B") — 6 TPC-H queries
   (Q1, Q3, Q6, Q12, Q14, Q18), each run **3 times**, against the healthy 16-file control
   table (`local.tpch.lineitem`).
2. **Physical storage baseline** (their "Phase 2A") — inspected the healthy table's
   physical layout: 16 files, ~9.08 MB average.
3. **Controlled fragmentation** (their "Phase 2B") — created a **separate** experimental
   table (`local.experiment.lineitem_fragmented`), repartitioned into 200 files (~842 KB
   average), leaving the control table untouched. Row-count and checksum validation
   passed.
4. **Fragmented performance** (their "Phase 2C") — same 6-query workload, 3 reps each,
   run against the fragmented table. Reported: fragmented state **34.89% faster overall**
   than the control baseline (13.811s → 8.992s), with mixed per-query direction (some
   queries faster, some slower).
5. **Compaction** (their "Phase 2D") — ran Iceberg's `rewrite_data_files` with **no
   explicit target file size specified**, using the default binpack strategy. Result:
   200 files → **1 file** (156.34 MB). Row/schema/checksum validation passed.
6. **Post-compaction performance** (their "Phase 2E") — same workload against the
   1-file compacted table. Reported: **slowest of all three states** (16.885s), i.e.
   +22.25% slower than the original healthy control and +87.77% slower than the
   fragmented state.

### Why these results are not yet trustworthy as findings

This is a validity assessment, not a rejection of the work — the engineering discipline
(separate experiment table, checksummed data-integrity validation at every step, isolated
`scripts/` directory structure, control table never touched, clean `lst-bench/` submodule)
is genuinely solid and should continue exactly as-is. The problem is specifically in the
**statistical and experimental-design layer**, which has not yet caught up:

1. **The Phase 1 noise-floor step was skipped, and it is not optional.** Section 7 above
   states explicitly why Phase 1 must come before any control/treatment-style comparison:
   *"we cannot claim a measured latency difference... is caused by [a change] unless we
   first know how much query latency varies run-to-run under identical conditions with no
   [change] at all."* Right now there is no baseline variance measurement — no repeated
   runs of the *same* table state with no changes between them, across enough repetitions
   and enough elapsed time to characterize normal JVM/OS/Spark noise. Without that
   number, none of the "State A vs B vs C" percentage differences can be judged as real
   effects versus normal noise.

2. **n = 3 repetitions per query per state is too small, and no variance was reported.**
   Every number in the update is a mean with no accompanying standard deviation, min/max,
   or confidence interval. Several of the reported per-query differences are on the order
   of 50–150 milliseconds on queries that already run in under a second (e.g. Q6:
   0.406s → 0.499s, a 93ms difference) — differences of exactly the magnitude that normal
   single-machine JVM warm-up, garbage collection pauses, and OS scheduling jitter
   routinely produce. AutoComp's own production-cluster evaluation shows wide latency
   spread (candlestick plots, Figure 8 in that paper) even at much larger scale with
   dedicated clusters; a single local machine should be expected to show *more* noise, not
   less.

3. **State C's result is very likely a configuration artifact, not a real compaction
   outcome, and should not be reported as one without first fixing it.** `rewrite_data_files`
   was called with no explicit `target-file-size-bytes` (or equivalent) parameter. With no
   target specified and the fragmented table's total size (~164 MB) below Iceberg's
   default target, the binpack strategy has no size boundary to stop at and can merge
   everything into a single file — which is exactly what happened (200 → 1). This is not
   what a real compaction policy does in production: AutoComp uses an explicit 512 MB
   target; PTO explores an explicit discretized target-file-size range (32 MB–512 MB); the
   fragmentation step in this very experiment (step 3 above) *did* specify an explicit
   target (524288 bytes). The compaction step should be re-run with an explicit,
   realistic target file size (e.g. matching the fragmentation step's own convention, or a
   more standard 64–128 MB target scaled to this dataset's size) before "extreme
   compaction is slower" is treated as a real finding. Right now State C is not
   comparable to States A/B — it's an unconfigured condition, not a data point on the
   same curve.

4. **No run isolation, ordering randomization, or reported machine-quiescence check.**
   Single machine, single run per condition (not interleaved/randomized across repeated
   trials), no reported confirmation that no other significant process was competing for
   CPU/disk during each phase. If State A, B, and C were run in that literal order,
   separated by however long the fragmentation/compaction steps themselves took, warm
   JVM caches, OS filesystem cache state, or GC behavior could differ systematically
   between conditions in ways unrelated to file count.

5. **The proposed Phase 3 (sweep file counts 1→4→8→...→200) is the right instinct,
   structurally — but should not be run with the current methodology, or it will just
   produce eight noisy points instead of three.** Once the fixes below are applied, this
   sweep becomes exactly the kind of characterization Phase 1 of the original execution
   plan and the "noise floor" pilot were meant to feed into — it should proceed, but only
   after the fixes in the next section are in place.

### Concrete fix-forward plan, before continuing to a file-count sweep

1. **Run the missing noise-floor baseline first.** Same 6-query workload, same healthy
   16-file control table, **no changes to the table between runs**, but with enough
   repetitions (recommend ≥10, ideally ≥20 per query, matching the "10–20 repeat" pilot
   scale suggested in the original execution plan's Gate-3 guidance) to compute a
   meaningful mean ± standard deviation / coefficient of variation per query. This
   produces the noise floor that every subsequent comparison must be checked against.
2. **Increase repetitions for the fragmentation/compaction comparisons to match** (≥10
   per query per state, not 3), and report variance (std dev or CV), not just means —
   this repo already has the DuckDB telemetry and CSV pipeline built, so this is a
   re-run/re-aggregation, not new infrastructure.
3. **Re-run the compaction step with an explicit, realistic target file size** (document
   the chosen value and why), and treat the current 1-file/156MB result as invalidated
   until that re-run exists.
4. **Randomize or interleave run order** across states where feasible (e.g., alternate
   A/B/C repetitions rather than running all of A, then all of B, then all of C), to
   reduce the chance of systematic drift (cache warmth, GC state) being mistaken for a
   real effect. If full interleaving isn't practical given the fragmentation/compaction
   steps physically change which table exists, at minimum re-run each state's benchmark
   a second time, non-adjacently in time, as a repeatability check.
5. **Only after 1–4 above are done**, proceed to the team's proposed Phase 3 file-count
   sweep (1, 4, 8, 16, 32, 64, 128, 200 files) — at that point it becomes a legitimate
   characterization study rather than a noisy repeat of the same design problem eight
   times over.

**This does not invalidate the infrastructure work.** The experiment tables, the
checksummed validation, the DuckDB/CSV/telemetry pipeline, the repo isolation — all of
that is real, working, reusable infrastructure. What needs to change is purely the
*experimental design* layered on top of it: more repetitions, reported variance, a real
noise-floor baseline, and a correctly-configured compaction target. This is a
methodology-layer fix, not an infrastructure rebuild.

---

## 7.2 Resolution: Phases 2F–2H (Validated Physical-Layout Experiment)

Every item in Section 7.1's fix-forward plan has been directly addressed:

| 7.1 Problem | Resolution |
|---|---|
| No noise-floor baseline | **Phase 2F**: 20 measured + 2 warmup reps on the unchanged control table |
| n=3, no reported variance | **Phase 2G**: 20 measured reps per state; mean, median, min, max, std dev, CV, and Student-t 95% CIs reported |
| Unconfigured 1-file compaction | **Phase 2G**: explicit `target-file-size-bytes = 67108864` (64MB) → realistic 4-file result |
| No run-order randomization | **Phase 2G**: counterbalanced cyclic rotation (A→B→C, B→C→A, C→A→B), order logged |
| Arbitrary "% difference" language | **Phase 2H**: Shapiro-Wilk normality testing per comparison, then Wilcoxon signed-rank (non-parametric) or parametric testing as appropriate, applied to paired counterbalanced observations |

### Phase 2F — Noise floor (control table, unchanged, 20 measured reps)

| Query | Mean | Std Dev | CV |
|---|---:|---:|---:|
| Q1 | 6.801 s | 0.1745 s | 2.57% |
| Q3 | 1.140 s | 0.0777 s | 6.82% |
| Q6 | 0.385 s | 0.0212 s | 5.50% |
| Q12 | 0.688 s | 0.0522 s | 7.58% |
| Q14 | 0.572 s | 0.0628 s | 10.99% |
| Q18 | 3.025 s | 0.1724 s | 5.70% |
| **Total workload** | **12.612 s** | **0.4097 s** | **3.25%** |

Warmup effect confirmed large and real: warmup 1 = 24.049s, warmup 2 = 13.548s (43.66%
reduction) — warmup and measured reps are now explicitly separated in all later phases.

**[TBD — the empirical "3× CV" noise-screening threshold used to initially flag
differences (e.g. Total Workload > 9.75%) is a heuristic with no stated statistical
derivation. It has since been superseded by the formal Phase 2H testing below and should
not be relied on as the primary evidence in the eventual paper — see Section 7.3, point 1.]**

### Phase 2G — Validated three-state comparison (20 measured reps/state, counterbalanced order)

| State | Files | Avg file size | Mean workload runtime |
|---|---:|---:|---:|
| A — Control | 16 | ~9.08 MB | 11.616 s |
| B — Fragmented | 200 | ~842 KB | **7.458 s** |
| C — Compacted (64MB target) | 4 | ~39.11 MB | 10.677 s |

Observed ordering: **fragmented fastest → compacted → control slowest.**
Additional variability finding: compacted layout showed *lower* run-to-run CV (~2.78%)
than fragmented (~3.68%), despite fragmented having the lower mean — a mean-vs-variance
tradeoff, not a strictly dominant layout.

### Phase 2H — Formal statistical testing

Shapiro-Wilk normality testing on paired differences found **several distributions
significantly non-normal** (e.g. Q1 Compacted-vs-Control, Q18 Compacted-vs-Control, Q3
Fragmented-vs-Control, all p<0.05), correctly ruling out blanket use of a paired t-test.
Wilcoxon signed-rank test applied for paired, counterbalanced comparisons where normality
was violated. This is the step that upgrades the claim from "exceeds an empirical
threshold" to "formally tested," and is the single most important addition since the
last review.

**Current bounded claim the team is making (their own wording, and it is good wording):**
> "In the tested single-workstation Spark 3.3.4/Iceberg 1.4.3/TPC-H SF1 environment,
> different Iceberg physical file layouts produced measurably different workload
> behavior, including statistically validated differences for relevant paired
> comparisons. The 200-file fragmented layout was observed to outperform the 16-file
> control and the compacted layout for important parts of the representative workload,
> while the compacted layout exhibited lower runtime variability than the fragmented
> layout."

This is an appropriately scoped, defensible claim as written.

---

## 7.3 Critical Review Against A-Conference Standards

This section is deliberately blunt, per request. The methodology work is genuinely
strong — stronger than most master's-level empirical systems work reaches. The gap
between "genuinely strong" and "A-conference-ready" is now about **statistical
completeness, scale realism, and mechanistic explanation**, not about experimental
discipline. Specific points, ordered by how much they'd matter to a PVLDB/SIGMOD reviewer:

**1. The 3× CV noise-screening threshold needs to be either removed or properly
justified — do not let it appear in the paper as-is.** It has no stated statistical
derivation (it is not the standard 3-sigma control-limit convention, which is a different
quantity), and now that Phase 2H's Shapiro-Wilk + Wilcoxon pipeline exists, the threshold
is redundant — a strictly weaker, less defensible method sitting next to a strictly
stronger one. **Recommendation: drop the CV-multiplier framing entirely from any future
write-up and lead exclusively with the Phase 2H formal test results.** Keeping both
invites a reviewer to ask "why do you have two different significance criteria, and which
one is authoritative?" — a question with no good answer.

**2. No effect sizes reported alongside the hypothesis tests.** A Wilcoxon test tells you
*whether* a difference is unlikely to be noise; it does not by itself communicate *how
large* the effect is in a standardized, comparable way. For an A-venue submission, each
significant paired comparison should be accompanied by an effect size (e.g., matched-pairs
rank-biserial correlation for Wilcoxon, or simply the paired mean difference with its own
CI) — reviewers increasingly expect this alongside p-values, and its absence is a common,
specific reviewer complaint. This is a small addition given the pipeline that already
exists.

**3. Multiple-comparisons correction is not mentioned anywhere.** Six queries × three
pairwise state comparisons (A-B, A-C, B-C) = 18 tests, plus the workload-total comparisons
— run that many hypothesis tests without correction (Bonferroni, Holm, or a
false-discovery-rate method) and some "significant" results are expected by chance alone
at α=0.05. This is one of the most common, most mechanical reviewer objections to
multi-query benchmark papers, and it's a cheap fix (a few lines in the stats pipeline)
relative to the damage an unaddressed version does to credibility.

**4. The parallelism explanation is still not mechanistically verified, and the team's
own hedging on this point is exactly right — do not let a later draft accidentally lose
that hedge under deadline pressure.** "More files enables more concurrent Spark tasks" is
a plausible, standard explanation, but it has not been checked against actual Spark task
counts/timelines (Spark UI event logs, or programmatic access to the same data). This is
listed in the team's own "next steps," correctly. For an A-venue paper, I would treat this
as **not optional** — a reviewer in this specific subfield (three of your six survey
papers are from authors who work on exactly this kind of system-internals evidence) will
almost certainly ask "did you confirm task parallelism actually increased, or is this
speculation?" Pulling Spark event-log task counts per stage for a representative run of
each state is a bounded, concrete task, not open-ended re-engineering — it should be
scheduled before scaling up further, not after.

**5. SF1 + single machine is a real, currently-honest limitation — but it is also the
biggest risk to the paper's eventual reception, and needs a plan, not just a disclosure.**
Being upfront about this (which the team is doing well) is necessary but not sufficient.
A reviewer's likely question: "does this counterintuitive fragmented-beats-compacted
result hold at a realistic scale (SF100/SF1000, matching AutoComp's and PTO's own
evaluation scale) or is it a small-data/single-machine artifact (e.g., everything fits in
OS page cache at SF1, erasing the I/O-bound advantage compaction usually provides at
scale)?" This is a very plausible alternative explanation for the current result, and it
is not yet ruled out. **This should be the team's top scientific priority once the
mechanistic check in point 4 is done** — even a single confirmatory run at SF10 or SF100
would substantially strengthen the paper, whereas leaving it purely at SF1 risks the
entire physical-layout finding being read as a curiosity of small-data caching rather
than a real systems phenomenon.

**6. Scope discipline is genuinely good, but the team should be honest with itself about
where this physical-layout characterization sits relative to the actual thesis.** This is
explicitly flagged correctly by the team already ("we should avoid prematurely expanding
the experiment again," "moving toward the project's core research problem") — good
self-awareness. To be blunt: **this entire physical-layout study (Phases 2A–2H) is
motivating background, not the contribution.** It answers "does file layout matter to
performance" (a known-important question in the literature already, per AutoComp/Smart
Compaction/PTO) — it does not yet touch *timing relative to concurrent workload
interference*, which is the actual gap this project claims to fill. This is fine and
expected — strong empirical motivation sections are valuable — but the team should not
let this phase's momentum and methodological polish become a reason to keep extending it
(e.g., the proposed file-count sweep) at the expense of starting the actual interference
harness (original Phase 2 in the top-level plan, Section 6.3's still-unresolved Thrift
Server scheduling-mode question). **Time-box this:** one mechanistic-verification pass
(point 4) + one larger-scale confirmatory run (point 5), then move to the interference
harness regardless of whether the file-count sweep is "finished."

### Answering the team's three explicit review questions

**(1) Does Phase 2H adequately address the arbitrary-threshold criticism?** Yes,
substantially — Shapiro-Wilk-gated parametric/non-parametric testing is the right
approach and is correctly implemented in spirit. Remaining gaps before this is
A-venue-complete: effect sizes (point 2) and multiple-comparisons correction (point 3).
Both are additions to an existing pipeline, not new infrastructure — should be quick.

**(2) Is "statistically validated empirical result in this specific environment" (not "a
general rule") appropriately cautious wording?** Yes — this is exactly the right level of
claim given current evidence, and matches how AutoComp and Smart Compaction both hedge
their own single-environment findings. Keep this wording discipline through to the final
paper; do not let later urgency loosen it without new evidence (specifically, points 4–5)
to support a stronger claim.

**(3) What should come next, and in what order?** Recommended order, tightened from the
team's own three options:
1. **Pull Spark task-level telemetry for one representative run per state** (point 4) —
   cheap, bounded, directly answers the team's own stated uncertainty about the
   parallelism mechanism.
2. **One confirmatory run at a larger scale factor** (SF10 minimum, SF100 if time allows)
   (point 5) — the single highest-leverage thing to do before writing any of this up as a
   result, since it's the most likely alternative-explanation a reviewer will raise.
3. **Then** pivot to the actual core research problem: the concurrent
   maintenance-interference harness (original project Phase 2), starting by resolving the
   still-open Thrift Server scheduling-mode question (Section 6.3) before building the
   control/treatment harness on top of it.
4. The file-count sweep (1→4→8→...→200) is a reasonable *future* extension of the
   physical-layout motivating section, but should not come before item 3 — it's polish on
   background material, not progress on the thesis.

**Status update: items 1 and 3 above were completed as Phase 2J and Phase 3A/3B
respectively (see Section 7.4). Item 2 (larger-scale confirmatory run) has not yet been
done and remains an open item — see Section 7.4's carried-forward TBD list.**

---

## 7.4 Phases 2I–3B: From Physical-Layout Motivation to Core Interference Modeling

This section covers the work completed after Section 7.3's review: statistical hardening
of the physical-layout study (2I), mechanistic verification (2J), the pivot to the actual
core research question (3A), and initial predictive modeling (3B). This is the project's
first substantive evidence on the thesis itself, not just its motivating background.

### Phase 2I — Statistical reporting hardening

Directly resolved the two gaps flagged in Section 7.3 (points 2–3):
- **3×CV heuristic retired** as an inferential criterion — now descriptive-only context,
  formal testing (Phase 2H) is authoritative. Resolves 7.3 point 1.
- **Effect sizes added**: paired mean difference, percentage difference, 95% CIs, Cohen's
  $d_z$, matched-pairs rank-biserial correlation. Resolves 7.3 point 2.
- **Holm-Bonferroni correction applied globally** across all 18 query-level comparisons,
  controlling family-wise error rate at α=0.05. Resolves 7.3 point 3. Previously-significant
  findings survived correction (raw p-values were small enough); some comparisons were
  retained as explicit non-significant null results (e.g. Q12 Fragmented-vs-Control) rather
  than discarded — good practice, keep this pattern going forward.

### Phase 2J — Task-level mechanistic verification

Directly resolves Section 7.3 point 4 (the previously-unverified parallelism explanation).
Collected Spark task durations, GC time, CPU time, deserialization overhead, read bytes,
file splits, and stage-level concurrency. **Important process note worth preserving**: an
initial interpretation appeared to contradict Phase 2G, and the team correctly did not
paper over this — they audited it and found the discrepancy was explained by a genuine
environment difference (Phase 2G ran through Thrift Server/JDBC with hot repetitions;
Phase 2J's initial pass used a local PySpark/Py4J path with different driver overhead and
cache conditions), not a flaw in either experiment. This kind of reconciliation, done
transparently, is exactly the right response to a surprising result and should be
documented as-is in the eventual paper rather than smoothed over.

**Reconciled mechanistic finding**: not "more files is always better," but a genuine
parallelism-vs-overhead tradeoff that depends on workload shape — heavier scan/aggregation
workloads (Q1, Q3, Q14) can benefit from fragmentation-enabled task parallelism; lighter
workloads (Q6) can be dominated by per-file metadata/footer overhead instead. This is a
more defensible, more interesting finding than the earlier blanket "fragmented is faster"
observation, and is now backed by actual task telemetry rather than plausible speculation.

**Remaining open item carried forward from Section 7.3 (point 5): the larger-scale
confirmatory run (SF10/SF100) has still not been done.** This has become slightly less
urgent now that Phase 2J provides a real mechanistic explanation (parallelism-vs-overhead
tradeoff is a more scale-robust kind of claim than a bare empirical ranking), but a
reviewer could still reasonably ask whether the *specific* crossover point observed here
is an SF1/page-cache artifact. Recommendation: deprioritize below the Phase 3C
prerequisites in Section 7.5, but do not drop entirely — flag as a "strengthens the paper
if time allows" item rather than a blocker.

### Phase 3A — Concurrent workload interference (the actual core research question)

**This is the project's first direct evidence on its actual thesis**, not motivating
background. Foreground (TPC-H queries) and background (Iceberg `rewrite_data_files`
compaction) workloads run concurrently through the same Spark Thrift Server application,
under both FIFO and FAIR scheduling (see Section 6.3, now resolved). 22 cycles (2 warmup +
20 measured) per scheduler condition; 528 query executions + 44 compaction executions
total. A real engineering problem was correctly diagnosed and fixed: the original
job-group-based synchronization for detecting "has compaction actually started" failed
because Spark Thrift Server overrides JDBC job-group properties with generated UUIDs —
fixed by polling the Spark REST API for any running job with active tasks instead, since
foreground queries are deliberately withheld until maintenance detection succeeds. This is
a good example of the same "identify the layer, make the smallest fix" discipline from
Section 9, applied correctly under real debugging pressure.

**Validation:** control table confirmed unchanged throughout (6,001,215 rows, ~16 files);
Spark event logs confirmed pool assignment actually happened as configured, not just
assumed; **100% of concurrent runs showed full temporal overlap** with the maintenance
operation — this is an important and easily-overlooked validation step, since without it
"concurrent" runs could silently have been runs where compaction had already finished
before the query even started.

**Results (Query Interference Ratio, $QIR = (T_{concurrent} - T_{baseline})/T_{baseline} \times 100$):**

| Condition | Mean QIR | 95% CI | Test | Effect size |
|---|---:|---|---|---|
| FIFO | +10.38% | [+6.94%, +13.82%] | Wilcoxon p=0.00161 | $d_z$=1.17, r=0.81 |
| FAIR | +12.77% | [+10.54%, +14.99%] | paired t p<0.00001 | $d_z$=2.50 |
| FIFO vs FAIR (direct) | — | — | t p=0.167, Wilcoxon p=0.211 | $d_z$=−0.32 (n.s.) |

Query-level FIFO interference ranged from +20.95% (Q14) down to a non-significant +0.78%
(Q12) — i.e., interference is real, large, and **workload-dependent**, not uniform across
query types. This per-query heterogeneity is itself an important finding: it directly
supports the project's premise that a *learned*, context-aware timing decision has real
value over a blanket "always defer during any concurrent activity" rule, since some
queries (Q12) show essentially no interference and wouldn't need deferral at all.

### Phase 3B — Predictive modeling of interference

12 configurations (3 fragmentation levels × 2 workload intensities × 2 scheduler modes),
4 measured reps each, 168 paired trial observations. **Anti-leakage design correctly
separates prediction-time features** ($X_{pred}$: fragmentation state, table size,
pre-execution CPU/memory/disk utilization, baseline duration, workload/scheduler
metadata) **from post-execution telemetry**, which is excluded from scheduler input by
design — this is the right discipline and should be maintained strictly through Phase 3C.
Validation uses GroupKFold by `config_id` rather than random splitting, correctly avoiding
same-configuration leakage between train/test.

**Results:**

| Model | Result |
|---|---|
| Ridge Regression | MAE 6.91%, RMSE 8.86% |
| Lasso Regression | MAE 7.35%, RMSE 9.19% |
| Random Forest Regressor | **MAE 5.38%, RMSE 7.34%** |
| Quantile Regression (q=0.95) | Pinball loss 0.89 |
| Random Forest Classifier (SLA>10% QIR) | Accuracy 78.2%, **ROC-AUC 0.531** |

**The classifier's near-random ROC-AUC (0.531) is correctly flagged by the team as a
serious problem, not glossed over — this self-diagnosis is exactly right and should be
preserved in tone through to the paper.** See Section 7.5 for the disposition
recommendation (retain as an explicit, diagnosed negative result — do not silently repair
or drop).

---

## 7.5 Critical Review: Proposed Phase 3C (Uncertainty-Aware Scheduling Policies)

Full detailed answers to the team's ten explicit review questions are the canonical
version of this review (kept in team chat/email history); this section records the
consolidated conclusions and required prerequisites for the working record.

**Overall verdict: conditionally justified to proceed, not yet justified to claim a
validated result.** Phase 3A/3B provide real, formally-tested evidence of interference
(large effect, workload-dependent) and a real predictive signal above the individual
Ridge/Lasso baselines (Random Forest MAE 5.38%). That is enough to prototype Phase 3C
policies. It is not enough to claim those policies *work* yet — with only 12
configurations, policy evaluation is currently evaluating generalization across
essentially no diversity.

### Required prerequisites before Phase 3C results can be presented as validated

1. **Out-of-distribution confirmatory test — highest priority.** Test the trained model
   against at least 2–3 genuinely new configurations outside the original 3×2×2 grid
   (e.g. a fragmentation level outside {50,200,500}, a workload mix outside the two
   tested intensities). This is the *only* experiment that directly tests the project's
   actual thesis — whether the model knows when it doesn't know, and correctly falls back
   — as opposed to "can we predict interference," which is necessary but not sufficient.
2. **Quantile-model calibration check.** The q=0.95 model has not been validated for
   actual coverage (does the predicted upper bound contain the true QIR ≥95% of the time
   on held-out data?). Until this is checked, calling Policy 5 "uncertainty-aware" is an
   overclaim — the team's own Section 18 correctly identifies this risk in principle; this
   is the concrete test that resolves it either way. Consider a proper conformal
   prediction wrapper for a distribution-free calibration guarantee, rather than relying
   on the quantile regression's calibration alone.
3. **Leave-one-configuration-out CV (LOCO-CV)** for policy evaluation, with **per-fold
   results reported**, not a single pooled average — the variance *across* held-out
   configurations is itself an important part of the finding, and hiding it behind a mean
   would understate a real limitation a reviewer will ask about directly.
4. **Two additional baseline policies**, both currently missing: (a) a naive
   fixed-threshold heuristic on raw prediction-time features alone (no model), structurally
   equivalent to AutoComp's own off-peak-deferral heuristic, and (b) a random RUN/DEFER
   coin-flip policy as a sanity floor.
5. **A trivial-baseline comparison for the regression result** (e.g. "always predict the
   training-fold mean QIR") — MAE 5.38% needs a reference point to be interpretable, and
   this is currently missing from the writeup.
6. **Maintenance-starvation tradeoff actually quantified per policy** (not just listed as
   a metric to track) — a policy achieving low interference by rarely running maintenance
   at all is not a contribution; the paper needs a number showing the best policy's actual
   position on this tradeoff.

### Specific flags

- **Possible circularity risk**: the SLA label (`QIR > 10%`) and Policy 4/5's thresholds
  both key off similar quantities. Given the classifier is near-random (AUC 0.531), verify
  explicitly that Policy 4/5's apparent performance is driven by the (working) regression
  model and not silently inherited from the (broken) classifier — run this as an explicit
  ablation, don't assume it.
- **SLA classifier disposition: retain as an explicit, diagnosed negative result.** Do not
  quietly repair-then-present-only-the-fixed-version (risk of unconscious p-hacking) and
  do not drop it. Run the confusion-matrix/precision-recall/PR-AUC diagnostics already
  planned in the team's own Section 17, report what's found either way, and keep the
  diagnostic narrative in the paper — a reported, explained failure is more credible to an
  A-venue reviewer than a suspiciously absent result.
- **Phase 3B's reduced repetition count (4 reps vs. Phase 2G's 20) is not yet discussed**
  anywhere in the update — worth explicitly checking whether per-configuration QIR
  variance (from only 4 reps) is small relative to across-configuration variance, since if
  not, some of what the Random Forest is "learning" could be per-config measurement noise
  rather than real signal.
- **FIFO-vs-FAIR non-significance (p=0.167) is well-hedged but should distinguish "no
  effect" from "insufficient power to detect a small effect"** in the eventual paper —
  these are different claims (see Section 6.3's note on this same result).

**Bottom line for the team:** proceed with Phase 3C implementation — the underlying
evidence base is real and the anti-leakage/validation discipline so far has been
consistently good. But budget time for the six prerequisites above before treating any
Phase 3C policy comparison as a presentable result, and prioritize items 1–3 as the
minimum bar, not all six as equally urgent.

---

## 8. Explicit Non-Goals for the Current Phase

To keep scope discipline, the following are deliberately **not** being done yet (per the
current handoff), and should not be started until the phases above them are validated:

- Regenerating or modifying the TPC-H dataset
- Downloading additional datasets (CAB workload streams, Alibaba traces) beyond cloning
- Downgrading Spark or Iceberg versions
- Modifying Spark or LST-Bench source
- Running the stock LST-Bench `W0` workload or SF1000
- Running CAB-generated workloads
- Using the Alibaba trace data
- Implementing any compaction/maintenance logic
- Creating fragmentation scenarios
- Building the ML prediction model
- Building the RL/scheduler component
- Running any control/treatment experiment

---

## 9. Working Principle for Environment Changes

> If something fails: identify the layer → reproduce the failure → inspect
> configuration/source → make the smallest change → revalidate.

Avoid broad changes to "just get something working" — this environment has been validated
layer by layer (Spark alone → Iceberg alone → JDBC alone → LST-Bench on top), and that
discipline should continue. Specifically avoid: changing pinned versions, reinstalling
Spark, replacing Iceberg, modifying upstream LST-Bench, creating duplicate datasets, or
introducing services not already justified above.

---

## 10. Open Decisions Log (all [TBD] items, consolidated)

1. Confirm all team members are pinned to Spark 3.3.4 / Iceberg 1.4.3 before Phase 1 work
   is distributed across the team.
2. Consider relocating the project root off a space-containing path before parallel work
   scales up (currently worked around per-service, not fixed at the source).
3. Decide target scale factor(s) for the actual Phase 2/3 interference sweeps (SF1 is a
   plumbing-validation dataset only). **Still open** — deprioritized per Section 7.4 (Phase
   2J's mechanistic explanation reduces urgency somewhat) but flagged as a
   "strengthens-the-paper-if-time-allows" item.
4. ~~Resolve Spark Thrift Server scheduling mode (FIFO vs. FAIR vs. separate
   applications) before building the Phase 2 control/treatment harness.~~
   **✅ RESOLVED via Phase 3A — see Section 6.3.** No significant FIFO/FAIR difference
   found; FIFO can be the default going forward.
5. Finalize the interference-cost metric definition. **✅ RESOLVED** — Query Interference
   Ratio (QIR) defined and used throughout Phase 3A/3B, see Section 7.4.
6. **Alibaba cluster-trace-v2018 acquisition is currently blocked** (survey-gated
   download link non-functional; this is a known, long-standing upstream issue, not a
   local configuration problem — see Section 5.3.1 for full resolution plan and fallback
   options). Still not urgent — not yet needed by any active phase.
7. ~~Re-run the fragmentation/compaction lifecycle experiment with a proper noise-floor
   baseline, more reps, realistic compaction target, and run-order randomization.~~
   **✅ RESOLVED via Phases 2F/2G/2H — see Section 7.2.**
8. ~~Add effect sizes and a multiple-comparisons correction to the Phase 2H statistical
   pipeline.~~ **✅ RESOLVED via Phase 2I — see Section 7.4.**
9. ~~Verify the parallelism explanation using actual Spark task-level telemetry.~~
   **✅ RESOLVED via Phase 2J — see Section 7.4.**
10. Run at least one confirmatory physical-layout comparison at a larger scale factor
    (SF10 minimum). **Still open, deprioritized** — see item 3 above and Section 7.4.
11. ~~Time-box the physical-layout characterization work and move to the actual core
    research problem.~~ **✅ RESOLVED** — team pivoted to Phase 3A/3B, which now
    constitutes the project's first real evidence on its actual thesis. Good scope
    discipline demonstrated.

### Current active open items (Phase 3C prerequisites, per Section 7.5)

12. **[Highest priority]** Out-of-distribution confirmatory test: evaluate the trained
    Phase 3B model against 2–3 genuinely new configurations outside the original 3×2×2
    grid, to directly test whether the model (and eventual uncertainty layer) degrades
    gracefully or correctly signals low confidence outside its training distribution.
13. **[High priority]** Calibration check for the q=0.95 quantile model — verify actual
    coverage on held-out data before using the term "uncertainty-aware" for Policy 5.
    Consider a conformal prediction wrapper instead of relying on quantile-regression
    calibration alone.
14. **[High priority]** Leave-one-configuration-out CV (LOCO-CV) for Phase 3C policy
    evaluation, with per-fold results reported (not just a pooled average).
15. Add two missing baseline policies: a naive fixed-threshold heuristic on raw
    prediction-time features (no model), and a random RUN/DEFER policy as a sanity floor.
16. Add a trivial-baseline comparison for the Phase 3B regression result (e.g.
    mean-QIR-predictor) — MAE 5.38% currently has no stated reference point.
17. Quantify the maintenance-starvation tradeoff numerically per policy in Phase 3C, not
    just as a tracked metric category.
18. Diagnose and explicitly retain the Phase 3B SLA classifier's near-random performance
    (ROC-AUC 0.531) as a documented negative result — do not silently repair-and-replace
    or drop it. Run the confusion-matrix/precision-recall/PR-AUC analysis already planned.
19. Check whether Phase 3B's reduced repetition count (4 reps vs. Phase 2G's 20) means
    per-configuration QIR variance is large relative to across-configuration variance,
    which would suggest the regression model is partly fitting measurement noise.
20. In the eventual paper, distinguish "FIFO vs FAIR shows no effect" from "insufficient
    statistical power to detect a small effect" for the p=0.167 non-significant result —
    these are different claims.

---

## 11. Change Log

- **[Phase 0]** Environment, TPC-H SF1, Iceberg catalog, and JDBC chain validated
  end-to-end. LST-Bench built. Smoke-test configuration in progress.
- **[Phase 0 → complete]** LST-Bench → JDBC → Thrift Server → Spark → Iceberg → DuckDB
  telemetry chain fully validated. Phase 0 marked complete; Phase 1 (baseline workload
  variance) is next.
- **[Alibaba trace]** Survey-gated download link for `cluster-trace-v2018` (and v2017)
  is non-functional. Confirmed via upstream GitHub issues that this is a known,
  long-standing problem (issue #93 open since 2021), not local misconfiguration.
  Resolution plan and fallback options documented in Section 5.3.1. Not currently
  blocking active work — revisit before Phase 2.
- **[Post-Phase-0 team update]** Team ran a fragmentation → performance → compaction →
  performance lifecycle experiment (16 → 200 → 1 files) in place of the scoped Phase 1
  noise-floor baseline. Infrastructure and data-integrity validation for this experiment
  is solid (checksummed, isolated experiment table, control table untouched). However,
  the experimental design has validity problems — no noise-floor baseline, n=3 reps with
  no reported variance, and an unconfigured (likely default/no-target) compaction call
  that produced a single 156MB file — that mean the reported percentage differences
  between states should not yet be treated as findings. Full assessment and fix-forward
  plan added as Section 7.1. Reworked baseline + increased repetitions + a properly
  targeted compaction re-run should happen before the team's proposed file-count sweep
  (Phase 3 in their numbering) begins.
- **[Phases 2F–2H]** All five items from the Section 7.1 fix-forward plan directly
  addressed: 20-rep noise floor established (Phase 2F, workload CV 3.25%), counterbalanced
  three-state comparison with realistic 64MB compaction target run (Phase 2G: fragmented
  7.458s < compacted 10.677s < control 11.616s), formal Shapiro-Wilk + Wilcoxon
  statistical testing added (Phase 2H). Full validated results in Section 7.2. Critical
  review against A-conference standards added as Section 7.3 — core methodology is sound;
  remaining gaps before paper-ready are effect sizes, multiple-comparisons correction,
  mechanistic (task-level) verification of the parallelism explanation, and a
  larger-scale confirmatory run. Team explicitly advised to time-box further physical-
  layout work and pivot to the core interference-harness research problem.
- **[Phases 2I–3B]** Effect sizes and Holm-Bonferroni correction added (Phase 2I),
  resolving Section 7.3 points 2–3. Task-level telemetry mechanistically confirmed a
  parallelism-vs-overhead tradeoff explanation, with a well-handled reconciliation of an
  initial apparent contradiction between environments (Phase 2J), resolving Section 7.3
  point 4. Team pivoted to the actual core research question: Phase 3A directly measured
  concurrent query/compaction interference under FIFO and FAIR scheduling (528 query +
  44 compaction executions; FIFO QIR +10.38% p=0.00161, FAIR +12.77% p<0.00001, no
  significant FIFO/FAIR difference), resolving the long-open Section 6.3 scheduling-mode
  question with real evidence. Phase 3B built an anti-leakage-correct predictive model
  (GroupKFold by config_id, 168 paired observations, 12 configurations) achieving
  MAE 5.38% QIR (Random Forest) but with a near-random SLA classifier (ROC-AUC 0.531,
  correctly self-flagged as a problem rather than hidden). Full results and a ten-question
  critical review of the proposed Phase 3C (uncertainty-aware scheduling policies) added
  as Sections 7.4–7.5. Verdict: conditionally justified to proceed to Phase 3C
  implementation, not yet justified to present validated policy results — six concrete
  prerequisites identified (out-of-distribution test, quantile calibration check,
  LOCO-CV with per-fold reporting, two missing baselines, trivial-baseline comparison for
  the regression, and quantified starvation tradeoff), tracked as open items 12–20.
- **[Phase 6 Master Run Audit (RUN_002) & Pivot to Methodology v2.1]** 20-hour live master
  evaluation completed on cluster node `worker3` (SF100, 60M rows). Infrastructure proved
  100% stable with zero crashes. However, comprehensive forensic audit (internal data
  analysis and external peer review) identified 5 critical validity flaws: (1) unmodeled
  query heterogeneity (3.5s vs 49s queries) caused a 22–25s MAE and prediction inversion
  ($\text{pred}_b > \text{pred}_a$), (2) 144 of 225 compactions were 0.15s no-ops on tables
  with $\le 35$ files, (3) training data lacked fragmentation variation (file count trapped in
  [32, 40]), (4) P95 latency reduction was an artifact of 60s window binning, and (5) statistical
  discipline regressed (N=12 conformal test split, N=1 run anecdote, post-hoc SLA shift).
  Upgraded to Methodology v2.1 (documented in `methodology_v2_cost_benefit.md` Section 7)
  mandating `query_id` feature encoding, dynamic fragmentation sweeps during training, minimum
  10-file compaction actuation guardrails, a priori SF100-grounded SLA (6.75s), competitive
  threshold baselines (50-75 files), and multi-trial counterbalanced evaluation with the
  Phase 2H/2I statistical testing pipeline.

---

## 12. Append-only evidence reconciliation —2026-10-14

This appended record supersedes conflicting current-status claims above without
rewriting historical entries. `docs/methodology_working_doc.md` is the continuing
methodology ledger; `updated_methodology_working_doc.md` keeps an append-only
cross-reference. Every major implementation, collection, model or evaluation job
must append its rationale, protocol/code revision, pipeline change, provenance,
raw artifacts, checks/failures, limitations and next gate. Earlier prose is not
automatically verified or suitable for the paper's Results section.

### 12.1 Research scope and corrections to historical claims

The target is forecast-aware timing of existing Iceberg compaction: act now or
wait based on future demand and measured action consequences, with uncertainty
and explicit residual query/maintenance work. No new compaction algorithm is
claimed. Separate A/B versus a shared conditional cost estimator is an empirical
architecture comparison; three models is not the contribution by itself.

Historical scheduler success, distribution-free safety, novelty exclusivity and
fixed-SLA/threshold conclusions in older methodology/master sections are not
accepted current evidence. Synthetic fallbacks, insufficient calibration blocks,
legacy no-op labels and post-hoc thresholds cannot establish policy benefit.
Old studies not re-audited under the current raw contracts remain historical
reports, not independently reproduced findings. Primary-source novelty and faithful
baseline reproduction remain required. The prior SF10060M-row statement is wrong
for the audited raw lineitem:600,037,902rows. No old paragraph should be copied
into paper claims without the relevant current evidence and limitations.

### 12.2 Data and actual runtime

TPC-H SF1 lineitem provides6,001,215verified rows and controlled benchmark SQL.
It is not an observed arrival trace. The prepared immutable source is
`local.experiment.integrity_sf1_20261014_0024`, snapshot2963541948322332238.
All eight raw SF1 tables matched source manifest bytes/rows on both computers.
SF100all-eight typed/lexical scans and raw size/count/hash comparisons passed;
generator/build provenance, relational integrity and clean readable large-table
preparation still gate scale claims. Source-only verification is not a physical
SF100 experiment. See dataset/resource readiness and typed-source review.

Snowset's complete archive was validated and a training-only selected warehouse
cohort independently audited:2,760,971actual arrivals, original identities/times,
about13.34observed source days. It has no SQL text. Current replay explicitly maps
arrivals to four custom SF1 lineitem SQL templates; it is not original Snowflake
SQL reproduction or the official full TPC-H query suite. No duration/resource
fields are used to infer missing SQL. Alibaba2017archive/task-arrival audits exist
but are not database SQL replay; no verified Borg replay integration exists.
Historical mathematical missing-trace fallbacks are retired/fail-closed.

Actual execution is worker3, Spark3.3.4/Iceberg1.4.3/Java8, local[16],16GiB driver,
i7-6950X10cores/20threads/~64GB RAM. This is one machine, not a distributed cluster.
The warehouse path contains nfs-storage but observed backing storage is ext4.
Live services were preserved. All validations/runs below used real artifacts or
real SQL on worker3; newly launched jobs use nohup and retain logs/PIDs. Detached
clients/observation threads finish naturally; no cancellation/table deletion.

### 12.3 Measurement pipeline changes

Replaced legacy fabricated/no-op-derived labels with exclusive durable JSONL
physical events, actual execute/fetch monotonic clocks, UUID-tagged SQL and raw
Spark REST job/stage/completed-task evidence. Intent/logging overhead is separate
from measured client service; service is not pure CPU execution time. Measured
host histories use exact60/300-second windows, available sample frontier,95%
coverage and2-second gap/freshness gates. Cross-Python float reconstruction uses
explicit ordered sums rather than weakening evidence tolerances.

Queries bind available snapshot/file inventory to actual SQL and results. Actions
bind fresh pre-action refresh/history/files and windows to the actual rewrite
call, including2-second actual-call metadata age. Useful rewrite/file/row
conservation, original/final bidirectional EXCEPT ALL and source results gate
success. Completed task-lifetime overlap is not simultaneous CPU-use proof.
Query-first/rewrite-first use dedicated sessions and actual submission/active-stage
proof. No missing overlap is manufactured or clipped into a positive cost label.

Offered/queued/dispatched/completed/failed events preserve original source spacing,
scheduled/actual/durable clocks, source IDs, measurement UUIDs and exclusive client
ownership. FIFO, complete source coverage, result/time/task binding and boundary
state conservation are audited. No thinning/time compression, quiet-tail padding
or completion-driven next-arrival scheduling. At horizon no further dispatch;
in-flight work completes naturally, queued identities remain debt. Actual observer
lateness and retrospective transition-clock census are reported separately.

Common-horizon arms use fresh isolated clones, matched offered source windows and
initial measured file row/byte signatures, verified original/final logical content
and shared checkpoint schedule. Queries pin the latest available controller
snapshot; post-commit publication/query-refresh lag and extra instrumentation are
recorded limitations, not assumed zero. Own registered metadata/maintenance work
is permitted; unrelated Spark work fails the gate. Controller/cohort pin code and
configs, audit every episode before a dependent one, retain all failures and
unattempted counts. Documentation-only commits may sync without changing run code.

### 12.4 Completed current evidence, with limitations

Four initial Q0–Q3 matched measurement pilots passed strengthened raw correctness
exports. They are diagnostics, not a cost-training corpus. Earlier Q1 lacked
pre-action context and Q0 used an immutable pre-warmup inventory; those omissions
are retained, not retroactively upgraded. Repaired Q2/Q3 include fresh action state.

Four real Q1 action-order episodes (query-first/rewrite-first, reverse-balanced)
passed row/result/task/raw export gates,16files to1 with unchanged6,001,215rows.
Signed during-minus-bracketed contrasts varied, and before/after control drift was
on a similar scale. No stable variance/causal-cost/winning-order claim follows.
Four no-maintenance controls subsequently audited showed middle-minus-bracketed
contrasts−67.10,−73.47,−68.00,−31.27ms without rewrite, confirming that bracketed
contrast alone is not a credible causal label. The first control runner failed
at an auditor missing-summary-field bug; original failure preserved, corrected
raw first-block audit passed, only three unattempted blocks then executed.

The first real source-bin queue screen offered113arrivals;41completed inside its
60-second horizon,1finished naturally afterward and71remained queued. Raw post-run
audit and full package hash mirror passed. This measures overload of the declared
single-client mapped workload, not the original warehouse or server generally.

Six60-second common-horizon episodes compared no maintenance/now/later in reverse
order,2per arm. All6passed raw/physical audits; initial164,550,027bytes/16files and
6,001,215rows matched. Active arms ended at1file/163,892,210bytes. Now rewrites
13.63/13.53seconds had zero overlapping query tasks; later14.89/14.57seconds
exposed14/13queries. Within-horizon completed counts: none41/39, now41/37,
later41/39. These do not show a robust throughput winner. Two episodes/arm,
one minute, tiny scale, imposed mix and time/cache/instrumentation effects prevent
publication-strength causal or calibrated-cost claims. Full review re-audited
all6packages and identified37arrival-aligned completions common across arms.

The longer registered cohort used three training-only5-minute windows with718/
762/744actual arrivals and rotated arms,9planned. Mapping source audits passed.
Only its first no-maintenance arm passed:718offered,245completed at horizon,
1finished afterward,472queued. Second now arm stopped when durable observation
logging crossed the horizon before dispatch;7episodes unattempted. This is a
boundary bookkeeping failure, not a bad-compaction outcome. Failed arm/table/logs
were not reclassified or discarded. Code now supports an explicit preregistered
prepared-but-not-dispatched outcome that keeps the request queued, while requiring
no SQL request/dispatch and actual crossing clock. Compilation and passed-arm
regression passed; the new path still needs a real registered recovery run. No
new physical work began after that cohort's18:30IST cutoff.

### 12.5 Forecast/model state and paper claim boundaries

One-warehouse Snowset arrival forecast diagnostic beat the daily seasonal MAE
baseline by about17.75/25.41/24.45% at1/5/10minutes, independently reconstructed
from saved predictions and source prefixes. This is a short, dependent diagnostic;
not a CPU/load predictor, calibrated90% guarantee, deployed Model C or scheduler
benefit. Three calibration source-days cannot justify the claimed daily-block
conformal coverage. Preserve warehouse/observation limits and no future leakage.

Strict separate A/B training code exists; an opt-in shared action-conditioned
candidate uses the same splits/hyperparameters and per-regime/query gates.
Successful fitting of the shared path remains unvalidated. No current cost model
is trained/accepted from these diagnostics, no calibrated scheduler is deployed,
and no arbitrary fixed defer penalty/intensity/small-file threshold/SLA is inserted.
Legacy trainer schema is intentionally incompatible with diagnostic exports.

Next end-to-end milestone is the raw-verified query/rewrite/episode cost-candidate
export, reliable diverse collection, exploratory model comparison, independent
chronological calibration/test and then physical temporal-policy evaluation.
See `learned_cost_model_implementation_plan.md`. Exploratory fitting is distinct
from acceptance; forecasts must ultimately improve held-out scheduling, not just
arrival MAE. Missing experiments/labels stay missing; failed attempts stay in the
inventory. A paper needs stronger workloads/scales, independent uncertainty,
faithful baselines, primary-source novelty and explicit negative findings.

### 12.6 Reproduction and append policy

Evidence index: `daytime_review_2026-10-14.md`, `overnight_review_2026-10-14.md`,
`common_horizon_cohort_review_2026-10-14.json`,
`long_common_horizon_partial_review_2026-10-14.json`,
`snowset_queue_diagnostic_review_2026-10-14.json`,
`no_maintenance_partial_review_2026-10-14.json`,
`no_maintenance_recovery_review_2026-10-14.json` and the raw results/packages
referenced there. Phase implementations/configs live under phase6-live-evaluation
and docs/experiment_protocols. SHA-pinned inputs/raw clock/result/task re-audits,
not a prose status flag, determine accepted evidence.

Major revisions: c7eeaf6order pilot;5f2a554null/shared candidate;04a57c4null audit
repair;bb26eaenull review;2107004queue/mapping; b900c6bactual queue registration;
9e47579queue evidence;b8e83fccommon horizon;842e4dfsix-arm review/window selection;
5d25c00longer collection;f07c2d6boundary repair/failure review. Raw packages freeze
actual execution code/HEAD, including documentation-only revisions. Initial
seven-table physical byte fallback was verified; newer raw/code/result mirrors
do not imply every newer warehouse data file has a local byte backup.

Remote working-methodology had a dirty deletion of the final historical14-line
Phase6paragraph. Exact remote file/diff preserved in
`results/methodology_reconciliation_20261014/`; target-only stash reconciliation
will preserve that edit before fast-forward. No unrelated dirty files/archive are
staged or overwritten. Historic incorrect paragraph is retained locally as history
and explicitly superseded above; this is not an endorsement of its thresholds.
After each major job append current observations and limitations here. Never
silently edit earlier outcomes to match a new model or retroactively approve runs.

## 13. Cost-candidate data pipeline implementation —2026-10-14

Major job: start the complete collection-to-model milestone rather than another
standalone timing pilot. `export_physical_cost_candidates.py` and preregistered
`physical_cost_candidate_export_20261014.json` re-audit7successful common-horizon
arm packages, export observed query service, actual rewrite work/duration and
whole-episode throughput/debt into separate tables, and retain failed/unattempted
inventory. This entry records implementation; actual export completion/checks
will be appended separately after the detached worker3 run.

Prediction features are available pre-query measured host windows, actual query
identity/table files/rows/bytes, controller maintenance client-request pending
state and observed queue depth. Pending is known client intent/completion
availability, not a claim of simultaneous engine execution. Completed task overlap,
arm assignment, observed queue delays and boundary outcomes are diagnostic fields,
excluded from the predictor allowlist. Targets are raw execute/fetch service ms
and actual rewrite client duration/bytes; no synthetic interference penalty or
unobserved alternative-action target is produced.

Full offered-history60/300-second counts are absent when replay history is
incomplete; coverage flags preserve this cold start rather than padding zeros or
inventing normalized intensity. Whole raw/frozen verification dependencies and
input/output SHA256s are bound. Repeated and overlapping source intervals are
retained with exact source identities so future splits can group/purge them.
No calibration or scheduler acceptance follows from exporting candidate data.
These7episodes still lack diverse layouts/workloads and independent calibration.
Model-development fitting and calibrated deployment are separate next gates in
`learned_cost_model_implementation_plan.md`. All validation/export execution is
on worker3 under nohup using actual recorded physical artifacts, no dummy data.

Remote target-only methodology deletion was preserved before synchronization in
stash84709ace32daa6c1af22e66522cf2c3e4e86a2e8, with exact local file/diff fallback
under the reconciliation directory. Other remote dirty files and the unrelated
archive were untouched. Both methodology updates add lines only; original local
text remains as historical evidence, with corrections appended rather than removed.

## 14. Cost-candidate export completed and independently verified —2026-10-14

Registered implementation2cb68cd8d2af23103ea2e724f5ae0acce1d951ab pushed and
worker3 fast-forwarded; all5intended file SHA256s matched. Detached exporter
PID974140 completed naturally on actual successful source packages. Output
`results/physical_cost_candidates_20261014/`:489query observations,4actual useful
rewrite observations and7successful episodes. Failed second long arm excluded;
failed/unattempted cohort inventory retained. No synthetic augmentation or model
fitting. Query targets are raw actual service ms; rewrite targets are actual call
duration/work. Predictor allowlist excludes task-overlap outcomes, source/episode
identity, assigned arm and other diagnostic future/outcome fields.

Separate verifier PID977499 compiled and ran on worker3 under nohup. CSV targets,
pre-query feature clocks/table state/windows, source IDs, offered-history counts/
missingness and rewrite work reconstructed from raw events; artifact/source hashes
and coverage passed. Readiness report `physical_cost_candidate_readiness_2026-10-14.json`
records1connected source-overlap family and0fully observed300-second offered-history
rows.7physical episodes/489rows are not489independent experiments or multiple
independent trace families. Current data can guide exploratory engineering, not
independent held-out calibration or scheduler acceptance. Missing300-second demand
was not filled with zero; existing host300-second histories remain actually measured.

Full candidate tables/config/exporter/verifier-dependency code/manifest/round-trip
proof mirrored locally; sorted file/SHA256 manifest matched worker3. Original raw
packages remain separately retained. Both methodology files passed server-side
byte-prefix preservation checks againstf07c2d6and the exact dirty remote methodology
stash. Historical text/deletion history remained recoverable; all other dirty files
were untouched. Append proof snapshot is
`results/methodology_append_verification_20261014.json` (the2cb68cddoc version).

Next major job: recover boundary-safe collection with preregistered new tables/
cutoff and explicitly varied physical states, disjoint source-time families and
appropriate observed-history burn-in. Implement the new candidate-schema trainer
for exploratory A/B/shared/rewrite comparisons, then independent chronological
accuracy/calibration gates. Do not force legacy normalized intensity/small-file
fields into this data or assign before/after differences as causal penalties.
No physical restart after the prior18:30cutoff, no model trained/promoted, no
shutdown/cancellation/table deletion in this documentation/export job.

### 14.1 Persistent workflow requirement

Added root `AGENTS.md` to carry the user's append-only methodology, raw-evidence,
worker3 detached-validation, preservation and audited Git/sync requirements into
future repository work. This is a workflow change, not a scientific measurement
or model promotion. The canonical working ledger and updated-master pointer remain
append-only; no historic method text was removed. Future major jobs must append
rationale, pipeline changes, verified evidence/failures and limits here.

## 15. Overnight collection-to-model milestone authorized —2026-10-14/15

User authorized autonomous work until06:00IST on2026-10-15. Existing same-chat
15-minute heartbeat updated toACTIVE with that deadline, audit/repair-before-
dependency queue and quiet-on-unchanged notifications. Queue and morning evidence
ledger are `overnight_execution_plan_2026-10-15.md` and
`overnight_review_2026-10-15.md`. No new physical episode after04:45IST, no new
Spark/SQL/maintenance after05:15IST; active work/services preserved at cutoff.

The next larger job targets18fresh controlled arms over three disjoint actual
source windows and two named original layouts,10-minute source exposure to permit
real300-second offered histories, complete raw audit/export then exploratory
separate/shared/rewrite estimation. This is registration intent, not execution
success or accepted calibration. Models and training features remain raw/split
bound, no synthetic missing data/labels or hardcoded policy predictions. Data-scale,
SQL mix, single-host, precision and independent calibration limitations remain.
Append all launches/failures/checks/outputs below after actual jobs. Preserve
original failed cohorts, occupied tables and dirty/archive/stash evidence.

## 16. Overnight diversity collector implementation —2026-10-14

Implemented named original-file-count interventions on verified source rows and
strict raw layout-state binding. Comparison groups require identical workload/
layout parameters; initial row/byte file signatures now match within declared
layout groups, allowing intentionally different physical layouts across groups.
Defaults retain historical contracts; no old outcome/data silently changed.
New ten-minute source windows expose actual offered histories while retaining all
600seconds in workload/debt accounting. No generated demands or imputed history.

Worker3 detached compilation and raw regression of the actual accepted long
baseline passed. This does not validate new32file or boundary branches; registered
real collection is next. Immutable worker3 runtime checkout will protect active
code/config while main develops new-schema estimators. Overnight queue/review
record deadline/safety buffers and dynamic failure-first behavior. No model fit,
accepted calibration or scheduling result in this implementation job.

## 17. Longer-run engine evidence retention —2026-10-14

Actual prior246-query episode produced492Spark jobs/stages. To avoid losing early
evidence in longer retained-UI history, added a registered in-run REST checkpoint
that preserves completed query task payloads. Raw job/stage frames merge by actual
job ID and stage ID/attempt, retaining latest recorded fields and failed attempts;
no invented engine completion/time. Final task/overlap audit remains strict.

Checkpoint runs uniformly across arms with measured host/logging overhead, not
extra SQL or artificial demand. Its instrumentation effects remain a limitation.
Worker3 compilation and actual historical raw regression passed; new live archive
path awaits the registered physical matrix. No engine restart/retention-setting
change or retrospective repair of missing old evidence. Candidate export freezes
this verifier dependency with other actual runtime modules.

## 18. Registered overnight cost-collection matrix —2026-10-14/15

Prepared18fresh arms in six matched source-window/layout groups. Actual three
600-second training-window exports passed independent source coverage/spacing/
SQL mapping audits.16/32original-file candidates are declared verified-source /
two-local[16]-task-wave interventions on identical real rows; source/generator
provenance unchanged, actual parallelism bound to raw environment. Within each
group all three maintenance arms use identical workload/horizon/client/engine/
archive/boundary conditions. Layout signatures match within named layout groups,
not across intentionally different layouts. All original/final logical content
and useful rewrite/actual timing/task/window gates remain strict.

Code/config registration is not live-path acceptance. Opt-in boundary preparation,
midpoint engine archive and32file layout need real execution evidence. Runtime
will be an immutable sparse Git worktree, with canonical dataset/results links,
so later estimator implementation cannot modify active collector code. Original
failed/occupied tables remain; fresh identity matrix is not silent retry/promotion.
New episode cutoff04:45IST, new SQL cutoff05:15IST, automation stop06:00ISTOct15.
No accepted cost model/uncertainty/scheduler claim from registration.

## 19. Immutable overnight collection launched —2026-10-14

Setup/registration commit60e15ba9cbc3b0fc53173d45f9bae2481349f33e pushed/synced,
all intended file name/SHA256 manifests matched. Worker3 sparse detached Git
worktree `/tmp/capstone_overnight_runtime_20261015` freezes code/configs with
canonical dataset/results links; no existing data/service removed. New main-
checkout trainer development cannot change the active collector source/HEAD.

Detached coordinator PID1031940, launch20:07:27IST,18planned real arms. Actual
progress confirms initial baseline running, not success. Logs/raw/audits in
`results/sf1_overnight_cost_cohort_20261015` and per-arm `_01`..`_18` packages.
Estimated4.5–5.5hours; actual operation/audit times and gates govern outcome.
Automation wakes15-minute to audit/repair/continue, records failures and append-
only methodology, stops at06:00ISTOct15and leaves in-flight services/work running.
No heavy model fitting/backup alongside physical query windows; no trained or
calibrated model claimed at launch. Morning review records precise completed/
running/failed/unvalidated states and next scientific gates.

## 20. Candidate-schema exploratory estimators implemented (2026-10-14 evening)

Purpose: move from measured candidate labels to an auditable shared-versus-separate
cost-model comparison without inventing legacy features. Added
scripts/phase6-live-evaluation/train_candidate_cost_models.py. Requires SHA-bound
raw export/independent verification, artifact integrity, complete chronological
source-overlap-family partition and unique whole-episode family membership.
Training-only scaling/SQL encoding and median baselines; fixed preregistered
Ridge alpha1.0, no held-out optimization. Shared observed-client-pending feature,
conditional separate latency estimators and distinct measured rewrite-duration
regression. No counterfactual penalty, calibration or scheduler authorization.
Complete demand-history mode excludes early missing60/300s histories with UUID
inventory; no imputation. Negative predictions retained. Saved model bundle,
held-out row predictions, per-episode/query/layout/pending-state errors, settings,
versions/source hashes and not-fit states enable review.

At14:44UTC collection PID1031940 still active in immutable60e15ba runtime; first
of18episodes running. Main implementation does not change frozen collector code.
No fitting/new physical episode started by this job, no new observed model result.
Validation next: detached worker3 syntax check; successful end-to-end validation
requires completed diverse raw export and registered actual hashes. Existing
489query/4rewrite corpus has only one source family and cannot train/test this
protocol. Three planned families still insufficient for calibration/generalization.

## 21. Overnight matrix stopped on task-retention failure; evidence adapter repair

At14:55UTC coordinator1031940 had exited naturally. First baseline failed at final
live task retrieval: Incomplete task-attempt REST evidence; cohort status remains
0passed/1failed/17unattempted. Original nine-arm run still1passed/1failed/7unattempted.
No processes canceled, tables reused or labels exported. Actual raw diagnostic
results/overnight_task_archive_diagnosis_20261015.json reports497completed queries,
495task payloads including an empty final response for stages/5657/0/taskList?length=1.
Midpoint archives existed, but final execution still re-requested archived early
stages from Spark UI, and auditor selected the last response even if empty.

Repair: ArchivedTaskEvidence uses an actual complete successful stage-attempt raw
frame with unchanged task IDs; final collector requests live evidence only when
no complete archive exists. Raw auditor uses the same complete-frame selection.
No invented task frames, timing/attribution gates unchanged. Failed original
package remains failed regardless of diagnostic checks. Detached server raw
regression/archived-checkpoint validation next; then register new recovery cohort
identities and immutable revision before physical execution. Missing archives must
still fail. No cost fit/calibration result exists.

## 22. Fresh task-archive recovery matrix registration

Registered18fresh recovery episode/table/config identities in
sf1_overnight_recovery_cohort_20261015.json; unchanged three actual600s windows,
16/32layouts, rotated matched arms, boundaryv1/archive midpoint, cutoffs/gates.
Reason is specific evidence-reader defect, not favorable-outcome retries. Original
18matrix0passed/1failed/17unattempted preserved, no reuse of failed rows/tables.
Historical successful baseline raw regression passed under repaired reader on
worker3 (results/archive_adapter_regression_20261015.json). Detached actual failed
run midpoint task check saved archive_checkpoint_validation_20261015.json; this
certifies archived task availability only, cannot upgrade the failed episode.
Next gate: inspect checkpoint receipt, commit/sync/hashes, frozen recovery checkout
and detached launch if no competing work. Model fitting still blocked by diversity.

Recovery launch evidence: actual archived checkpoint247queries/741tasks passed on
worker3; failed original status unchanged. All23registered unitSHA256 matched
bothhosts at8a11a71eef51507dc4023763c9d2b67331b53b6e. Fresh frozen runtime
/tmp/capstone_overnight_recovery_runtime_20261015 at that revision, canonical
results/datasets symlinked. nohup coordinatorPID1068198 confirmed running15:12UTC;
log results/sf1_overnight_recovery_cohort_20261015_launch.log, progress/raw audits
in matching cohort directory and arms sf1_overnight_recovery_20261015_01..18.
Estimated first gate around21:00IST; full matrix around01:15–02:15IST if healthy.
No recovery result accepted at launch. Next wake audit progress before dependent
work; collection runtime frozen, heavy fitting/export waits for inactive collector.

## 23. Exploratory model reporting audit

While immutable recovery collection runs, audited trainer reporting. Added finite
positive registered regularization/boolean-history contract; test-target positive
check; family-level error groups; shared/separate comparison on exactly matched
held-out UUIDs with per-episode errors and explicit unpaired counts, no winner
selection. Bundles bind saved models/predictions/config/source by SHA256. Failed
fit gates save distinct timestamped failure receipts beside registration, without
reusing output or hiding partial bundles. No real fitting occurred or accuracy
claim made. Worker3 detached syntax validation next; model behavior still requires
actual diverse verified export. Heavy validation/fitting remains deferred until
physical collector inactive. Frozen recovery runtime unaffected by main edits.

## 24. First recovery ten-minute baseline passed actual raw gates

At15:40UTC coordinator1068198 active, second compact_now arm running since15:28:45.
Recovery01 no_maintenance passed physical and independent frozen raw audit:
1478offered,497dispatched/completed within horizon,981queued at boundary/final;
boundary observation125.599992ms late reported without changing registered horizon.
ResultSHA256 b51b5ee2c292cdb9dd79c508819bb077ce5c6b0246d7c277cbb60a6184bcacec;
eventsSHA256 5c7ad495767b4fe9487e831a2f03f22a7581cf208ef9f9228a9ebfdf160df828;
independent auditSHA256 a6d06880f6bf79b0d560fb6766707b0562593722e19782eaff06c1e6796e23e8.
Small immutable result/audit receipts mirrored locally with matching hashes; full
raw package/physical byte mirror deferred while active queries to avoid I/O load.
Logs/raw paths results/sf1_overnight_recovery_20261015_01 and matching cohort.

This validates archive-first evidence retrieval on an actual600s episode, not just
historical regression. It does not validate the32file/new-maintenance branches or
make this one family independent training/test/calibration data. Offered backlog
remains part of evaluation; no workload thinning or assumed zero deferred cost.
Original failed18matrix remains0passed/1failed/17unattempted; original nine-arm
1passed/1failed/7unattempted. No cost fitting/promotion. Next gates remaining raw
arms, matching layout/source groups, whole-family export and actual fit registration.

## 25. Maintenance task archival omission detected and repaired

At15:55UTC recoverycoordinator1068198 exited naturally15:45:13UTC:1passed/1failed/
16unattempted. Recovery02 compact_now failed final rewrite task retrieval with
Incomplete task-attempt REST evidence; query archive reader succeeded. No running
Spark jobs observed. Midpoint archive only processed trace_query statements, so
actual early rewrite tasks were not preserved before Spark UI eviction. This is
another instrumentation implementation defect, not evidence that compaction is
ineffective. No failed labels admitted, tables/processes/data preserved.

Extended uniform midpoint checkpoint to actual completed maintenance statements:
unique matching pre-action decision supplies fresh table, existing strict rewrite
job-group/table/client-time/task attribution certifies actual archived tasks. No
invented tasks or relaxed successful/no-retry/coverage gates. Running/uncompleted
maintenance still must certify at final audit. Same midpoint overhead applied to
all arms, instrumentation workload remains a limitation. Next server detached
syntax/historical active-arm regression then new recovery identities/registration;
prior failed ninearm1/1/7, original overnight0/1/17, firstrecovery1/1/16 stay intact.
No fitting or calibrated scheduler claim. Model export waits for independent data.

## 26. Completed-maintenance archive validation and fresh recovery2 registration

Worker3 detached validation invokes actual checkpoint implementation on saved real
successful compaction arm02 raw events/jobs/stages/task payloads, no generated
measurements or dummy data. Receipt results/maintenance_checkpoint_real_validation_20261015.json;
script results/validate_maintenance_archive_real_20261015.py. Historical raw audit
also passed results/maintenance_archive_regression_20261015.json. These validate
saved-evidence code path, not new live midpoint success. Registered recovery2
18fresh table/episode identities, same three source windows/two layouts/rotated
arms, uniform midpoint query+maintenance archive, boundaryv1 and23:15/23:45UTC
cutoffs. Original failed statuses/counts unchanged; no favorable-outcome selection.
No active physical/Spark jobs at16:10UTC. Next immutable launch after checkpoint
receipt and Git/file agreement, then actual live audits before candidate export.

Recovery2 launched16:12UTC undernohup PID1130786 confirmed alive, frozen
/tmp/capstone_overnight_recovery2_runtime_20261015 at
dd4ebf5a1c0cdad2f7a6e120f40ab0489831cd9f. All23registration filesSHA256 agree
local/worker3. Log results/sf1_overnight_recovery2_cohort_20261015_launch.log;
progress/audits matching cohort directory, arms sf1_overnight_recovery2_20261015_01..18.
Saved real checkpoint query+maintenance validation passed, not livepath approval.
First check approximately22:00IST; full matrix02:15–03:15IST if healthy. No
recovery2episode accepted yet, no learned model fit. Inspect nextwake before work.

## 27. Recovery2 telemetry freshness failure and serialized preparation repair

Recovery2 exited16:28:42UTC,0passed/1failed/17unattempted; no activeSpark16:40UTC.
Actual saved diagnostic results/recovery2_freshness_diagnosis_20261015.json:
494completed queries, one query's60/300s samples age2.179098077s atsubmission,
observation-to-call1.392276840s versus intent-only I/O0.041765266s. Strict2s gate
correctly rejected run. Archive/log interleaving is a suspected contributor, not
proved causal; no retrospective timestamp correction or max-age relaxation.

Implemented opt-in serialized_durable_submission_v1 preparation: reentrant event
log lock covers refreshed actual telemetry windows, durable observation, dispatch,
intent and actual execute-start stamp only; releases before SQL RPC/fetch so offered
arrivals/archive/telemetry aren't blocked for service duration. Same raw chronology,
2s freshness, FIFO/cutoff and all physical/task gates still required. Registered
boundary abandonment leaves queued/no intent/noSQL as before. New physical path
requires fresh protocol/live validation; original frozen runtimes unchanged.
Next detached server syntax/raw regression, inspect preparation error accounting,
register fresh identifiers before launch. All prior failed counts unchanged;
no model fit/labels from failed package. Avoid blind repeat without causal repair.

## 28. Submission lock-order audit and recovery3 registration

Before live use, found ledger->log versus preparelog->ledger inversion. Queue state
and durable log now share one reentrant lock; RPC/fetch never hold it. Before-
dispatch preparation failure leaves queued rather than inventing a failed SQL
transition. Shared cohort check binds preparation contract across all arms.
Registered18fresh recovery3identities with serialized_durable_submission_v1,
existing boundary/archive contracts and same source/layout/order/cutoffs/gates.
Prior frozen runs/counts unchanged. Server detached syntax/historical actual raw
baseline regression next, then frozen runtime launch if checks pass. This lock
change alters instrumentation scheduling; actual generator lateness/backlog remain
reported, not assumed original SQL replay or timing-neutral causal measurement.

Recovery3actual launch16:57UTC (22:27IST), nohup PID1177256 confirmed alive,
frozen /tmp/capstone_overnight_recovery3_runtime_20261015 at
c93f13ffb77de1114fb6bcbeaa60d9faf0a6acfb; all26unitSHA256 agree bothhosts.
Historical actual recovery01raw regression passed
results/serialized_preparation_raw_regression_20261015.json. Live serialized
submission behavior not yet validated. Log
results/sf1_overnight_recovery3_cohort_20261015_launch.log, matching cohort progress/
audits and raw arms sf1_overnight_recovery3_20261015_01..18. Firstcheck22:45IST,
fullestimate03:00–04:00IST if healthy; cutoffs unchanged. No learned-model fit.

## 29. Serialized preparation first live baseline passes

At17:25UTC coordinator1177256active; recovery3baseline01passed physical+independent
frozen raw audit, strict2s telemetry age unchanged.1478offered,506dispatched and
ultimately completed,972queued final. Actual boundary observer73.220066ms late:
505completed/1dispatched/971queued/1offered at that recorded census. These census
counts are not an exact-time completion count or throughput winner. No request
thinned; in-flight finished naturally. compact_now02running since17:13:56UTC.
Live submission serialization now passed once; maintenance/archive/32file paths
still require their own actual gates. No family-independent model fit/calibration.
ResultSHA15bda7ede5e00397a650fe35174a1479797d8b248f41afa57e0cf212424b938f;
eventsSHA2c10774a71162efb9433eb61a98951fcf944cde056b06f116fd68c7cdeafb1b2;
frozen auditSHA479ded45a36f2cca033ebbf46caf7b9f48b152412501b884bbc88f010aff4e1c.
Small immutable result/audit receipts mirrored matching hashes; bulk evidence/bytes
wait until no active query collection. All prior failed counts remain unchanged.
Next inspect current action-arm raw gate before further export/fit. No heavy fit
or second collector started concurrently, no service/table stopped or deleted.

## 30. Immediate compaction live archive/physical audit passes

At17:40UTC recovery3coordinator1177256active. Arm02compact_now passed physical
and independent frozen raw audit including actual maintenance task evidence;
1478offered/509ultimatelycompleted/969queued final. Recorded boundary observer
11.735593ms late,508completed/1dispatched/969queued census. Deferred03running
since17:30:36UTC. Near-identical baseline/action counts are descriptive only, no
causal compaction benefit or model winner. Current one sourcefamily/one layout
still not independent calibration/test evidence. Live maintenance archive repair
now validated once under unchanged raw gates; later/32file branches still pending.
ResultSHA661de18684bdd69aefb8c6539b34fab8ffa376c75fb20c2f108c879f2f959846;
eventsSHA004e61fc09b232986280ac867fe209ddcdca84f60a76fe1ac5c9df10826aa08a;
auditSHA9f7acc9761f7fc0ed26aefa02a3bc1adfe354bc1133babd22fbbc7c8143fffdb.
Small result/audit receipts mirrored exactly; full raw/byte mirroring and expensive
candidate export/fit deferred during physical collection. No failed prior status
changed, no new concurrent run, no accepted learned cost model/scheduler.

## 31. First matched three-arm recovery group complete

17:55UTC recovery3PID1177256active. Source_day_0_files_16 matched group01/02/03
allpassed physical/frozen raw/layout signature gates.03compact_later1478offered,
509ultimatelycompleted/969queued;101.703039mslate boundary census508completed/
1dispatched/969queued. Baseline506versusnow509/later509 finalcounts are descriptive
only, no winning schedule/causal effect claim. One episode/arm/one sourcefamily
cannot support calibrated models.04now/source_day_0_files_32running since17:47:18.
Original source spacing/debt/in-flightcompletion retained; no thinning/SLA objective.
03resultSHA b6e2acc4d03368e1788e3df7140e5203ba219a30159a89fe1a2995517414626d;
eventsSHA df2eec2216993c1d2cb111b893b18edf6648f5aa2daafd4932ba42f390fdf9d2;
auditSHA 8734712789818bd57e73f553d4f6112f783c47bceee2b3cf30d5cea97c8eb846.
Result/audit receipts mirrored hash-identical; full raw/bytes/export/fitting wait
until inactive collection. Next validate32file real layout and remaining disjoint
sourcefamilies before chronological candidate fit. All prior failures preserved.

## 32. Recovery3 stops on missing fresh telemetry; candidate export registered

Recovery3exit18:02:37UTC:3passed/1failed/14unattempted.32file04failed beforequery
submission at sampler.window with Stale or future telemetry; no activeSpark18:15UTC.
No gate relaxed/failed labels reused. Sampler diagnostic
results/recovery3_sampler_diagnosis_20261015.json shows maximum sample-end to
recordstamp0.003870043s; this does not prove logging was causal. Need inspect actual
sample availability at failed preparation; future collector should wait for actual
fresh durable sample without newSQL/retiming/padding and retain wait/debt, while
sampling-gap2s/freshness2s gates remain unchanged. Do not blind retry same unit.

Registered SHA-bound candidate export of successful recovery3arms01/02/03 only,
with six historical/overnight attempt inventories. New package
results/physical_cost_candidates_recovery3_20261015, protocol same name inexperiment
protocols. This is real end-to-end candidate export progress, not independent
train/test evidence: one sourcefamily,16file original layout, no32file accepted.
Detached worker3 export/rawaudit next; independent roundtrip before any model use.
Original failures/tablebytes kept; fitting/calibration remains blocked by diversity.

Candidate export launched worker3nohupPID1261960 at18:19UTC; log
results/physical_cost_candidates_recovery3_20261015_launch.log. Estimated check
within5minutes/nextheartbeat.63f025bHEAD/5intendedSHA matched hosts. No physical
collector active; no accepted export result yet, independent roundtrip next.

## 33. Verified fuller-history candidates and real-sample availability contract

Worker3 independent roundtrip passed:1524query/2rewrite/3episode rows,772queries
with actual complete300s offered history. All failures/unattempted retained; one
connected sourcefamily still blocks independent fit/calibration. Export package
results/physical_cost_candidates_recovery3_20261015; independent_verification.json
and verifierlog results/physical_cost_candidates_recovery3_verification_20261015.log.
VerifiernohupPID1269964completed. Full package mirror still pending.

Opt-in wait_for_real_durable_sample_v1: wait outside log lock at existing sampler
cadence for actual fsync-published sample before window preparation/after realSQL
refresh; stop at original horizon, leave requestqueued, save start/end/sample/wait
outcome. No fakewarmup, featureimputation, timeline compression, relaxed2s gap/age
or retry of physical query. Windows still pass full strict verification; delayed
samples causing actualgap failure remain failure. Historical failure occurred
17:53:01 beforemidpoint archive17:57, so archive alone is not established cause.

Registered12fresh recovery4episodes: remaining two disjointsourcefamilies ×16/32
layouts ×three arms, original order from remaining matrix. Retain completedsource0
matchedgroup rather than repeat identical pilots. Enables planned chronological
three-family candidate comparison if collection passes; source0/32cell remains
missing. No model/power/calibration claim. Fresh immutablelaunch after worker3
syntax/rawregression/registrationSHA; all prior failures unchanged.

## 34. Remaining-source-family recovery4 detached launch

At18:40UTC/00:10IST no activecollector/export/physicalSparkjob. Historical actual
later-arm raw regression passed results/availability_wait_raw_regression_20261015.json;
0b0539352c736967ead44a3c47ecf8d40b06b1b3 HEAD/all20intendedunitSHA previously
matched hosts. Created immutable sparse runtime
/tmp/capstone_overnight_recovery4_runtime_20261015 at thatrevision, canonicaldata/
results symlinks. nohup coordinatorPID1285378 confirmed alive,12registeredepisodes
for source1/2layouts16/32. Log results/sf1_overnight_recovery4_cohort_20261015_launch.log,
progress/audits matchingcohortdirectory, raw sf1_overnight_recovery4_20261015_01..12.

Firstcheck00:30IST; fullestimate03:30–04:15IST if strict raw gates pass, existing
04:45episode/05:15operation/06:00workcutoffs unchanged. Wait contract livepath not
accepted from historicalregression; real samplinggap/freshness cannot be repaired
by inventedvalues or weakenedlimits. Alreadypassedsource0group retained; missing
source0/32cell explicit. Fit remains blocked pending actualremainingfamilies and
independent export/verification. No heavybackup/modelrun concurrent withqueries.

## 35. Actual sampling gap diagnosis; independent counter/persistence pipeline

SSH restored19:16UTC; recovery4stopped19:13:09UTC1passed/1failed/10unattempted.
Passed01source1compact_now1557offered/523completed/1034queued; two sourcefamilies
now have realpassedepisodes but independenttestfamily still missing. Failed02
actualtelemetry interval19:08:28.651567..31.180153UTC2.528587620s, archivecheckpoint
completed19:08:53UTC, actualwrite-rate~60MB/s. Savedrawdiagnosis
results/recovery4_gap_diagnosis_20261015.json. Causal attribution tofsync not proved,
but sampler currently serializesread+durablelogging so a logstall delaysnextread.

Opt-in independent_counter_sampling_durable_publish_v1 separates realcounterreader
fromFIFOwriter. No samplesdropped/generated; originalendpoints/elapsedvalues kept,
features see samples onlyafterdurableemit/fsync. Writerdrains onobservercompletion;
failures explicit; realgap/freshness/coverage gates unchanged. Thread/GIL/hostload
can stilldelayactualread andmustfail, not be repaired. No service/process canceled.
Registered11freshrecovery5episodes: source2sixarmsfirst toprioritizemissingfamily,
thenfiveunpassedsource1arms; retainpassedsource0three/source1one. Two layouts/three
arms/source-spacing/cutoffs/boundary/preparation/archivecontracts unchanged. All
historical failed counts preserved. Next server syntax/rawregression then immutable
launch; no fituntilrawverified independentfamily data. No calibration/policyclaim.

Recovery5nohup launch19:28UTC/00:58IST, PID1334649alive, frozen
/tmp/capstone_overnight_recovery5_runtime_20261015 at
95a5548d9f46471b852f0d796b6268055babb1f0. All19unitSHA/HEADmatchhosts;
actualsource1nowrawregressionpassed independent_sampling_raw_regression_20261015.json.
Live newreader/writer contract stillneedsphysicalaudit. Log
results/sf1_overnight_recovery5_cohort_20261015_launch.log; matchingprogress/rawarms
01..11. Firstcheck01:20IST;fullestimate04:00–04:30ISTsubjectstrictgates. Existing
cutoffs preserved; noheavyfit/backupwhilequeriesactive. Three-family exportfit
possibleonlyonactualsuccessfulsource2data, nofuturelabels/manufacturedsample.

## 36. Third disjoint source family and live independent sampling pass

19:55UTC PID1334649active; recovery5arm01source2compact_laterpassed physical+
frozen raw gates,1501offered/528ultimatelycompleted/973queued.134.852304mslate
boundarycensus527completed/1dispatched/973queued retained.02source2baselineactive
since19:44:48UTC. Independentreader/durablewriter now passed one actualepisode;
no samplegap/freshness thresholds relaxed. Successfulepisodes now coverthree
registered disjoint600s sourcewindows (source0three,source1now,source2later).
This enables a possible whole-family chronological exploratorysplit afterexport,
not sufficient calibration/power/causal/generalization evidence. Still no actualfit.
ResultSHA72440a6724b661694ffc73dd8272a432f6ccf2859bcbafc4332ac529ae1c5293;
eventsSHA89f8df6e2d40c2572b7c2b42629860902e60d172d30afc6b1111b774a5e3afc7;
auditSHA2f7368ecabf1ccb817b3e78e867da4af0022a870c3f0531301fea1c1a3fa01d2.
Smallimmutable result/audit receipts mirrored; fullraw/exportroundtrip/fit wait for
inactivecollector. Remaining32file/layout/sourcearms stillpending; all prior
failed/unattempted counts unchanged. Next physical gates before dependentmodeljob.

## 37. Recovery5 lock-acquisition freshness failure; three-family export milestone

20:25UTC noactiveSpark/collector. Recovery5stopped20:16:46UTC2passed/1failed/
8unattempted:03stale actualtelemetry inserializedprepare afterlockacquisition,
noSQL submitted forfailedpreparation. Countergap/freshnessgates unchanged. Two
passedsource2arms later/base each1501offered/528finalcompleted/973queued; baseline
90.044346mslatecensus527completed/1dispatched/973queued. Failure/statuses retained.

Prioritize complete export/verification/registered exploratoryfit of actualsuccessful
sixepisodes acrosssource0/1/2 ratherthanblind physicalretry. Registered
physical_cost_candidate_export_three_family_20261015.json SHA-binds sixresults and
eighthistoricalattemptinventories, output matchingresults directory. Onlyoriginal
16filelayout, incomplete source1/2matchedgroups, persistence/preparation version
confoundedwithfamily/time: exploratoryevaluation only, no generalization/calibration/
policyclaim. Source0/1train source2test andalpha1 preregistration unchanged. Primary
latencyfit excludesincomplete demand histories, rewritefeaturesmeasuredonly.
Next nohup export+independentroundtrip, actualhashfitregistration, failedfits saved.
Telemetrylockavailability repair remains a futurephysicaldependency, not relaxed.

ThreefamilyexportnohupPID1396241 launched20:28UTC; log
results/physical_cost_candidates_three_family_20261015_launch.log. Checkwithin5min/
nextwake; independentroundtrip before fit.8cfa5f7HEAD/5intendedSHA agreehosts.
Nophysicalcollector running, no acceptedfit/exportresultatlaunch.

## 38. Independent three-family roundtrip and registered first exploratory fit

Exportcompleted3103query/4rewrite/6episode rows. Worker3nohup verifierPID1410147
completed independentrawroundtrip; output
results/physical_cost_candidates_three_family_20261015/independent_verification.json.
ExportrecordSHA306c9844453174951abf262fd22b607ce3e6c341ad340f08c6e650cf2a0e0712;
verificationSHAe1af34743dc1167ab28f863f06853fdd3f6c5ac8d3a9090ab063d644ba126c36.
Fullcandidatepackage mirrored locally; intendedartifactSHA agreement next. Noactive
physicalcollector, so fitting won't compete withphysicalquerywindows.

Registered candidate_cost_fit_three_family_20261015.json: originalpreregistered
chronologicalfamily0/1train,2test; alpha1.0noheldouttuning, fullreal60/300sdemandonly,
training-onlyencoding/scaling/medians, shared/separatependinglatency and rewrite
clientduration. Wholeepisodes/sourcefamilies preserved; no calibration or scalar
counterfactual objective. Primaryfit bundles explicitlyuncalibrated/noscheduler;
missingregimes notfit, negativepredictions retained, failureattemptssaved. Onlyfour
rewriteexamples/oneoriginallayout/instrumentversionconfounding/incompletegroups:
this is pipeline/exploratoryevidence, not acceptedscientificcostmodel. Next worker3
nohup fit/log/PID, then auditactualoutputs/predictions/errors before claims.

FirstfitnohupPID1411927launched20:44UTC; log
results/candidate_cost_fit_three_family_20261015_launch.log. Checkwithin5minutes/
nextwake, then auditresults before accuracyclaims. Finalcandidatepackageincluding
independentverification20filesSHA agreedhosts, da9c915HEAD/5unitSHA agree. First
mirror occurredbeforeverificationfilecompleted; refreshedmirror nowverifiedfull
package. Fit/data/gates frozen for this shortjob; no physicalcollector active.

## 39. First fit negative results and independent saved-model audit implemented

Firstfitcompleted onworker3, uncalibrated/noauthorization. Preliminaryfitreport
paired521heldoutqueries: later262sharedMAE24.8856ms/separate66.7832ms versus
baselineepisode259shared601.2233ms/separate593.8812ms. SeparatependingTrue trains
11/test12with9negativepredictions; rewrite3train/1testMAE199.7219ms versus
median311.9211ms. This is not successfulcostgeneralization: baselineepisode severe
error, tinyconditional/rewriteblocks and negativepredictions. No tuning/refitting
onheldoutoutcomes, no calibration/promotion. Preliminaryvalues need independent
roundtrip before finalaccuracyreport. All failed physicalattempts remain excluded.

Added audit_candidate_cost_fit.py, read-only actualCSVtarget/identity/wholeepisode
membership/missinghistoryinventory/trainingmedian andpersistedprediction checks,
artifactSHA, rowcoverage, negativepredictions and descriptivetrain-range shifts.
Doesnotrefit or selectwinner; rangeoutliers not permission for heldouttuning.
Next worker3nohup auditandactualreceipt, mirrorfit/candidate/rawpackages, append
negativefindings and nextindependentcollectiongate. No activephysical/modeljob.

Independentfit auditnohupPID1427023launched21:00UTC; log
results/candidate_cost_fit_independent_audit_20261015.log; intendedreceipt
results/candidate_cost_fit_three_family_20261015/independent_audit.json. Check5min/
nextwake; failures preserved andnotre-fit.7f441ebHEAD/5unitSHAagreehosts.

## 40. Independent negative-model audit passed and bundle preserved

Actual persistedprediction/CSVtarget/identity/trainingmedian/hash/coverage checks
passed.1551earlyincompletehistoryqueries excluded;1031train/521test sharedrows.
SharedMAE311.395130063ms versus median22.928232362ms; separatependingFalse
312.200003429vs20.364429173ms (1020train/509test), pendingTrue1033.550793674vs
48.999455208ms (11train/12test),9negativepredictions. Rewrite199.721930139vs
311.921126999ms with3train/1test is not robustaccuracyapproval. Modelaudit successful
means evidence reconstruction, not statisticalperformance. Learnedmodels rejected
for scheduler use; no tuning/rerun to erase negative result.

Independent auditSHAfad4fe8fb85c1c3f22ab34a54f59b61b6fc9d75ba712a306c3cf969d84f4d7f8;
fitrecordSHA45b6b56c374046f74dc71bd9d7fbdb8f9903c91421ce26ac35e10bb45a26f1a6.
Sixfitbundlefiles mirrored withSHAagreement. Range diagnostics show multipleactual
I/O/demandheldoutvalues outside trainingrange; not a causal explanation or license
for heldouttuning. Entire6successfulrawpackages (~220MB) mirror initiated; verify
allrawfiles beforefallbackclaim. Actualphysicaltablebytes not yetmirrored fornewruns.
No activephysical/modelprocess at21:10UTC. Append nextgates inlearnedcostplan:
lock-acquisitionavailability race, matchedindependentvariedlayout/regimecollection,
future untouchedtestblocks/trainingonlypositivemodelprotocol, physicalfallback.

## 41. Six successful raw packages fully mirrored and hash verified

All144files across6accepted-for-physical-diagnostic packages mirrored locally,
including rawevents/frozenprotocol/code/SQLreferences/mapping/results. Worker3
nohupSHA256checkPID1456293finished,144OK/noFAILED; receipt
results/six_raw_mirror_integrity_20261015.log, manifest /tmp/six_raw_mirror_hashes.
No activeSpark/collector/modelprocess at21:25UTC. Together with20candidatepackage
and6fitbundlefiles, actual model-input/predictionevidence has fallbackcopies. This
is rawresearch-evidence fallback, not Icebergtable-byte/portablecatalog fallback;
newphysicaltablebytecopy stillmissing. Neverdelete/resetremotedata or archive.

Negativefit remains unchanged. Nextcodegate: releasepreparationlock ifactualdurable
sample expiredwhileacquiringit, recordunsubmitteddeferral, waitoutside thenfresh
prepare. PreserveFIFO/cutoffs/actual2s gap-age/history gates; noSQLretry or prior
failedstatusupgrade. Newpathrequires preregisteredfreshlivevalidation, not fake
samplesor historicalcompile-success. Physicalbytepreservation is independentjob
whileidle; no modelrefitting onheldoutoutcomes.

## 42. Lock-acquisition sample expiry repair, no physical SQL retry

Added opt-in release_and_wait_for_real_sample_v1: oncepreparationlock acquired,
readactualdurablyavailable sample-end/clock; expiredsample triggers typedexception
beforeanyobservation/dispatch/SQLintent. Lockreleased, savequery_preparation_deferred
actualidentity/clock/sampleendpoint, waitoutsideforrealdurablesample, retain sameFIFO
requestuntiloriginalhorizon. No counterfactualprediction/timestamprepair/SQLretry or
newmaxageconstant. Actualwindowgap/freshness/history/coverage remain strict. Raw
checkerbinds deferralcontract/sourceUUID/expiredage/chronologybeforeanySQLintent;
cohortrequiresidenticalcontractallarms. Historicalfrozenruntimesunchanged.
Serverrawregressionnext, newpathrequiresfreshregisteredlivevalidation. Negativefit
unchanged, no promotion. No activephysical/modeljob at21:40UTC.

## 43. Fresh32file matched group preregistered for repaired live path

21:55UTC noactiveSpark/collector. Historicalreal source2laterrawregression passed
submission_deferral_raw_regression_20261015.json; codef4e831d7unitSHA/HEADagree.
Registered sf1_layout32_validation_cohort_20261015.json and3freshbaseline/now/later
identities. Sameactual600ssource2window/fullarrivals, actual32filecontrolledlayout,
allstrictsampling/task/layout/result/gap/freshness/multiset/cutoffgates; newopt-in
unsubmitteddeferralcontract, matchedinstrumentationallarms. No reusefailedtables.
Purpose validate32layout and newsubmissionpath, not refittingtoimprove currenttest.
Sourceoverlapscurrenttestfamily2 so notnewindependenttest/calibration; crossversion
16vs32comparisonconfounded. Negativefit preserved. Episodecutoff04:45IST/SQL05:15
unchanged; reserveaftercompletionforrawaudit/mirror and morningreview. Next immutable
worker3launchafterregistration/headSHAchecks; actualbranchmustbeobservedtoclaimvalid.

32filegroupnohup launched21:57UTC/03:27IST, PID1486932confirmed alive. Frozen
/tmp/capstone_layout32_runtime_20261015 at
1fa3d3da9649e157dc2155ec5180f34103340133;8registrationfileSHA/HEADagreehosts.
Log results/sf1_layout32_validation_cohort_20261015_launch.log; matchingprogress/
audits andarms sf1_layout32_validation_20261015_01..03. Firstcheck03:50IST, group
estimated04:20–04:30ISTsubjectrawgates. Noacceptednewlayout/deferralbranchatlaunch.
No heavycopy/fitting concurrent; finishinflightnaturally/cutoffs unchanged.

## 44. Complete32file matched physical group passed; separate diagnostic export

Cohortcompleted22:46:44UTC3passed/0failed/0unattempted; no process canceled.
Each1501offered. Baseline535finalcompleted/966queued, now522/979, later530/971;
latecensus534/521/529completed plus1dispatchedeach, observer89.500690/100.443621/
77.118767mslate. Strictphysical/logical/raw/layout/task/freshnessgates passed;
singleepisodes/no causalpreferredpolicy or calibrationclaim. Allpriorfailedcounts
unchanged, existingnegativefit unchanged. New source2overlap isnotindependentfamily.
Branch diagnostic results/layout32_branch_evidence_20261015.json separatelyrecords
actualunsubmitteddeferrals/waits; passingepisodecannotproveunexercisedbranch.

Registered separate32filecandidateexport, SHA-bound3results and9cohortinventories,
output results/physical_cost_candidates_layout32_20261015. No refit/test-outcome
tuning. SourcecohortSHA d13bbc70743d8ecaedddfebaec83c9bf746e0abbf17808c70b46cfc00c8b6258.
Next nohup export/independentroundtrip, rawmirror/hashes, idlephysicalbytefallback;
cutoffs/newphysicalepisodeconstraints preserved. No acceptedcostmodel/scheduler.

Actualbranchdiagnostic: all3episodes0deferrals/0availabilitywaits, so newdeferral
branchnotexercised andnotclaimedlivevalidated.32filefullrunpath passed. Separate
exportnohupPID1550562 confirmed by actual launch receipt;
nextcheckwithin5min/nextwake, log physical_cost_candidates_layout32_20261015_launch.log.

## 45.32file verification launch and successful-table byte fallback registration

32fileexportcompleted1587query/2rewrite/3episode rows. Independentroundtripnohup
PID1565070 confirmed by actual launch receipt.
No physical/modelcollectoractive23:10UTC. No newphysicalexperimentplanned tonight.
Implementedbuild_physical_table_manifest.py/registered9actualsuccessfultables:
SHA-boundresults/rawevents, actualinitialinventorylocaldatafilepaths deterministically
bind table-root, allretaineddata/metadatafilesSHA/size, no symlinks/ambiguousroots,
idleSparkbefore/after. Failedtables remainremote untouched/excludedfromsuccessful
fallbackmanifest. NoSQL/tablemutation/deletion, noportablecatalogproof: absolutepaths
andcatalogstate areworker3-specific. Next detachedmanifestjob, transferonlyactual
manifestroots thenfullbefore/afterhashagreement beforefallbackclaim. No modelrefit.

ActualbyteinventorynohupPID1565619launched23:13UTC; log
results/physical_table_byte_manifest_20261015_launch.log, output
results/physical_table_byte_manifest_20261015.json. Check5min/nextwake, nophysical
operationinitiated. c283508HEAD/6unitSHAagreehosts. Tablebytesnotmirroredyet.

## 46. Physical byte transfer initiated; approval timeout preserved

Firstcombinedcopycommand didnotstart: automaticpermissionreview timedout (not a
safetyfinding). Allowedoneretry splitread-onlymanifest transfer succeeded. Actual
manifest9tables/516files/2,486,276,798bytes downloaded, saved
results/physical_table_byte_manifest_20261015.json. Source-registered table roots
only, copywithoutdelete/reset to results/physical_table_byte_fallback_20261015/
<experiment_id>/<table_root_name>/. Copycommands /tmp/copy_physical_table_fallback_20261015.sh
use10sSSHconnecttimeout; running localtransfer execsession81303. No validation/model/
physicalSQLrun started; no service/table/process shutdown. Transferoutcome/hashes
notyetaccepted; mayremainpartial atcutoff. Estimatedchecknext15minwake; no guarantee
of full2.5GB copybydeadline. Postcopyallfile/size/SHA agreement required, absolute
catalogpaths remainworker3-specific. Failedtablebytes stillremote untouched.

## 47. Byte copy finished; independent worker3 before/after verification launched

Transferexecsession81303finishedexit0. Actualcopiedfilehashinventory collected
results/local_table_byte_inventory_20261015.json, uploadedtoworker3. Independent
read-onlynohup verifierPID1595507 comparesallcopiedrelativepaths/size/SHA against
originalactualmanifest thenrehashesworker3sources/checksnoadded/missingfiles.
Script results/verify_mirrored_table_bytes_20261015.py, log
results/physical_table_byte_fallback_verification_20261015.log; receiptmatchingJSON.
No Spark/SQL/data mutation, noportablecatalogproof. Pendingverification cannotbe
backupapproval. Completed32candidate/cohort/raw3armmirrortransferexecsession95731
stillrunningatlaunch; no competingphysicalexperiment/modeljob. Nextcheckbothjobs,
allmirroredraw/candidateSHA agreement andfinalmorningstatus before06:00IST.

## 48. Full accepted evidence/byte fallback verification and morning handover

Worker3byteverifierpassed9tables/516files/2,486,276,798bytes: allcopiedpaths/size/
SHA matchoriginalmanifest; sourcesrehashunchanged. Receiptmirroredlocally
physical_table_byte_fallback_verification_20261015.json; sourceManifestSHA
89e5e51c04ed818cbcd6e502282dd2c5e51d7a5991f67fca867817722a7b1a96. Portablecatalog
notproved; failedtables remainremote. Final32candidate/cohort/raw3arms117files
mirrored, nohupSHAcheckPID1610036finished117OK/noFAILED. Previous144raw/20candidate/
6fitfilesagreement unchanged. No activeownphysical/modeljobs/Sparkjobs23:55UTC.

Saved docs/morning_review_2026-10-15.md distinguishes implemented/fitted/negative/
uncalibrated/acceptedrawstates, exactfailedcounts/resources/nextgates/fallbacklimits.
No newphysicaloperations aftercutoffs. Automationstillactiveuntil06:00IST; pauseat
cutoffwithoutcancelinganyservice. Allfuturemodelsneednewuntouchedtestblocks;
tonight's heldoutnegativefitnotrefitted. Targetedpush/sync/hashcheckscontinuefor
finaldocs; unrelateddirty/stashes/archivepreserved.

## 49. User-authorized detached cost failure and pipeline audit setup

User requests background worker3 audit before laptop closes in20minutes. SSHworks,
no activecollector/fitter/Sparkjobs atsetup. Added run_cost_failure_audit.py and
SHA-bound protocol cost_failure_background_audit_20261015.json using actual frozen
3103query/4rewrite/6episode export and negative exploratoryfit. No SQL, maintenance,
modelrefitting, test-outcome hyperparameter selection or fabricateddata. Independent
savedprediction/CSV/median roundtrip plus train-only scaler mean/variance reconstruction
(registered1e-10roundoff tolerance, not modelaccuracygate), designrank/constants,
trainingcoverage/correlations, existingheldouterror/contributiondiagnostics and actual
frozen measurementversion/registeredtelemetry inventory. Coefficients/range/error
patterns cannot establish causality. No physical branch can be validated read-only.
Freeze runtime code onworker3, nohup log/PID/resultJSON/Markdown; output/failures
preserved. Nextgate inspect actualaudit afterdisconnect, appendfindings, designfresh
consistent independentcollection/newuntouchedtestblocks. Oldautomationremainspaused.

## 50. Detached failure/pipeline audit completed and mirrored within setup window

Worker3nohupPID1700236finished naturally, statuscompleted_read_only_failure_and_
pipeline_audit_no_refit; log results/cost_failure_background_audit_20261015_launch.log.
Actualsavedpredictions/targets/mediansroundtrippassed, all4training-only scalermeans/
variances reconstructed.3distinctfrozeninstrumentationcodevectors observed in6fit
sourceepisodes. Shared1031train/521test,19columns/rank16; separateFalse1020/509,
18columns/rank15; pendingTrue11/12,18columns/rank10; rewrite3/1,11columns/rank2.
Largeheldoutcontributions fromreadIO/querycategories/shared andmemory/demand/sparse
pendingstate arediagnostic, notcausalexplanations. No scalingmismatch found bythese
checks, notproofallmodelassumptionscorrect. Negativefit/failedattempts unchanged.

FullreportJSON/MD, independentroundtrip, actualprotocol/frozenauditdependencies
mirrored results/cost_failure_background_audit_20261015;7fileSHA agreehosts.
Human-readable findings docs/cost_failure_audit_summary_2026-10-15.md. NoSQL/refit/
physicalbranchvalidation/modelpromotion performed. User's20minute setup requirement
met; alreadyfinishedbeforelaptopclosure. No backgroundjoblefttoawait/no automatic
newcollection. Next consistentinstrumentation/independentmatchedblocks, training-only
modeldevelopment/newuntouchedtestfamilies. Existingovernightautomationstaypaused.

## 51. New detached consistent measurement/coverage collection authorization

User authorizes next steps onworker3 with laptop unavailable after30minutes.
Connectivityworks; no activephysical/fitter/Sparkjobs. FirstSSHcheckautoapproval
review timedout beforeexecution; narrowedretry succeeded. Added immutable bounded
run_detached_collection_plan.py andregistered newactual source-day3/4/5 mappings,
18episode ×16/32layouts ×three arms withsame frozeninstrumentation/rotatedorder.
Oneepisode/cell is reliability/coveragepilot, notprecision/power/calibrationproof.
Newcutoffs15Oct10:30UTCepisode/11:00UTCSQL; oldovernightcutoffs supersededonlyfor
this newuserauthorizedunit. Allinflight finishnaturally, no services/data stopped.

Runnerprepares+independentlyaudits realSHA-boundmappings, checksdisjointoldwindows,
materializes all18fresh configs/source hashes beforeSQL, freezes code, launches
existing strict serialcohort, stops anyfailure/no retry, retains allunattempted.
Afterterminalcohort only rawpassedsuccesses mayexport whenrealrewritelabels exist;
independentroundtrip andfinalhandover/resultsaved evenifpartial/failure. No dummy
warmup/SQL/labels, no modelrefit/promotion, no relaxedgates. Existingnegativefitkept.
Prospective collection/modelcomparison preregistration saved
consistent_collection_model_protocol_2026-10-15.md; source3/4development,5futuretest,
trainingonlycandidate comparison pending datagate. Localclosuredoesnotaffectfrozen
nohupserverjob; futuremirror/actualresultsreview waitsforreconnection.

## 52. Actual detached consistent collection launch within30minute setup window

All8registration/code/docfileSHA agree local/worker3; frozen Gitworktree
/tmp/capstone_consistent_runtime_20261015 at
ea2b6e69eeeeb34d6a41c8212f544334dba046d0, canonicaldatasets/results symlinked.
CoordinatornohupPID1804667 launched03:03:16UTC/08:33IST, PPID1confirmed afterSSH
sessionexit; initialsource_preparationrunning (no dummytest/SQL). Log
results/consistent_collection_20261015_launch.log, progress/result/finalhandover
under matchingjobdirectory; childsource/rawlogs persistedserver-side. Estimated
5–6hours,13:30–14:30ISTsubjectgates; named16:00/16:30ISTlaunch/SQLcutoffs.
Usercancloselaptop: serverorchestratorneedsnoCodexheartbeat/networkconnection to
continue serialgatedsteps. Appautomationremainspaused. No automaticmodelrefit.

Saved detached_collection_handover_2026-10-15.md withcheckcommand/paths/guardrails.
Firstpreparation/execution healthcheck stillrequiredbeforesetupcompletionclaim;
no passednewdata/modelresultatlaunch. Alloldnegativefit/failures/dirt/archivekept.
Newresults onremote mustmirrorafterlaptopreconnect; cannotpromiseoffline localsync.

## 53. Detached setup health gates passed before laptop closure

All3fresh source mappings independentlyaudited; runner advanced physical_collection
onlyafterold/newsourceintervaldisjoint checks, actualmapping/auditSHA binding, all18
protocolgeneration andsavedexecutionmanifest. Existing strictcohortstarted with
frozenea2b6e6 revision, firstepisodelog exists/no reportedfailure athealthcheck.
ExecutionmanifestSHA0ed30bb68f8a8ccec8849828fa2e256fb7b0e33c3ed57043ce0dc18910064c10;
immutablemanifestmirroredlocally/hashmatches. No newphysicalepisodeclaimpassed yet.
CoordinatorPID1804667PPID1running independently ofSSH/laptop, allchildlogs/progress/
terminalstatus persist onserver; noCodexheartbeatrequired. Setupcompletedwellwithin
user30minuteavailability. Actualnewrawresults/data/possiblefailedgates mustbereviewed
andmirroredafterreconnection; no automaticfitting/promotion. No service/tabledeleted.

## 54. User-requested detached health review finds preserved boundary failure

User asksreviewstillgoingwell. At05:47UTC/11:17IST coordinator1804667alreadyexited
naturally; terminalstatusstopped_failed_physical_gate_preserved_no_retry. Cohort
ended03:37:29UTC/09:07IST:1passedbaseline/1failedcompact_now/16unattempted. Export
correctlyskipped:no successfulrewritecorpus. No activeSparkjobs; no service/process
killed/restarted. Laptop-independent orchestration/stop/handover worked, collection
nothealthy/complete. Currentmodel/earlierfailedcountsunchanged.

Actualrawfailure Call/outcome boundary differs. Worker3nohupdiagnosticPID1969785
saved boundary_failure_diagnostic.json: onecall dispatched15.683719msbeforehorizon,
actualexecute-start67.927321msafterhorizon; intentlogging41.867600ms. Fetch-end still
precededcompletedtransition50.777903ms. Thusrealdeadlinecrossing duringdurable
submissionpreparation, not a modelprediction failure or grounds to shift horizon.
Failedarm remains excluded; don'tretroactively relabel/retry forfavorableoutcome.
Terminalresult/handover/diagnosticmirrored forreview. Nextnecessaryrepair is actual
call-start cutoff plus explicitdurableunsubmitted-intent/queue accounting before
freshregisteredcollection; no physicalrestartperformedbythisreview.

## 55. User-authorized ntfy failure alerts for future tests/runs

User explicitlyauthorizes https://ntfy.sh/shashank_capstone_alerts andrequestsstatus
within4minutes. Worker3check:no activeprojectexperiment/fittingprocess orSparkjob.
Added configuredHTTPfailure notifier, standalone actual-command wrapper preserving
exitstatus/no retries, detachedrunner failedchild/orchestrationhooks, standing
AGENTS workflow for everyfuturetest/job.10s oneattemptnotificationdeadline is
operational bound, not policy/data constant. HTTP/localdelivery failures getreceipt
andcannotupgradeoriginalrun. No activefrozenruntime modified/restarted; oldfailed
job remains1passed/1failed/16unattempted. Verifydeliverywith actualfailedcohortalert,
not dummytest/data, undernohupworker3; saveexactresponse/PID receipt. NoSQL/refit.

## 56. Actual failure notification delivered and notification code checked

Worker3nohupPID1986995 parsed3changedPythonmodules andsentactualpreservedcollection
failure (not dummytest). ntfyreturnedHTTP200, eventIDoqZkPibiuhmG at06:05:10UTC;
receipt results/ntfy_actual_collection_failure_20261015.json, matchinglog. NoSQL/
physicalexperiment/modeljob started. Future standalone tests/jobs must use failure
wrapper; detachedrunnerchild/orchestrationfailuresalsoalert, failednotification
receipt cannotalter experimentstatus. 7bc00f6HEAD/all7unitSHA agreehosts. Userstatus:
no currentprojecttests/experiments/fitting/Sparkjobs; services preserved. Oldfrozen
runtimesnotretroactivelychanged. Externaldelivery requires worker3internet/topic
availability; failuregets localreceipt/no silentclaimof deliverednotification.


## Actual RPC deadline guard registration — 2026-10-16

Purpose: repair durable intent logging crossing the query admission horizon before actual SQL submission. Prior consistent collection remains 1 passed / 1 failed / 16 unattempted. Register guarded_rpc_start_requeue_v1: after durable intent and log-lock release, check monotonic client-call boundary; if horizon reached, emit statement_not_submitted, issue no SQL, release admission slot and retain source arrival as queued debt. No fabricated execution labels. Raw audit requires matching intent/observation, exact cutoff, chronological requeue, final FIFO admission and no observed Spark jobs for the marker. Existing executed-query deadline gate is unchanged.

Protocol docs/experiment_protocols/rpc_guard_regression_20261016.json binds four accepted real raw archives and the failed late-RPC archive by server SHA256. Worker3 detached audit must preserve accepted results and original failure rejection. Read-only regression cannot verify the new live branch. Code/protocol revision is the commit containing this entry. Fresh physical identities/cutoffs required before collection; old Oct15 cutoffs expired. No model acceptance or fitting claim. Unrelated local files preserved.


### Fresh guarded collection registration — 2026-10-16

Conditional on real archive regression passing, docs/experiment_protocols/detached_consistent_collection_20261016.json registers fresh 18 tables/outputs, same source-day3/4/5 arrival windows, layouts16/32 and rotated none/now/later actions. These overlap the prior attempted source families; do not count them as independent new families. Template explicitly opts into guarded_rpc_start_requeue_v1. Mapping audit receipts and full episode hashes are saved before first physical SQL. Previous failed 1/1/16 inventory SHA is retained. No new episode after16:30IST / newSQL17:00IST Oct16; rationale is bounded approximately6.5hour serial batch, natural in-flight completion. Fail-fast, no retries, no model fit/promotion. Log results/consistent_collection_20261016_launch.log; expected first-arm check roughly20minutes after physical launch, full batch5–6hours plus raw audits if healthy. Exact launch PID/revision and regression results will be appended.


### Guard regression observed outcome — 2026-10-16

Worker3 actual detached regression completed under revision fa5c394f18e068f5146244825714e0e530fc9259; childPID3211109, wrapperPID3211108. Four accepted raw audits passed (526/535/522/530 executed queries); historical failed arm correctly rejected with Call/outcome boundary differs. No failed evidence upgraded. Receipt results/rpc_guard_regression_20261016/result.json SHA256 90c74f1a447ae349aad6da5182311a64251e6e0e7f8d582ba5c48043032bf7a8 mirrored locally; log results/rpc_guard_regression_20261016_launch.log. All six intended Python source SHA256 and registration SHA256 match local/server. New live branch remains unverified until a natural boundary crossing. This permits fresh registered collection, not model acceptance.


### Guarded detached collection launched — 2026-10-16

Started04:13:49UTC (09:43:49IST), wrapperPID3213486 verified PPID1 after SSH disconnect; coordinatorPID3213487. Frozen runtime /tmp/capstone_consistent_runtime_20261016 at3fa7e52f30a885364adf1bca7cb75401068cac3b. Canonical repository was fast-forwarded and all six intended Python files, all six Oct16 protocol files and completed regression receipt SHA256 match local/server. Regression receiptSHA90c74f1a447ae349aad6da5182311a64251e6e0e7f8d582ba5c48043032bf7a8. Prelaunch Spark runningjobs empty; process inspection excluded inspection shells. Initial launch guard matched its own inspection shell and prevented launch; corrected read-only process check confirmed no competing Python jobs before single launch. No physical attempt occurred from that prevented launch.

Actual phase at first check: source_preparation, running; not yet physical success. Log results/consistent_collection_20261016_launch.log; durable queue/results results/consistent_collection_20261016/{progress.json,result.json,handover.md,execution_manifest.json}; terminal files appear only on completion. Wrapper failure receipt results/consistent_collection_20261016_failure_alert.json; child stage alerts saved beside their logs. First physical-arm estimate20–30minutes from launch, whole batch roughly5–6hours if all gates pass. Server coordinator serially advances without laptop and exports independently verified candidates when sufficient passed real arms exist; it does not fit models or promote a scheduler. Old overnight Codex heartbeat remains paused. Runtime source is frozen; later documentation commits do not alter it. Next gate: inspect source receipts/all episode registration then first raw physical audit; new branch occurrence remains pending.


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


### 2026-10-19 13:36 UTC: analysis source preflight and reproduction commands
Worker3 detached wrapper204530 actual-source no-SQL preflight passed at canonical065e7bf. Receipt analysis_source_preflight/result.json SHA21cee2dfff12f218f53152b1a37f73549855a48c3fefefe780efc8ca6afa342a; local/remote sourceSHA agreement comparator a2c72eb24cad5ce71c83a728c4ec461f8e56ba4ee1b42449a9110d57272a8978 and verify_runtime c94c9569c88cf704a9cef14eb97acd48eb2b917a6f443b47fd239d5a65054a7c. This only proves source/import and existing actual-source controller checks, not completed raw comparison. Added terminal-cohort registration utility (execution pending complete cohort) and runnable README with unique detached comparison command and limitations. First five preparation/registration checklist items marked evidenced; physical and final evidence requirements remain unchecked. Completed preparation/repair/original-failure evidence mirrored to original laptop drive; live recovery excluded from mirror until terminal.


### 2026-10-19: final analysis registration audit
Strengthened postcohort analysis binding: actual copied physical registration SHA must match both the terminal cohort and newly bound analysis protocol; manifest revision must match frozen cohort revision. This repairs a missing explicit provenance check, without changing measured outcomes or policy logic. Registered final source preflight includes added terminal-registration utility and analysis binding. Completed evidence transport checksum comparison returned no differing files (live recovery excluded); raw physical warehouse files are not included.


### 2026-10-19 13:39 UTC: actual controller/rewrite/query execution verified
Specific live wrapper203577/coordinator203578/episode203583 verified. First recovery arm passed initial physical multiset and305s telemetrywarmup, started actual source clock, selected immediate at0.089164217s, completed one real rewrite and14tracequeries at inspection. No complete-arm/benefit claim; substantial3067arrival first cohort still running. Final source preflight wrapper205380 passed canonical74897f1, receipt SHA d8aef2de4d161f5b2def2506152d168bb368a7355c405c1324357f5ba6e85ec7. Comparator/source hashes match server; registration utility parsing included in finalpreflight but actual terminal-registration/comparison must await all8arms. Original failure preserved; fixed frozen runtime remainsaf274db. This goal turn is progress: code repair, actual-table validation, fresh registered collection, independent analysis implementation, documentation/sync and real execution evidence. Full feasibility goal remains active and incomplete.


### 2026-10-19: simulator semantics audit registered before further model claims
Code review found a possible physical-contract mismatch: simulator.py treats conditional whole-call service medians as fractional work rates and can change layout mid-query, while actual SQL pins a snapshot. Registered simulator_semantics_audit_20261019.json verifies all old development labels against actual pinned SQL/whole-call timings, and inspects all registered candidate-start boundary crossings on actual prepared arrivals. No prospective physical outcomes used, no synthetic requests. If inconsistent, preserve failed model gate and introduce a separate snapshot-pinned model version; do not edit frozen live runtime or silently upgrade its scientific status. Physical cohort continues unmodified as candidate evidence.


### 2026-10-19 13:42 UTC: model semantics gate failed; separate repair registered
Detached audit wrapper207399 at55d231e verified all9923historical query labels against actual snapshot-pinned SQL and whole-call elapsed targets. All61actual-source simulated boundary crossings violate the whole-call conditional duration contract. Receipt simulator_semantics_audit/result.json SHA0f3d42c6f8a95e32b336b265f22a125622491d90380566b51a14583207ac3431; failure preserved and wrapper alerts. Source/core arithmetic preflight is explicitly superseded as evidence of physical model correctness: conservation alone did not prove action-transition semantics. Frozen physical cohort remains unchanged and cannot certify repaired model. Added snapshot_simulator.py with whole duration chosen at dispatch and pinned for the query; separate SnapshotMaintenancePolicy candidate selects it through overridable choose implementation. Default historical policy semantics remain unchanged for raw decision replay. Registered exhaustive real-source reconstruction before future physical use; no prospective outcomes/refitting. Approximate publication delay and observational interference labels remain limitations.


### 2026-10-19 13:44 UTC: separate snapshot model reconstruction passed; physical acceptance withheld
Detached wrapper208043 at15cc930 passed131838actual-source query/candidate recurrence checks, all61boundary crossings, no-action invariance and past-only controller integration. Receipt snapshot_model_reconstruction/result.json SHAb4e062876b3025d572e0faaccfce0ea9080884e55fa9098d8d4b89b1f984ced6; simulatorSHA226c80b20fb9e593d3b5827dacaf1bfc537adb7b7049266a11103dbb002cce46. Both repaired initial choices wait60s; predicted full-population advantage versus immediate is22.414837s/22.643336s, not physical measurements or robust significance. The change in choice establishes need for separate physical validation, not equivalence to old cohort. Final comparison now requires SHA-bound semantics receipt and reports original candidate model gate failure even if physical reconstruction passes. README commands updated; source and repair evidence synced. Original semantics failure ntfy deliveredHTTP200 idv5uY16hEqjlA. New prospective physical labels remain unused for fitting.


### 2026-10-19: operational resource-budget prefix audit registered
Live first-arm counters showed90completed queries at410.85s with queued980; source/core8.4h estimate may understate instrumentation/driver delays. Registered runtime_budget_prefix_20261019.json to preserve a complete raw-log prefix and account actual completed service, between-call gaps, REST response lifetimes and a clearly nonstationary linear completion diagnostic. No partial-prefix physical success, model refit or policy comparison allowed. New audit does not submit SQL or compete with physical workloads.


### 2026-10-19: explicit controller-version integration registered
Added controller_factory.py and future-runner selection of policy_model_version. Missing version retains legacyfluid_v1 for existing protocols; snapshot_whole_call_v2 requires SHA-bound passed reconstruction and exact simulator/base/subclass hashes. No automatic upgrade of old data or frozen runtime. Registered controller_wiring_20261019.json for16actual-source policy/window/version checks, saved model-choice preservation and physical-runner import wiring; no SQL or new fitted outcomes. Updated comparison modules import/parse included so model-failure reporting cannot silently break analysis source. Fresh physical v2 validation still required.


### 2026-10-19: actual operational prefix identifies freshness wait alias; condition-based repair registered
Budget wrapper209352 receipt runtime_budget_prefix/result.json SHAfe71a77c116e08d8f23ef92ad7b53fa1c79b055da73981ffcc7cc284c26894f9. Exact prefixSHA6d0c55bc635c1c95c50aef14e8c4939f5d4639e747ae767ebd723027f54e9d68:91complete queries/557.9s,83.75s client service,382.81s busy between-call gaps;189completedRESTresponses total1.118s. Largest164.23/123.22/56.26s gaps contain telemetry-availability waits, not RESTcalls. Code polls every1s while requiring latest durable sample age<=1s on a1s sampling cadence; phase alias can repeatedly miss freshness. Added separate PublicationTelemetrySampler condition notification only after actual eventfsync/samplepublication; retained1s submission age and original2s gap/age/95percent windows. Registered actual host-counter305s warmup+30s publication validation; no fake clock, no SQL. No frozen-run change. Current full8arm overnight completion estimate is unreliable and may miss deadline; report actual unfinished arms rather than compress demand or relax gates.


### 2026-10-19: independent durable-publication audit and future-runner gating implemented
Publication validation wrapper210832 runs real305s warmup plus30s actual observations, expected check around13:58UTC; source9604ad3. Added independent raw-counter/window verifier using unchanged verify_window rules and complete observation population. Future sampler_factory requires both actual validation and independent audit, exact observerSHA and unchanged numerical telemetry/submission gates before allowing durable_publication_v2. Old protocols retain interval_poll_v1; active frozen runtime is unchanged. Future runner explicitly selects both observer/model versions, but no corrected physical cohort has been launched. New factories/auditor await source/integration/actual receipt checks; missing receipt cannot be imputed.


### 2026-10-19 13:55 UTC: feasibility review and dynamic continuation queue superseded
Created FEASIBILITY_REVIEW.md with goal/data/model/observer/resource limitations, raw evidence pointers and explicit repaired-controller physical gate. New scheduler prompt/handover supersede earlier positive-source-preflight interpretation and8.4h estimate. Original candidate remains running unchanged; no corrected physical episode or completed feasibility claimed. Real observer validation210832 live with225actual intervals at13:55:39UTC; planned terminal~13:57:30UTC then independent raw-window audit and factory checks. Meaningful audit update ntfy deliveredHTTP200 idOxxc1RkWWY85. No service/process/data removal.


### 2026-10-19 13:58 UTC: actual durable-publication validation passed
Detached observer wrapper210832 ended13:57:29UTC;29actual publications, maximum sample-age onwakeup0.08134365s, original60/300s windows/95percent coverage/2s age/gap and1s submission freshness passed. Receipt publication_sampler_validation/result.json SHAd17964d7b8b233b82c66ed93057899d2ab8fe573f04f00203058c97b05820371; raw eventsSHA0995cc61ddd949925597e5fa24ca9ab272a1bd38fb011a857fcd77da151c302a. Actual-source controller wiring separately passed16checks atf101f80, receiptSHA462401ac6a301531bc23594086ef1204c22a34840e30f4652594a0297c7eacc7. Registered independent full raw-counter reconstruction protocol; no new SQL and no physical repaired-controller acceptance. Observer test remained source9604ad3 despite later canonical code additions; sampler/verifier hashes unchanged.


### 2026-10-19 14:00 UTC: independent observer audit passed; next chronological source audit registered
Detached raw audit wrapper213546 reconstructed all29publication observations/58original60/300s windows at unchanged exact-counter gates. Receipt publication_sampler_independent_audit/result.json SHA88f8d4dd1e6ecc41fb7262b5ded460e53ebea8be46bff502264633d8a140a882. Future observer factory now has actual evidence available; physical v2 still unvalidated. Added registered prospective_offset_seconds=2400 selection for next two chronological20minwindows after active source, and explicit exclusion of all current registered workload intervals via SHA-bound preparation receipt. No selection from performance, no compression, same-day dependence remains. This is source preparation only; no competing physical launch and no promise entire corrected cohort fits before cutoff.


### 2026-10-19: future-runner configuration integration check registered
Extended actual-source wiring check to validate observer factory selection with actual passed validation/raw-audit receipts, exact unchanged gates and canonical runner import. Constructor-only observer selection starts no thread and fabricates no counters; it is explicitly not observer/physical execution. Actual-host observer behavior is separately evidenced by29publications/58raw windows. Registered unique future_runner_wiring_20261019.json, retaining all16real-source model/policy checks and legacy defaults. Fresh chronological-source input audit is a separate queued detached job.


### 2026-10-19: fresh-source audits passed; corrected full pipeline preparation registered
Source audit214321 passed:3094arrivals20:40–21:00 and3188arrivals21:00–21:20 onsource27Feb2018 (all exact.286UTC offsets), receiptSHAb400f828678a1140f1cc61090bf8cfa74058674affe7841ac189200e4023baf3; explicit active-window exclusion passed. Future-runner configuration/model checks214322 passed, receiptSHAfcb728e94c2a10555127976d3681dfd265f3ada4b0f123f63f151a65ca5f967a. Added explicit model-version selection to preparation/preflight/study and raw decision reconstruction; legacy defaults preserved. Final comparison binds semantic proof to exact frozen simulator version, preventing snapshot proof laundering into legacy results. Registered fresh snapshot core preparation with immutable original empirical-model SHAa6fb2274b6adebe4f23aaaae608567aaacfd054376cb0158fa4f29b40e912d39 and exhaustive independent action-query recurrence on new actual arrivals. No new SQL or competing physical run.


### 2026-10-19 14:04 UTC: fresh corrected core passed; resource admission implemented
Detached215472 at e918bdc passed7core checks on3094+3188actual arrivals, including every action-query whole-call recurrence, FIFO/complete population and independently reconstructed past-only forecasts. Receipt snapshot_fresh_core_preparation/result.json SHA97167303a0f8b9d205d9f0cc1a78d37c4996e21c3596783651865b2d9da767bd; empirical-model bytes remaina6fb2274b6adebe4f23aaaae608567aaacfd054376cb0158fa4f29b40e912d39. Model-only8arm budget30306.45s, excluding initialization/audit overhead. Registered snapshot fresh runtime preflight; replaced stale hardcoded immediate-choice wording with per-version recorded choices. Added optional prospective resource_admission using SHA-bound actual model diagnostics and registered orders/warmup, actual exclusive-lock probes, all-arm start/end cutoffs. It refuses new SQL when locked or obviously unable to fit; estimate is explicitly not a guarantee and does not thin scope. Existing frozen cohort unaffected.


### 2026-10-19 14:07 UTC: corrected fresh runtime passed and full physical protocol registered, not launched
Detached216643 preflight passed all8fresh policy/window choices with snapshot_whole_call_v2 and unchanged empirical-model SHA; receipt snapshot_fresh_runtime_preflight/result.json SHA930b6676c9b784dc36fe06e82ab03a9e6ec2a81333edfee7e340975643546e08. Both initial corrected choices60s are model outputs, not improvement evidence. Registered physical_study_snapshot_publication_20261019.json: eight fresh tables queueaware_20261019_snapshot_01..08,25128offeredqueries if complete, all real arrivals/full drain, strict original gates, exact model/observer proofs and raw audited sources. No physical launch while old coordinatorlive; resource_admission requires actual locks and all-arm estimated starts/terminal within original cutoffs. Original failed and active candidate evidence preserved. Next run is admission diagnostic only; rejected admission means resource/time unavailable, not an experiment result or permission to reduce scope.


### 2026-10-19 14:13 UTC: full corrected deliverable frozen; actual admission denied
Prepared /tmp/capstone_queue_aware_20261019_snapshot_publication atd5e7c4002f49c409ae0b1e01863ceea40368d39a with protocolSHAae7da3e0724b65462b7e48583e64dd2bcf7ad620c0ae794c7a81b251466fb7ce. Actual prepared_snapshot_runtime.json states not launched; no table/job created. Real admission217516 denied because physical/study locks held, receiptSHAe51b2d0720b330a686950245bb46a4fda32c8d14583c7ac4625b7b87f57e35d6. Estimated latest launch14:53:53UTC excludes init/audit/drift, not a guarantee. Original203578/203583 live14:10UTC with3067offered/507completed,7futurearms unattempted. Updated README executable corrected/no-clobber commands and handover/feasibilityreview; all source/observer checks distinguished from missing corrected physical proof. Completed evidence mirrored; prepared-runtime receipt newly added and final checksum mirror follows. No goal completion claim.


### 2026-10-19: successful-path schedule constraint audit registered; cancellation permission pending
Original203578/203583 revalidated live14:17:41UTC,3067offered/601completed,7unattempted. Prior goal turn classified progress; this turn has a verified active dependency. Asked user asynchronously whether to preserve original study or explicitly override standing no-cancellation rule for only its experiment processes; corrected full design is concrete/prepared. No cancellation authorized or performed, and elapsed time cannot imply approval. Registered source/manifest-based lower-bound schedule audit: each unattempted serial arm requires its actual305s warmup+1200s arrival horizon, excluding current drain and overhead; compare resulting successful-path floor to corrected registered model-admission latest launch. This is operational constraint evidence, not an invented physical runtime or reduced success criterion.


### 2026-10-19 14:23 UTC: actual registered successful path misses corrected admission
Detached schedule audit222191 confirmed actual coordinator203578 runtime, seven unattempted manifest/protocols and unchanged corrected admission. Their warmup+arrival horizons alone10535s imply prior successful-terminal lowerbound17:18:37UTC from14:23:02, excluding current drain/init/audits. Corrected latest model-feasible launch remains14:53:53UTC. Receipt success_path_schedule_audit/result.json SHA0f316df79183edac264c5329119af11a043d081399d5bb458cf4797d72de6e8b. This proves incompatibility with the current registered admission plan, not an absolute physics runtime bound. User cancellation decision still pending; no processes stopped and no scope/gate changes. Required-action ntfy deliveredHTTP200 id41dWkkvq2So4. Added REQUIREMENTS_AUDIT.md preserving full objective and exact outstanding repaired physical/analysis/mirror gates; no completion claim.


## Authorized original interruption and corrected full study launch — 2026-10-19 14:33 UTC
Supersedes pending-authorization/not-launched status above. Human explicitly answered “Authorize stopping only the original study”. After exact /proc command identity validation and durable pre-stop registration, SIGTERM was sent only to original coordinator203578 and query-client203583; alert wrappers203577/203582 exited naturally. All four were absent afterward. No Spark/service process was signalled; no tables/data/logs were deleted. Reason: independently demonstrated historical whole-call/snapshot model defect and observer wait defect, not selection on prospective performance. Original repair inventory is **0 passed / 1 intentionally aborted / 7 unattempted**. Stable ledger:3067offered/queued,777dispatched/completed,one rewrite;2290offered queries did not complete, so this is incomplete evidence and cannot enter full-drain comparison. Earliest failed cohort remains0passed/1failed/7unattempted.

Evidence under results/queue_aware_maintenance_20261019/authorized_original_interruption/: registration, pre-stop progress, exact command identities/signals, executed control/verification scripts, stable partial-ledger inventory. Interruption result SHA790bcc80b115d40909a6278d5afcf99773ac92f5f08769944b5d093115807fc0; stable events SHA c14e3b070027f70a8dcad78490c98f62064ee0e3150cee64c7c044749ea89bb2. Original raw progress remains preserved rather than rewritten to a fabricated terminal result. Wrapper failure receipts/exit evidence remain intact; intentional abort is separately recorded.

Detached read-only integrity verification passed: Spark3.3.4 alive, no running jobs before check, both locks free, retained table local.experiment.queueaware_20261019_repair_01 current snapshot536319999756561391 has6001215rows/1file, symmetric EXCEPT ALL versus immutable source snapshot2963541948322332238 returned0. Receipt SHA50536d5a1869894c9143bdd968d5d58d37be6eda835e6c82f0cfb2adc6f38622. Verification wrapper225695 completed; no mutation.

Corrected full eight-arm physical study launched14:32:49UTC (20:02:49IST) from frozen /tmp/capstone_queue_aware_20261019_snapshot_publication atd5e7c4002f49c409ae0b1e01863ceea40368d39a; protocolSHAae7da3e0724b65462b7e48583e64dd2bcf7ad620c0ae794c7a81b251466fb7ce. Actual fresh resource/time admission passed, SHAb7f708db25eea5a102a56a53e269f7a3d7c44ea3422d8b8d96a9e092beb04d5d. Wrapper226239/coordinator226240/firstarmwrapper226244. Output cohort_snapshot_publication, outer log results/queue_snapshot_publication_20261019_launch.log; firstarm queueaware_20261019_snapshot_01 queue_aware running, seven unattempted. Both snapshot_whole_call_v2 and durable_publication_v2 registered; no active frozen source changes. Fresh3094/3188arrivals, fourpolicies/window,25128queries planned, complete-drain population, strict gates unchanged.

Admission's model-only terminal estimate22:57:55UTC (04:27:55IST) excludes initialization/audits/drift; completion is not promised. First-arm model estimate15:35UTC (~21:05IST); scheduler checks every10min sooner. No new episode after22:15UTC/no new SQL after23:45UTC; final deadline00:30UTC. Original stop authorization does not extend to corrected processes or services. Scheduler updated with actual handles and new state. Next gate: actual complete arm/raw audit, then eight-arm independent version-bound comparison; full goal remains incomplete. No calibrated model, causal benefit or publication novelty claim yet. Stable original evidence mirrored separately from active corrected cohort; final checksum/morning mirror still required.


## Corrected controller first real action — 2026-10-19 14:40UTC
Live handle226245 confirmed. First corrected arm moved beyond required warmup into actual trace-driven SQL. Raw events show initial wait at14:38:34UTC (elapsed0.06764s), then execute-now at14:39:34UTC (elapsed60.65049s), followed by one cohort_maintenance_completed event. Observation prefix:235offered/queued,66dispatched,65completed, no failed event observed. Source is cohort_snapshot_publication/episodes/queueaware_20261019_snapshot_01/events.jsonl on worker3; this is a mutable prefix, not a terminal audit or complete-drain proof. It establishes actual repaired controller start/wait/action execution, not measured superiority or model calibration. All eight-arm completion, raw reconstruction and comparator gates remain pending; no refit/source change/competing workload introduced. Next check: first complete arm and raw audit, model estimate~15:35UTC plus overhead.


## Terminal-analysis readiness source review — 2026-10-19 14:42UTC
Reviewed compare_study.py, register_comparison.py, audit_episode.py and ledger.py against the running runner without executing competing tests. Registration requires actual8/8terminal success; comparison binds protocol/terminal/source hashes and snapshot semantics, independently rebuilds queue transitions and exact response-area accounting, rechecks raw SQL/results/tasks/telemetry and replays past-only decisions. Ledger uses the shared event lock for decision observations/censuses, preserving chronology. This is source inspection, not a passed runtime audit; actual terminal comparison remains pending. README now appends exact corrected-cohort registration/comparison commands and explicitly supersedes historical original-run handles/commands. No running code/model/protocol changed. Next gate remains actual first-arm completion, then full8arm analysis; original failed/aborted counts are retained.


## Monitoring interruption and undeployed follow-up — 2026-10-19 15:20UTC
Last authoritative physical-client observation was14:47:53UTC: coordinator226240/client226245 live with fresh events, no failed event in bounded tail. The attempted14:49SSH process-identity read was NOT executed because automatic approval review hit a usage limit; this was review unavailability, not a safety rejection. At15:19–15:20UTC approval execution resumed, but two actual SSH attempts to10.10.3.232 timed out. Monitoring failure is not evidence of process termination; no remote restart/retry/cancellation performed. Human requested to restore campusVPN/network.
Local follow_terminal_study.py is a new UNVALIDATED/UNDEPLOYED draft that would wait for the identity-bound coordinator, require the complete8/0/0cohort and frozen comparison sources, then launch one detached whole-cohort comparison before deadline. /tmp/terminal_followup_registration.json is an incomplete draft with coordinator_start_ticks=null; it is not a registered executable protocol. No follower PID exists or launch is claimed. Preserve the draft; obtain actual process identity before registration, server-only validation/launch, and don't overwrite any comparison the existing heartbeat may already start. Current canonical remote/GitHub verified revision before interruption was33adc114e2fd4d40e273a525b9519376325d6770; frozen physical runtime remainsd5e7c40. Full goal and final comparison remain incomplete.


## Connectivity restored, first complete corrected arm and detached terminal follow-up — 2026-10-19 15:48UTC
Human reported connectivity restored; actualSSH succeeded15:46UTC. Coordinator226240 remained live throughout outage. Arm01queue_aware PASSED complete physical/raw audit15:45:29UTC:3094/3094queries,0failed/unfinished,one14.879901635srewrite,16→1files preserving6001215rows. Drain3829.441751062s; mean response1349.349730166443s; totalresponse4174888065134974ns exactly equals independently reconstructed outstanding-area and wait+service. RawresultSHA277ae8367117a442d42e20243f7ae0e85f2b04c84f7ab9010aa781060367d8e2, eventsSHAe0e0ce7ae515730ad2f55c5c4510f10e74e208ff7c5e8c925c4e6df7e0b04e75. No baseline comparison/benefit/calibration conclusion yet. Arm02no_maintenance started15:45:30UTC wrapper247356;6unattempted. Arm01walltime~73min exceeds planningestimate~62min: full8arm completion within unchangedcutoffs is uncertain. No scope/gate/cutoff relaxation.
Deployed source-bound follow_terminal_study.py (newcodeSHA3653d387a33097f94a38fa8bc2d931ffdad364a24c245f1f74ce8f0ece50917e) and protocolterminal_followup_20261019.jsonSHA277b87a6a6880f686aef5dc0db8a67eb3ba50a132d59d36357780393146b707a. ActualcoordinatorPID/startticks226240/135998028 verifiedbeforebinding. Canonicalcodecommitfd1f923 synchronizedlocal/GitHub/worker3; physicald5e7c40 frozencheckout unchanged. Real detached alert-wrapper248363/client248364 launched15:47:19UTC, progress waiting_for_identity_bound_collection. Output results/queue_aware_maintenance_20261019/terminal_followup/, logterminal_followup.log, launchreceiptterminal_followup_launch.json. No dummytest: actual invocation/import/config/processidentity reachedlivewait state; terminalbranch remains untesteduntilrealcohort completion.
Follower has noSQL/physicalwork and sleeps60s while identity-bound coordinator lives; uponterminal requirescomplete8/0/0and unchangedfrozen analysis sources, registersactualSHAand launches one failure-alerted whole-cohortcomparison before00:30UTC. Existing outputs refused; failures preserved; no kill/cancel atdeadline. Finalrequirements/mirror/report still separate gates. Heartbeat updatedtoinspectfollowerbeforeanyanalysis, preventingduplicatecomparison. Earlier draft/undeployed notes superseded.
Mirror initial rsync failedexit11 because localdestinationparentabsent (no experiment failure). Createddestinationand resumedstablearm01transfer; checksumverification pendingbelow/nextcheck. No activearm02evidence describedasimmutablemirror. Networkoutage handover remains retained; server fast-forward now restored. Next: completearm02/full8cohort, automaticrawcomparison ifeligible, finalreportandmirror.


## Completed corrected arm01 evidence mirror — 2026-10-19 15:54UTC
Stable arm01transfer completed with exit0. Itemized checksumdryrun `rsync -rcni` over the entire completed episode directory then exited0 with no itemized differences. Explicit localSHA256 result277ae8367117a442d42e20243f7ae0e85f2b04c84f7ab9010aa781060367d8e2 and events e0e0ce7ae515730ad2f55c5c4510f10e74e208ff7c5e8c925c4e6df7e0b04e75 match authoritative serverterminal receipt. Mirrorpath results/queue_aware_maintenance_20261019/cohort_snapshot_publication/episodes/queueaware_20261019_snapshot_01/. Includes raw events/config/frozen code/mapping/references/result; physical warehouse bytes remain remote. Follower launchreceipt also mirrored. Activearm02 and wholecohort remain incomplete and are not claimedmirrored.
Verificationmethod clarification: silent default `rsync -rcn` output alone is insufficient because changes may not be displayed without itemization; futuretransportchecks use `-rcni` plus explicit terminal/eventSHA. Earlier broad silent-dryrun claims require this stronger check before finalacceptance. This unit's completedarm has that strongercheck. No addedSQL/fitting/experiment was run fortransportverification.


## Post-hoc completed-arm forecast and queue diagnostic — 2026-10-19 16:10UTC
Purpose: explain the first completed arm's observed demand/response behavior without tuning the forecast or policy. Registered after observing arm01 (explicitlyposthoc), protocolarm01_posthoc_diagnostic_20261019.jsonSHA48ac73fdadef1a7a74fe1778a5cc27ad28fdc7334f2403d6e32834c0f2c01738, code190d306f95b0182b60901818765dba48dea846dd9e3379df2ebd0b2536ff1890, revisionacc0356. Source/protocolHEAD+hashes matchedlocal/serverbeforeexecution. Actualworker3nohupalertwrapper256090 ran16:10:01–16:10:02UTC, logarm01_posthoc_diagnostic.log, resultarm01_posthoc_diagnostic/result.jsonSHA1fa6a7fd41386519da643f1c88c34c10aecb33c6f937ec08a5411aa10b149ec2. NoSQL,fitting,policyedit or prospectivefeedback; runtime0.81s. Full eventSHA matches terminalaudit; onlyfirstdecision parsed afterstreamedhash, actualmapping/hash/sourcefreeze checked.
Observed firstforecast:2585predictedversus3094actualarrivals in exactrecordedintervals;binMAE25.45queries,WAPE0.1645119586296057. Signedtotalerror−509 (16.45%belowactual); this is descriptive one-windowforecasterror, not independent-daycalibration or a causal cause estimate. Actualcompletedarm meanresponse1349.349730166443s = meanwait1348.4719054982106s + meancall0.8778246682320621s; waitingfraction0.999349446145349. Waiting includes clientscheduling/telemetry/archive overhead and overload, not just Spark execution or direct compaction cost. Thus this test strongly stressesqueue debt; it does not establish general productionlatency behavior or policybenefit. Full8armcomparatorsstillrequired. Historicalcost/forecast/policybytes unchanged.
Completeddiagnosticresult mirroredlocally and itemizedchecksumdryrun exited0withnodifferences. Nofailedattempts in thisunit. Next: fullbaseline drain/rawgate, completecohort/automaticcomparison ifeligible; discuss forecastunderprediction/overload and overhead in finalfeasibility limitations, never refit on these outcomes.


## Primary-source dynamic-compaction novelty follow-up — 2026-10-19 16:20UTC
Reviewed primaryPVLDBArceKVsections3.2–4 and appended qualified overlap assessment to docs/novelty_comparison_2026-10-17.md, with sourceURL/page/section locators. No runtimevalidation/experiment/modelchange. Stronger limitation: our prototype does not establish novelty merely through transition-aware compaction simulation; exactexternalIcebergresponse-accounting scope still needs a distinct mechanism and independent evidence. PTO maintext retrieval remainsunresolved: publisherDOIredirect403, localPDFtextextractionempty/noOCR; missingaccess is not evidenceofmissingcapabilities. Preserve unknowncells. Livebaseline247357/coordinator226240/follower248364 confirmed before source review; physicalcollectionleftunchanged. Nextscientificgate still complete8armphysicalcomparison and finalrequirementsaudit.


## Stronger completed-base evidence transport verification — 2026-10-19 16:27UTC
Refreshed serverstudyresultroot with rsync-a (exit0), explicitly excluding cohort_snapshot_publication and terminal_followup* (active collection/follower). Then itemizedchecksumdryrun rsync-rcni over exactlysameinclusion exited0 withnoitemizeddifferences: every includedserverfile matchedlocalcopy. Localextras preserved; no deletionrequested. This rechecks the earlier broadmirror scope with the strongeritemizationmethod, superseding relianceonsilentplain-dryrunoutput. Separatecompletedarm01dir already has verifiedterminal/eventSHA and itemizedfull-dircheck. Receipt completed_base_transport_verification_1627.json (local; synced separately). Physicalwarehousebytes andactiveoutputsareoutsideverifiedbackups. NoSQL/fitting/experiment added; actualbaseline247357/coordinator226240/follower248364 confirmedlive beforetransportchecks. Fullgoalstillawaits8armcompletion/comparison/finalreport.


## PTO main-paper access gap resolved by visual review — 2026-10-19 16:32UTC
UsedPDFskillread-onlyworkflow: local image-only26pagePTOmainPDF renderedwithPoppler to /tmp/capstone_pto_review/page-01..26.png and visuallyinspected; sourceSHA73066a4750e01236ea194464f28b08452ec1c9542b79e98ec2c83152bd6029c3. Publisher403 remains an accessfailure but no longer prevents reviewing this savedmainversion. Appendedpreciselocator/evidencecomparison to novelty_comparison_2026-10-17.md, supersedingmaintextUNKNOWNnotes without erasinghistory. Keylocators:§2.2p4skippingobjective;§3.2.3p7footnote excludesfinalcompactiontimefromsortscoring;§4.2.2pp15–16reportsoptimizationcosts;§5p22latencybudget andp23periodicbatchedreruns/noautomaticdriftdetection/concurrentingestionredesign. Thus broadclaimsPTOignoresallcosts/dynamics areinvalid. Distinguish our evaluatedstart-timeobjective from layoutselection, but genericplanningpriorartstillpreventsnoveltyclaim. NoSQL/test/fitting/physical/model/protocolchange; actualbaseline247357/coordinator226240/follower248364confirmedlive. Nextgate unchangedcompletephysicalcohortandindependentcomparison.


## Deployed follow-up operating instructions — 2026-10-19 16:36UTC
README now describes the actual server-side identity-bound follower, its study-specificregistration, read-onlyprogress/logcommands, deadline behavior and no-duplicate-analysis rule. Explicitlyqualifies manualcomparisonexamples: neverlaunchalongsidefolloweroritsanalysischild, neverinferterminationfrommonitoringtimeout. This documents deployedbehavioralreadyobserved248364waiting; no newtest/runtime/policychange. Actualbaseline247357/coordinator226240/follower248364reconfirmedlive. Finalphysical/comparison/mirrorrequirementsremainpending.


## Corrected baseline complete; third registered arm active — 2026-10-19 16:59UTC
Arm02no_maintenance terminalaudit PASSED16:58:54UTC:3094/3094queries,0failed/unfinished,0rewrites,16files/6001215rows preserved. Meanresponse1373.9978016732814s; drain3872.79655405s; sumresponse4251149198377133ns equalsindependentoutstandingarea and wait4248409527514041ns + service2739670863092ns. ResultSHA2ee0a37f22f9104135802123ff31edac6605c66f2ccf2690090671035465a5ef; eventsSHA8c3ffc50a114fd94ec3231e78ae4babb06887634c964420a0c11bb127af7c0e6. Initial16files' sortedrowcount/bytes signatures matcharm01 exactly. Fullpairedpolicyanalysis remainsgatedonall8arms: do nottune, computesurvivorcomparisons orclaimbenefit fromthesetwosequentialruns.
Coordinator226240advancednaturallytoarm03forecast_quiet at16:58:55UTC, wrapper271592/client271593 verifiedlive;tablelocal.experiment.queueaware_20261019_snapshot_03;protocolSHA75d26b513cc1edc95c81ce4b630d4762a9620b9d8f2e583b0810ce99d18e6885. Inventory2passed/0failed/1running/5unattempted. Follower248364 continueswaiting forwholecohort; noanalysislaunched. Bothcompletedarms walltimes~73minexceedinitial~62minplanning; completing8beforeunchangedstart/SQL/deadlinecutoffsremainsuncertain. Neverchange frozenrunningcode, cutoff, population oracceptancegate toclaimcompletion.
Stablearm02rawdirectorymirror startedtransport session62765;copy/checksumverification stillpending. Arm01andcompletedbaseevidence haveprioritemizedchecksumproof. Next: thirdarmfulldrain/rawaudit, automaticcompletecohortcomparisonifeligible, finalrequirementsreportandverifiedevidencecopies. Originalfailed/abortedinventoriesunchanged.


## Completed baseline and fixed cohort registration mirrored — 2026-10-19 17:01UTC
Arm02rawcopy session62765 completedexit0; fullstableepisodedir itemizedchecksumdryrun exited0/nodifferences. ExplicitlocalresultSHA2ee0a37f22f9104135802123ff31edac6605c66f2ccf2690090671035465a5ef andeventsSHA8c3ffc50a114fd94ec3231e78ae4babb06887634c964420a0c11bb127af7c0e6 matchauthoritativeterminalrecord. Mirroredfixedcohortregistration/manifest/all8preregisteredprotocols separately, excludingepisodes/progress*/logs/notifications; itemizedchecksumcheck alsoexit0/nodifferences. Fixedmetadata usedlosslessrsynctransportcompression only, notdemandcompression/retiming. Receiptarm02_mirror_verification.json. Activearm03andphysicalwarehousebytes remainoutsidecompletedmirrorclaim. This supersedes armmirrorpendingnote. NoSQL/model/experimentchange. Full8armcomparison/finalreport remainpending.

Timestamp clarification for the preceding mirror entry:17:01UTC was a draft heading, not an independently recorded completion timestamp. The actual UTC clock check for recording this verification was2026-10-19T17:04:19UTC; copy/checks had completed before that observation. File hashes and exit statuses above are actual observed evidence.


## Authorized post-deadline preserved-cohort audit and evidence backup — 20 October 2026
Human explicitly authorized continuing with audit, backup and claim assessment. Overnight automation was paused; no physical episode, SQL, fit or survivor comparison launched. Actual remote terminal cohort SHA a1f6e5a8c7ff42fc32c7d109d3a2a1cafe6442cd87d92c37616c53ded19a7ed8 is 7 passed / 0 failed / 1 unattempted, 21,940 completed queries. Missing window1 queue-aware arm was barred by the unchanged 22:15UTC launch cutoff after arm07 finished23:11:08UTC. Follower preserved an incomplete-cohort failure and did not run comparison. Failure notifications actually delivered (collection sGaeeqPdaswt; follower B5liDVUXpqDe). This supersedes earlier live third-arm observations; original failed/aborted inventories remain unchanged.

Raw evidence root copied worker3→local without deletion; rsync-rcni exited0 with zero itemized differences, excluding active new preserved_audit_20261020_0822*. Receipt backup_verification_20261020.json records741files/2647759059bytes. Physical warehouse files remain remote and are not claimed backed up.

New read-only audit_preserved_cohort.py SHA d093311b5a0ab0c1395ceb04db4e1431eb5bc37bf5b297d431df29787fe89c71 matches deployed /tmp/capstone_audit_preserved_20261020.py. Purpose: reconstruct each completed raw episode and past-only decisions without weakening full eight-arm comparison gate. Frozen d5e7c4002f49c409ae0b1e01863ceea40368d39a runtime unchanged; all frozen source hashes checked before replay. Actual nohup failure-alert wrapper511312/auditor511313, parent511311, label preserved_cohort_raw_audit_20261020_0822. Log results/preserved_cohort_audit_20261020_0822.log; unique output results/queue_aware_maintenance_20261019/preserved_audit_20261020_0822/. Running at this entry; arm01 reconstructed; terminal result pending. No dummy test, SQL or model refit. Estimated several minutes per raw episode; inspect checkpoints, no duplicate launch.

Claim assessment draft queue_aware_maintenance/AUDIT_REPORT_2026-10-20.md distinguishes implemented snapshot/FIFO lookahead from unproven performance, causal cost calibration, independence and novelty. Saved mean responses are22–24minutes and >99.9%waiting-before-call; client/observer effects and serial overload limit external validity. Next gate: complete raw audit, mirror/hash its results, append actual outcome and synchronize report. Complete matched independent physical blocks remain a separate future registration; never silently append the missing arm and claim the original full protocol passed.


## Terminal raw audit and complete study-table backup — 20 October 2026 08:47 UTC

This supersedes pending-audit and evidence-only-backup notes above. The actual detached worker3 auditor ran **08:23:03–08:45:32 UTC**, exited successfully and produced `passed_preserved_incomplete_cohort_raw_audit`. Every one of seven completed episode results reconstructed exactly from raw SQL/results/snapshots/tasks/telemetry/FIFO/accounting; every recorded controller decision replayed from past-only state without refitting. Total21,940queries; inventory7passed/0failed/1unattempted; missing queue-aware window1 remains missing. Audit result SHA256 `401c6832e2e4bdf1a7735bf0018821709a0e22f3c91d149f3f9341bab061d084`; auditor source SHA256 `d093311b5a0ab0c1395ceb04db4e1431eb5bc37bf5b297d431df29787fe89c71`. Result and cohort file hash manifest are mirrored; rsync-rcni exited0 with no differences. Receipt `results/queue_aware_maintenance_20261019/preserved_audit_mirror_verification_20261020.json`. This is a successful integrity audit of an incomplete collection, not a passed full study or policy comparison.

Backup dependency inspection found the forecast source absent at its registered local path. Copied the actual180MB arrival export and provenance records (excluding disposable duckdb_scratch), verified itemizedchecksum zero differences and expected source SHA f058f9b99de4989b75941934f185db562cab5e482e700757821e163ddf514d20. Initial missing-file finding retained in backup_dependency_checks_20261020.json; successful superseding checks in backup_dependency_checks_20261020_after_source_copy.json. Core preparation/model/reference/turnaround dependency copies also match registered hashes (backup_core_dependencies_20261020.json).

Additionally backed up all **nine existing study Iceberg table directories**, including original failed/aborted attempts and seven corrected tables: **420 files / 2,483,873,977 bytes**, under `results/queue_aware_physical_backup_20261020/experiment/`. Copy exit0 and itemized checksum dryrunexit0 with zero differences. Physical-file SHA256 manifest `files_sha256.json` SHA `7bc8d6f6f37bb0b1c37c54ba40279dbf3fb22bd2eaf309a039eddfd432bec332`; receipt `verification.json`. This supersedes the earlier statement that only evidence was backed up. Unrelated warehouse tables/source-table global backup is outside scope. Restore/relocation is not tested; Iceberg metadata may contain original absolute paths. No table/data/service modification, SQL, new physical episode or fitting occurred.

**Claim assessment:** real corrected-controller execution and raw integrity are supported in this narrow setup. Full eight-arm benefit comparison, calibrated/causal interference costs, independent-day generalization and publication novelty remain unestablished. Queue-aware snapshot/FIFO lookahead is more than a three-predictor diagram, but extra complexity does not establish extra benefit or novelty. Strong current-queue and faithful planning baselines, ablations and untouched independent matched blocks remain necessary. Actual end-to-end collection budgeting must include initialization, observation and raw-audit overhead; the old model-only admission proved insufficient for full completion before launchcutoff. Next: separately register overhead/headroom and matched recovery/independent-block protocol before physical work, preserving7/0/1 and all failed history; do not just append a favorable eighth arm or relax gates. Overnight automation remains paused; this authorized audit unit is finished, full research goal incomplete.


## Autonomous evidence-first continuation registered — 20 October 2026
Human authorized executing next steps remotely, independently of laptop, with ntfy. New plan queue_aware_maintenance/CONTINUATION_PLAN_2026-10-20.md and protocol continuation_evidence_first_20261020.json SHA 7c45f1ea936b8e6fec9afdac55aa1ea242e56a1e34212740b97472f30c1e7826. New continue_research.py accounts recorded inter-call/telemetry/REST intervals, preserves unattributed time, exercises queue-only/forecast-planner comparators on actual prior queue observations, reconstructs development perfect-arrival timing headroom, checks fixed independent-day7/8 source counts, and writes/alerts terminal gates. All predictive costs remain SHA a6fb2274b6adebe4f23aaaae608567aaacfd054376cb0158fa4f29b40e912d39. No SQL/physical launch/refit or survivor comparison in this unit; original7/0/1 and cutoffs unchanged.
New ablation_policy.py and explicit factory gate information_removal_v1 with SHA binding preserve existing policy/model bytes and old frozen checkout. These are candidate information-removal baselines, not reproduced published systems or accepted physical models. Actual-source runtime validation occurs in the new detached job; source is prepared, not yet executed at registration.
Timing-headroom gate is an explicitly post-hoc development planning screen, not a preregistered old-test success criterion or formal uncertainty bound: both old development windows require positive perfect-arrival model improvement over immediate, per-query greater than median measured busy gap. Saved diagnostics already indicate zero oracle-model gain; never weaken gate to force a long physical campaign. If blocked, report exact next design gate and ntfy instead of consuming independent blocks. Independent candidate days7/8 are original arrival calibration context and need a supported frozen-history protocol before physical use; current rolling forecast cannot fill unseen predecessor days with zeros.
Remote launch will use frozen revision under nohup/failure wrapper, unique output evidence_first_0922, no retry, process receipt/log and start ticks; independent of app/laptop scheduler. Next gate is actual terminal stage results and mirror/sync.


## Terminal first continuation and registered actual submission-path probe — 20 October 2026
Read-only continuation actually ran09:31:30–09:32:02UTC onworker3, frozen891f3f37be1c75b45617098a8e9d8c87f213fc46, wrapper529369/child529370, new session/parent1 verified. ResultSHA4f8184e7d77ea8ecc240b21254245448d5e2bdcade94e6a8e74464f5c6232da5, statusblocked_no_resolvable_development_timing_headroom, no executionfailure. All7overhead ledgers accounted and4new ablation decisions exercised on actual recordedqueues. Both development windows' perfect-arrival model beststart0/immediate, gain0seconds, medianbusy-gap screen0.209236768s/query. This is model-based negative planning evidence, not proof of zero physical benefit or observer-free throughput. No policyrefit or survivorcontrast. New source days7/8 have3259/3282realarrivals, not physically consumed. ntfy startzesTSoQNG4QX andterminalHQDbmOIpx9Zr delivered. Completedoutputs mirrored; checksumverification pending launchunitcompletion.

Do not launch a long benefitcampaign merely because twelve arms are implementable. To resolve the next independent overhead question, registered probe_submission_overhead.py + protocols/submission_overhead_probe_20261020.json (SHA7b93940be6efcbad2540c718bd186ae9f06c10582fb0cacb01159c7488a69e07). It creates fresh local.experiment.queueaware_20261020_submission_probe_01, no existingtable reuse, same6,001,215row verifiedsource/16files, originalstrict telemetryproofs and305swarmup. Four realtemplate warmupcalls, then ABBA full/minimal/minimal/full phases, fourcomplete templatecycles perphase, total68realSQLqueries. Queryresults/pinned snapshot/multiset equality/actualSpark tasks checked forbothmodes; fullmode additionally independently verifies all original60/300s coverage/freshness/windowbindings. Minimalmode keeps durableSQLrecorder andshared backgroundsampler but omitsper-call telemetrypreparation; it is explicitlynotobserver-off and NEVER eligibleforcosttraining/policycomparison. This diagnosticdoesnot weaken priorstudyacceptance ormanufacturearrivaldata. Phasepositions/querywarmupbalancegrossdrift, notindependentconfidence. Newprobe administrative nonewSQLafter20Oct11:30UTC; operationsfinishnaturally. No fit,rewrite,or maintenancebenefitclaim. Frozenremote nohup+failurealert launchpending nextentry; nextgate actualprobe terminalaudit and causal/overhead interpretation.


## Remote independent probe launched and verified — 20 October 2026 09:38UTC
Actual probe launch09:37:02UTC: frozen /tmp/capstone_submission_probe_20261020_07eb97f at07eb97f833bfc8decfabbb062304873b89a36f90, sourceSHA b325f67df0bd5511f3f8d82b950ab132df5847a9c9d670220288a9187b249d4c, protocolSHA7b93940be6efcbad2540c718bd186ae9f06c10582fb0cacb01159c7488a69e07. nohup failure-alert wrapper530928, startticks142863427, child530929; SID530928, wrapperPPID1 confirmed after SSH launcher exited. Hostboot132d4e3a-b5b5-43b8-b45d-414e48a7334c. Log results/queue_aware_continuation_20261020/submission_probe_0935.log; launchidentity submission_probe_0935_launch.json; output submission_probe_0935/. No laptop/app-scheduler dependency. Failurewrapper unique labelqueue_submission_probe_20261020_0935, receipt submission_probe_0935_failure.json.
Actual initialization passed: fresh table created, original snapshot source verified, initial16files/6001215rows and symmetric EXCEPT ALL zero checked. At09:38:09UTC33actualtelemetryintervals had persisted; seven metadata/init statements completed;305s originalwarmup stillactive. Startntfy JYubnoP6SgUN delivered09:37:36UTC. This is running physicaldiagnostic evidence, not68completedqueries or terminalacceptance. Estimated usefulcheck09:45UTC (15:15IST), mayextendnaturally; nonewSQLafter11:30UTC, no cancellation/restart or tabledeletion. It will send its own terminalsuccess/failure notice and save actualstrictwindow/task/source/results audit. No dependent longpolicycampaign launched given0modelheadroom.
Completed first-stage diagnostics mirrored worker3→laptop; itemizedchecksumverificationexit0/zerodifferences excludingactiveprobe. Receipt stage_a_mirror_verification.json, originalresultSHA4f8184e7d77ea8ecc240b21254245448d5e2bdcade94e6a8e74464f5c6232da5. Activeprobe rawcopy notclaimedcomplete. All originalfailures/7/0/1 counts/warehousebackups preserved. Next requestedcheck: actualprobeprocess+terminalreceipt first, then rawmirror/interpretation; do not relaunch or tune from results, and don't claim observer-off measurements or repaired queuebenefit.


## Submission probe failed at first warmup; status check and repair registration — 21 October 2026
Actual worker3 terminal record supersedes20Oct running notes. Probe failed20Oct09:42:43UTC (15:12:43IST), error KeyError client_elapsed_ns. StatementRecorder records that derived field in statement_completed events but returns only clocks/rows/identity; new diagnostic incorrectly indexed it from the returned dict. This is an implementation interface defect, not a failed SQL result or evidence against queue-aware maintenance. First warmup query completed and exact result check passed before accounting crashed;0/64measuredcalls completed,3/4warmupcalls andallmeasuredcalls unattempted. No successful full/minimal comparison, overhead estimate or task/window terminalaudit exists. Frozen07eb97f runtime/table/rawfailure preserved. Wrapper530928/child530929 absent on21Octactualps; no automatic retry occurred. Failure ntfy Xte5ofDtZqcF deliveredHTTP200 at09:42:43UTC.

Entire continuationresultroot mirrored; rsync-rcni exited0/zerodifferences. Repair replaces invalid dictionary access with exact fetch_end.monotonic_ns minus client_execute_start.monotonic_ns, requiringvalidintegerclockordering; nofallback, imputation or changed timingdefinition. New read-only audit_failed_submission_probe.py will statically inspect actual helperreturnkeys, reconstructthosefields from the actual completed raw warmup record, comparecorrectedtimingexactly againstraw client_elapsed_ns, verifySQL/snapshot/result/referencehashes and retainfailedinventory. Allvalidation worker3detached+failurealert; noSQL/restart/newphysicalattempt authorized by this check. Actualauditterminalpending. Futurephysicalrecovery requiresfreshregisteredtable/output/cutoffs, neverreuseoldoccupiedtable or originalprotocol.


## Actual failed-record interface audit completed — 21 October 2026 13:27UTC
Worker3 nohup failure-alerted read-only audit started13:27:07.774UTC/ended13:27:08.009UTC, statuspassed_real_failed_record_timing_interface_audit_only. Launcher shellPID926291 observed; wrapper/childPIDs were not captured before this subsecondaudit finished and remainunrecorded. Log results/failed_submission_interface_audit_20261021_1324.log; output results/queue_aware_continuation_20261020/failed_interface_audit_20261021_1324/. AuditSHA35ff462a43b619702d0a81e52a1614b496a59de9f8a859a4328bee7575f598c0; repairedprobeSHAac8cba2b5e00bf2c2893694bb582811c703cad9c14d4fce75f5ce5e4f4922aca. TerminalresultSHAbe9c4cda05f275623953fa069c38525f5b43ccbcef456d6d6460bf4783a03470.
Staticinspection confirmed one successful StatementRecorder returncontract withoutclient_elapsed_ns; actualrawwarmupquery0 returnedcorrectSQL/snapshot/results. Correctedactualduration447985102ns exactlymatchesrawloggedduration; allinputfields actualrecordedclock/returnfields, no dummydata or imputation. Inventory1completedwarmup/0measured,3warmup+64measuredunattempted. This validates the repairedtimingextractiononly; full/minimal telemetry/tasks/phasecomparison remainunexecuted. Originalfrozen07eb97f source/protocol/table/failureuntouched. Newcanonicalrepair f5b5fcb sourcehashesmatchedlocal/server, intendedfilesonly; noSQL,restartornewphysicalrun. Wholecontinuationresultroot includingnewaudit mirrored/checksumverifiedrsync-rcni exit0/zerodifferences. No currentprobeprocess; ntfyoriginalfailureXte5ofDtZqcF delivered. Nextphysicalrecovery requiresfreshregistration/table/output/cutoffs, notsilentrerun ofoldprotocol. Originalqueuebenefitclaim stillblocked; nooverheadresultaccepted.


## Authorized fresh overhead-probe recovery registered — 21 October 2026 13:30UTC
Human explicitly requested restart to obtainresults. New protocol submission_overhead_probe_recovery_20261021.json SHA0bb1cc143c7af72304cca11add4aad9e9d6ea1a20a598c45f389e2709ccdc436, fresh local.experiment.queueaware_20261021_submission_probe_02 and results/queue_aware_continuation_20261021/submission_probe_recovery_1329. Oldfailedtable/output/frozen07eb97f source remainuntouched. Exact timingfixsourceac8cba2b5e00bf2c2893694bb582811c703cad9c14d4fce75f5ce5e4f4922aca and realrecordaudit bound inregistration; launcher must verifyrepairreceipt/source/failurehashes beforestarting. Same68realqueries,ABBAphaseorder,source16files/6001215rows,305swarmup, strictfulltelemetry/correctness/snapshot/task gates, ineligiblefortraining/policybenefit. New cutoffnonewSQL21Oct15:30UTC (21:00IST), abouttwohours administrativebudget; activeoperationsfinishnaturally. Inspectactualprocesses/locksfirst; no competingownphysicalrun observed13:29UTC. Commit/push/serverfast-forward and source/protocolSHAcheck precedelaunch. Nextgateactualwarmup/queryphases thenfinalrawresults; noautomaticretry orfavorable-resultselection.


## Fresh submission-probe recovery PASSED — 21 October 2026 13:38UTC
Actual detached recovery ran13:30:55–13:38:17UTC (19:00:55–19:08:17IST), wrapper927541/startticks152906703, child927542, parent1/newSID927541 verified. Frozen /tmp/capstone_submission_recovery_20261021_3cfd42a at3cfd42a8e19006923c5594d6cce523c376a9111d; protocol0bb1cc143c7af72304cca11add4aad9e9d6ea1a20a598c45f389e2709ccdc436. Launcher checked actualrepairreceipt/source/failureSHA andfreelocks beforelaunch. Log results/queue_aware_continuation_20261021/submission_probe_recovery_1329.log, PID/command/bootidentity inlaunchreceipt. All68realqueriescompleted (4warmup+64measured);32strictfullobservations passedoriginalwindow/coverage/freshnessproofs; exactSQLresults, fixedsnapshot6594224475879981160/logicalsourceequality andactualSpark tasks certified. Statuspassed_actual_matched_submission_path_probe; resultSHA19de6bfb02e693fbffd8eacd85850efba51fb6e82087719db18f4a637038caee, eventsSHA1a543274f7db403ec774be6819fa7d2c00bd6a0cb77dccd5bbc50a6cb250a4b4. Processesfinishednaturally; nofailedrecovery stage/retry/fit/rewrite. Originalfailedwarmupattempt preserved.
Full versusminimal medianpreparation-to-result difference bytemplate0..3: +34.03,+1.31,+48.09,+42.96ms. These aredescriptiveendtoend differences, notpure causaloverhead: actualSparkcall medians also varied, sharedsampler/durablerecorder remaininbothmodes; noobserver-free capacity or independentblock confidence. Dataeligibleforcosttraining=false andpolicybenefitcomparison=false. Fullgate/novelty/headroomclaims remainunproven; do not turnprobevaluesinto inventedoldcohortcounterfactuals. See SUBMISSION_PROBE_RESULTS_2026-10-21.md.
NtfystartmjhuEY1XyUPT andcompletionqKRo1t0Lci8H deliveredHTTP200. Completedrawroot mirrored anditemizedchecksumdryrunexit0/zerodifferences; receipt results/queue_aware_continuation_20261021/mirror_verification.json. Bothfailed/recoveryphysicaltabledirs additionallybackedup: 80files/331706316bytes, underresults/queue_aware_probe_physical_backup_20261021/experiment; copy+itemizedchecksumexit0/zerodifferences, SHAmanifest/verification.json saved. Restoreuntested; metadataabsolute-path limitationretained. Oldbackups/failedcounts/archive/unrelateddirtyfiles preserved. Nextscientificgate remainsseparatelyregistered physicalaction-time/headroom andobserver-scope study ondevelopmentdata beforeindependentbenefitcampaign; noautomaticlargecampaign launched.


## Repeated physical timing study and implementation guide registered — 21 October 2026
Human authorized small real timing experiment and requested ongoing updates to the copied methodology plus plain-language explanation of created/edited files/functions. New TIMING_STUDY_PLAN_2026-10-21.md and protocols/timing_headroom_development_20261021.json SHA202066caff3bcc83fe4faf47bc9bea55b58fb94dcf6a27c99e57902a32ac1263. Scope: one known realdevelopmentwindow3094arrivals/1200s, no timingcompression/thinning, fresh8tables queueaware_20261021_timing_01..08. Compare fixed0,60,600s atfirstcontrolleropportunity andnull; repeatforward/reverse order8arms, full drain/exactoriginalgates. Choicesrationale0immediate/60oneexistingbin/600halfhorizon; two repeatsbalanceearlylateorder, notpower/independentdayproof. Sourceoriginalmatched16file/6001215rowSF1, noingestion; fixedhistoricalmodelnotrefitted orusedtochooseactions. Original7/0/1 and allfailures staypreserved.
Newfiles: fixed_start_policy.py (registeredtimerintervention), preflight_timing_study.py (realrecordfrontier/source/import/authchecks), run_timing_study.py (sequentialcoordinator, measuredtimeadmission, checkpoints, ntfy, BOTHmethodologyappend/targetedGitpush afterunits), compare_timing_study.py (all8rawreconstruction/replay/matchedcomparisons), plan/protocol, IMPLEMENTATION_WALKTHROUGH_2026-10-21.md (plainlanguagefunctions/filemap/dataflow). Editedcontroller_factory.py toselectexplicitSHA-bound fixedintervention; editedaudit_episode.py torequireactualrewrite/nonearlysubmission/registereddecisionbehavior, retainingoldgates. Nochanges tooriginalfluid/snapshotmath, forecasts, labels orfrozenoldruntime.
Observedfull-armplanning, notmodel-onlydrain: maxprioractualarmwall plusmax305swarmup/priorindependentauditperarm; budgetall8+finalreconstruction ~11h, notguarantee. Newnonewepisodeafter22Oct15:30UTC,nonewSQLafter22Oct18:30UTC; preserveactiveoperationsnaturally, neverdelete/cancel/restart. Preflight mustpassonworker3detached, includingactualGitHubpushauthorization(dryrun) beforephysicalwork. Coordinatorwritesactualprogress/PIDs/logs, sendsntfystart/perarm/final/failure, failsdependentqueueonintegrity/doc-syncerrors, noretries/benefit-selectedstopping.
Both docs/methodology_working_doc.md and copied docs/updated_methodology_working_doc.md receive durableappend-onlyunitrecords andtargetedcommits onworker3, pushedGitHub. LocalclientHEAD/rawmirror necessarilydeferred whileoffline; nocurrentclientagreementclaim. Finalreportlinksimplementationguide andincludesallobservedpositive/negativecontrasts; descriptiveheadroomflagif samedelayedintervention lowersresponseinbothrepeats, noCI/causalgeneralization/noveltyclaim. Independentfutureblocksremainuntouched. Actualworker3preflight/launchpending; no physicaltimingrun launched atthisregistration.


## Explicitly authorized deferred documentation publication — 21 October 2026
Preflight_v1 failed only at requiredGitHubwrite readiness after realtimingfrontierchecks; HTTPScredentialunavailable. NoSQL/physicalrunstarted. Sourceprotocol202066... andfailedreceipt/log preserved; ntfy EXZqVrAqTvUU delivered. An alternateexisting-push readiness check alsofailed effectiveHTTPScredential lookup, ntfymGTqTLuzish6; it didnot establisha successfulSSH credential orchangeauthentication. Human explicitly answered “Proceed; defer documentation pushes”. This supersedes originalimmediatepush requirementfor thisrunonly. Bothmethodologydocuments willstillappend/fsync andtargetedcommit locallyonworker3 aftereachunit; GitHubpush/clientmirror deferreduntilnextcheck. No scientific/source/timing/acceptancegate weakened.
New effectiveprotocoltiming_headroom_development_deferred_push_20261021.json SHAdbfab850c4eb100caff416515f58756451ebca0d574023ae96289e03c463d102; same8registeredphysicalinterventions/source/orders/cutoffs, new codehashes for deliverymode. Newpreflight_v2 willverifyactualsourcefrontiers, imports, sourcehashes, explicitdeferauthorization andeffectiveGitcommitidentity. run_timing_study.append_docs skipsGitHubpull/push inthisauthorizedmode toavoid divergentremotehistorywhilelaptopoffline; preservesconcurrentdirtydocs. At nextcheck, FETCHworker3 main viaSSH, fast-forwardlocal before editing/pushing; do not overwrite its unpushedmethodologycommits. Frozen physicalsource remainsseparate. IMPLEMENTATION_WALKTHROUGH updated toreflecteffectivemode. Launchpendingv2actualpreflight.


## Timing study preflight passed; frozen launch handover — 21 October 2026
The effective protocol is `queue_aware_maintenance/protocols/timing_headroom_development_deferred_push_20261021.json`, SHA256 `dbfab850c4eb100caff416515f58756451ebca0d574023ae96289e03c463d102`. Worker3's real-source preflight ran15:33:09–15:33:15UTC and passed: all four intervention rules checked on65actual recorded queue/time frontiers each. It checked source hashes, imports and the Git author/committer identities under the user's explicit deferred-push authorization. No SQL was submitted. ResultSHA256 `e50edff2ecaf1f889850291db25a6c19ac8661a6f6da777380a47faa37988307`, saved in `results/queue_aware_timing_20261021/preflight_v2/result.json`; failed readiness v1 remains preserved.
The physical runtime will be frozen in `/tmp/capstone_timing_20261021_v2`, with a detached Git HEAD. Its `results` symlink shares the canonical result/lock directory; the checkout's original tracked results directory is preserved by rename. The launcher records exact revision, PID/start ticks, boot ID, command and log. Canonical result root: `results/queue_aware_timing_20261021/repeated_window0`; inspect `progress.json` for actual current child handles, not these planned paths alone. Parent log: `results/queue_aware_timing_20261021/study.log`. No physical launch is claimed by this pre-launch entry.
After launch, the coordinator automatically appends and commits actual unit evidence to both methodology documents on worker3. Those commits intentionally remain unpushed until the next laptop check. Before any local documentation edits or pushes, fetch worker3's main branch overSSH, fast-forward the client to its committed history, mirror completed raw artifacts and verify checksums. Do not reset or overwrite server-only commits. The initial source/protocol publication is already onGitHub; later documentation delivery is deferred by explicit user authorization.
The final report automatically links `queue_aware_maintenance/IMPLEMENTATION_WALKTHROUGH_2026-10-21.md`. That guide explains each new/edited file and the functions in plain language, including how replay, decision timing, raw validation, reporting, documentation and ntfy fit together. It does not claim the eight-run experiment is complete before actual results exist.


## Physical timing study started — 2026-10-21T15:36:49.195116+00:00
Registered8arms, two reversed-order repeats on one development source window. Fixed0/60/600s experimental opportunities plus noaction, all original3094arrivals/full drain, fresh16file tables. CoordinatorPID959092, preflightSHAe50edff2ecaf1f889850291db25a6c19ac8661a6f6da777380a47faa37988307, ProtocolSHAdbfab850c4eb100caff416515f58756451ebca0d574023ae96289e03c463d102, runtime790f4f89d1d8cbe821903af79392134bfb1c6bbb, estimatedwholewall10.80h including observed setup/audit. No fitting/independent-day/novelty claim. Output/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0; source manifest fixed before physical work. Local client mirror deferred while offline; server documentation committed after units; GitHub delivery follows registered mode.


## Timing study completed queueaware_20261021_timing_01 — 2026-10-21T16:49:26.103510+00:00
Actionstart_0, repeat0, raw/full-drain PASSED 3094queries. ResultSHA398f82b3d45a6aa2d3482f4dd9880f49146df0f20a59c9e88d371c43a4690b09, eventsSHAa5d9443194c07d278ed3e779d07bf6942f6f796a93ea2bab6c83559768dca887; sumresponse4166556114442666ns = rawoutstandingarea; mean1346.656792s, drain3821.283392s. Actualtiming{"actual_rewrite_start_after_arrival_clock_seconds": 0.519190713, "actual_rewrite_call_seconds": 14.79220523}. Frozen790f4f89d1d8cbe821903af79392134bfb1c6bbb; sourcewindow reused intentionally as development, no newfit or calibratedmodel. No policy contrasts before full8armgate. Output/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0/episodes/queueaware_20261021_timing_01. Preserve all failed/unattempted scope. Local raw mirror pending client reconnect.


## Timing study completed queueaware_20261021_timing_02 — 2026-10-21T18:01:46.744313+00:00
Actionstart_60, repeat0, raw/full-drain PASSED 3094queries. ResultSHA151d53d42daae4db9fe144d25433f82f8f38a2c70d8991c6c8e4f580901aab2e, eventsSHA3332eda3a789064614015ddaf8a6caf98662ae2c727e719563f9ef9369801851; sumresponse4146235201150722ns = rawoutstandingarea; mean1340.088947s, drain3808.132032s. Actualtiming{"actual_rewrite_start_after_arrival_clock_seconds": 62.832324869, "actual_rewrite_call_seconds": 14.533694642}. Frozen790f4f89d1d8cbe821903af79392134bfb1c6bbb; sourcewindow reused intentionally as development, no newfit or calibratedmodel. No policy contrasts before full8armgate. Output/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0/episodes/queueaware_20261021_timing_02. Preserve all failed/unattempted scope. Local raw mirror pending client reconnect.


## Timing study completed queueaware_20261021_timing_03 — 2026-10-21T19:10:20.673101+00:00
Actionstart_600, repeat0, raw/full-drain PASSED 3094queries. ResultSHA7dabe9cac53336ffa1c911aec4d1cec5bf4b5751897a5d00f918388da7e664c4, eventsSHA49b88d2ccc9db6aa8b5406776513efb2ebe0e130d55103f1bc760d5ad5723f23; sumresponse3859440145195632ns = rawoutstandingarea; mean1247.395005s, drain3591.570974s. Actualtiming{"actual_rewrite_start_after_arrival_clock_seconds": 601.230998998, "actual_rewrite_call_seconds": 14.691739291}. Frozen790f4f89d1d8cbe821903af79392134bfb1c6bbb; sourcewindow reused intentionally as development, no newfit or calibratedmodel. No policy contrasts before full8armgate. Output/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0/episodes/queueaware_20261021_timing_03. Preserve all failed/unattempted scope. Local raw mirror pending client reconnect.


## Timing study completed queueaware_20261021_timing_04 — 2026-10-21T20:18:56.411745+00:00
Actionno_action, repeat0, raw/full-drain PASSED 3094queries. ResultSHAf31d9a87ee58362df04971f2bf24378ab3f288a076cae0c9026bfbc00a93ca53, eventsSHA3f338004581d4e9913c0b992259a9cfff07ca659fee7362507f190760349192e; sumresponse3740014261006165ns = rawoutstandingarea; mean1208.795818s, drain3588.820194s. Actualtiming{"actual_rewrite_start_after_arrival_clock_seconds": null, "actual_rewrite_call_seconds": null}. Frozen790f4f89d1d8cbe821903af79392134bfb1c6bbb; sourcewindow reused intentionally as development, no newfit or calibratedmodel. No policy contrasts before full8armgate. Output/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0/episodes/queueaware_20261021_timing_04. Preserve all failed/unattempted scope. Local raw mirror pending client reconnect.


## Timing study completed queueaware_20261021_timing_05 — 2026-10-21T21:27:08.734457+00:00
Actionno_action, repeat1, raw/full-drain PASSED 3094queries. ResultSHA176b8fe05ab4855bc98e8ca755475069a91e2bcf78cad5e0a0866af0cb27fffb, eventsSHAc8f45bfcf6a244bbda70160203a1fd344f1f7186afef8b18f9c7d150283fb6c7; sumresponse3698598823982578ns = rawoutstandingarea; mean1195.410092s, drain3564.200220s. Actualtiming{"actual_rewrite_start_after_arrival_clock_seconds": null, "actual_rewrite_call_seconds": null}. Frozen790f4f89d1d8cbe821903af79392134bfb1c6bbb; sourcewindow reused intentionally as development, no newfit or calibratedmodel. No policy contrasts before full8armgate. Output/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0/episodes/queueaware_20261021_timing_05. Preserve all failed/unattempted scope. Local raw mirror pending client reconnect.


## Timing study completed queueaware_20261021_timing_06 — 2026-10-21T22:35:02.114203+00:00
Actionstart_600, repeat1, raw/full-drain PASSED 3094queries. ResultSHA37e9efa80c889a4421569db0305d1635416ec66804cee02e9af2920e880be70d, eventsSHA9f58e81eaf011e3e2ce97ac4921fe97cb5fc3ac54af516ed2a12f46aa89d7a82; sumresponse3685512253532714ns = rawoutstandingarea; mean1191.180431s, drain3552.678643s. Actualtiming{"actual_rewrite_start_after_arrival_clock_seconds": 601.528305906, "actual_rewrite_call_seconds": 14.556429725}. Frozen790f4f89d1d8cbe821903af79392134bfb1c6bbb; sourcewindow reused intentionally as development, no newfit or calibratedmodel. No policy contrasts before full8armgate. Output/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0/episodes/queueaware_20261021_timing_06. Preserve all failed/unattempted scope. Local raw mirror pending client reconnect.


## Timing study completed queueaware_20261021_timing_07 — 2026-10-21T23:42:28.752109+00:00
Actionstart_60, repeat1, raw/full-drain PASSED 3094queries. ResultSHA4214399f043505da697cb50b8556bd93e013f64fc7a2846b25f7b2fc7dde8e15, eventsSHA9724bf276effd77edccd3c1e5c9928cf7a06b5ee28178ab5b044ce1284ed94ce; sumresponse3642382076121891ns = rawoutstandingarea; mean1177.240490s, drain3519.788632s. Actualtiming{"actual_rewrite_start_after_arrival_clock_seconds": 61.421926402, "actual_rewrite_call_seconds": 14.547178174}. Frozen790f4f89d1d8cbe821903af79392134bfb1c6bbb; sourcewindow reused intentionally as development, no newfit or calibratedmodel. No policy contrasts before full8armgate. Output/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0/episodes/queueaware_20261021_timing_07. Preserve all failed/unattempted scope. Local raw mirror pending client reconnect.


## Timing study completed queueaware_20261021_timing_08 — 2026-10-22T00:49:51.467050+00:00
Actionstart_0, repeat1, raw/full-drain PASSED 3094queries. ResultSHA9dcf910020f1a7ec764f1763e988c03868d757c99bc7bb23553853d034b187dc, eventsSHAd1630de931830a578281f9dbebe23ff7f3e52d285b9507cf2eb43e4950c5c17d; sumresponse3649705551150489ns = rawoutstandingarea; mean1179.607483s, drain3516.918709s. Actualtiming{"actual_rewrite_start_after_arrival_clock_seconds": 0.51333119, "actual_rewrite_call_seconds": 15.405411879}. Frozen790f4f89d1d8cbe821903af79392134bfb1c6bbb; sourcewindow reused intentionally as development, no newfit or calibratedmodel. No policy contrasts before full8armgate. Output/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0/episodes/queueaware_20261021_timing_08. Preserve all failed/unattempted scope. Local raw mirror pending client reconnect.


## Physical timing study terminal review — 2026-10-22T01:13:23.333674+00:00
All8physicalarms/rawreconstruction complete. AnalysisSHA2502ecf5a65961700bad880d43d47677c71c41c148582fa46c53904ff2d52ba3, report/mnt/nfs-storage/shashank_prafullathta/implementation/results/queue_aware_timing_20261021/repeated_window0/analysis/report.md. Descriptive contrasts[{"repeat": 0, "action": "start_60", "sum_response_difference_ns_vs_immediate": -20320913291944, "fraction_lower_response": 0.004877148593176228, "meaning": "Observed repeated-development contrast, not an independent-day confidence/causal estimate."}, {"repeat": 0, "action": "start_600", "sum_response_difference_ns_vs_immediate": -307115969247034, "fraction_lower_response": 0.07370978832673536, "meaning": "Observed repeated-development contrast, not an independent-day confidence/causal estimate."}, {"repeat": 0, "action": "no_action", "sum_response_difference_ns_vs_immediate": -426541853436501, "fraction_lower_response": 0.10237276103349846, "meaning": "Observed repeated-development contrast, not an independent-day confidence/causal estimate."}, {"repeat": 1, "action": "start_60", "sum_response_difference_ns_vs_immediate": -7323475028598, "fraction_lower_response": 0.002006593388414468, "meaning": "Observed repeated-development contrast, not an independent-day confidence/causal estimate."}, {"repeat": 1, "action": "start_600", "sum_response_difference_ns_vs_immediate": 35806702382225, "fraction_lower_response": -0.009810846897207348, "meaning": "Observed repeated-development contrast, not an independent-day confidence/causal estimate."}, {"repeat": 1, "action": "no_action", "sum_response_difference_ns_vs_immediate": 48893272832089, "fraction_lower_response": -0.013396497922051998, "meaning": "Observed repeated-development contrast, not an independent-day confidence/causal estimate."}]. Repeatedlowerresponseactions['start_60']; no causal/generalization/calibration/novelty accepted. Only two repeats of one development arrival window; actualstartlateness/tableendstates and all negative outcomes retained. No refit. Rawbackup/localHEADsync deferred until client returns; immutable rawoutputs onworker3.


## Independent trace/dataset binding audit — 22 October 2026
Purpose: verify the actual trace-to-benchmark implementation after the user requested accuracy checks. Source revision90f59d3ae987f33a29f08a7a34349669daf72600; scriptSHA15639d0bc1ad131e48337620c3b14276aa4ae9b9582582229bdb5dd93fc116db; physical runtime790f4f89 unchanged. Detached worker3 wrapper/client1158443/1158444, 03:05:24–03:06:00UTC; log results/trace_dataset_binding_20261022/audit.log, result audit/result.json SHAb3358b7c4f652d2397f874fdbe53e81f1aa14472b12a478319ca97efbf23576b. PASSED independent scan of2,760,971 exported arrivals, exact3094 source-window IDs/timestamps/offsets/round-robin mappings and all24,752 actual SQL/table/snapshot/offer/FIFO/drain bindings across8runs. Separate detached checksum check confirmed current original lineitem.tbl and generator manifest match registered ingestion hashes; dataset_checksum.log bothOK. No newSQL, fitting, physical replay, failures or changed old outcomes. Fresh raw archive/Parquet validation and generator rebuild NOT performed; historical source custody limitations retained. Supersedes any implication that actual releases occur exactly on schedule or these are the official TPC-H suite: four custom lineitem templates, imposed774/774/773/773 mix, not original Snowset SQL/cost correlations. Actual per-run median generator lateness3.389–31.960ms, p99 253.747–508.956ms, worst1162.967ms, included in response time; serial/instrumentation conditions remain. Details queue_aware_maintenance/TRACE_DATASET_AUDIT_2026-10-22.md. Next gate independent workload/SQL-mix representativeness and repeatability; no causal scheduling/calibration/novelty claim. Audit artifacts mirrored; full earlier physical raw mirror remains separately pending verification.


## Queue package organization — 22 October 2026 (validation pending)
Purpose: user requested clear folder structure. Moved source into core/models/policies/runtime/preparation/observability/audits/analysis, documents into package docs/guides/plans/reviews/operations; layout_manifest.json records every previous location. Added explicit package imports, direct-script bootstrap, shared package/repository/source path resolution, grouped source archiving and flat/grouped manifest hash lookup with ambiguity rejection. Root README is the navigation entry; historical README preserved in docs/operations. Protocol JSON, frozen instrumentation primitives, results, datasets, services and frozen worktrees unchanged. No active queue experiment found before edits; unrelated worker3 methodology/model dirt and local pycache preserved. Historical hashes are not rewritten: future physical runs require new registrations/proofs; no reuse of old acceptance claims. Worker3 detached real-source validation will check imports/direct and module entrypoints and reconstruct all recorded trace bindings; no SQL/fitting/new physical collection. Final actual validation status/log/PID/hash follows in an append.


## Queue package organization — verified completion, 22 October 2026
Supersedes validation-pending status above. Implementation revision99f74126ece26c2988756e097b6f72e6acbc27be. Worker3 detached failure-alert wrapper1160924, results/queue_package_layout_20261022/launch.json and validation.log; started03:13:35UTC, completed03:14:16UTC. PASSED41 relocated module imports,27 command entrypoints in both direct-file and package-module forms, Python source parsing and actual recorded trace binding for all8episodes/24,752queries. ResultSHA d81305b7772b7dc173c807c350f9283d0108e9e2acb309d5520084f838981705; nested actual-trace auditSHA d5fd85d4b121ec04df1c2c36876056df2efa835d798cdd9eca36bea1d4d8cd2f. NoSQL, fitting, fabricated data or physical rerun. No validation failures. Frozen physical checkout still790f4f89d1d8cbe821903af79392134bfb1c6bbb; gitdiff confirmed instrumentation and all historical protocolJSON unchanged. Source/path/import organization only; no new scientific acceptance. New registrations/proofs required before future physical collection because source hashes changed. Validation evidence mirrored with itemized checksum verification. README maps folders; layout_manifest maps all41source and10document moves; original README preserved as an additional historical document. Both methodology documents updated; targeted GitHub publication and canonical worker3 fast-forward/SHA verification performed for this unit. Unrelated dirt/archive retained.


## Explicit two-chat ownership and Antigravity handover — 22 October 2026
User assigned exploring novelty chat to queue-aware implementation and Main chat to the original three-model implementation, with possible future evidence-gated hybrid. Saved docs/queue_three_model_handover_2026-10-22.md covering pipeline, organized package, all failed/incomplete/completed cohorts, eight-arm descriptive results, trace/dataset accuracy and release lateness, consumed held-out model family, missing causal/calibration/generalization evidence, and shared predictor/planner integration contract. Worker3 physical/heavy fitting must not compete; both chats share a dirty checkout, so queue code ownership and exact-path staging/shared-doc append coordination are explicit. User authorized messaging the existing model chat; no new chat or subagent required. Added queue_aware_maintenance/docs/operations/ANTIGRAVITY_TASKS_2026-10-22.md with a bounded read-only navigation-inventory prompt and future delegation safeguards; Antigravity is manually relayed, not connected or claimed launched. No new SQL/test/fit/physical campaign/automation, no revised scientific results. Next queue gate remains repeatability/measurement/workload and faithful baselines; Main starts with model/schema/readiness audit, not old-test refit or joblib promotion. Methodology histories updated and targeted publication/server sync required before dispatch.


## Three-model track: candidate contracts and readiness registration — 22 October 2026

Main owns new three_model_maintenance/; queue_aware_maintenance/ and frozen runtimes untouched. Read handover0131e00, publication/model plans, historical execution receipts and current exports. Added strict candidate-only A/B/C/rewrite units/condition/support/evidence/time contracts and read-only readiness command plus phase plan. A/B use observed client pending, not inferred engine activity or causal A-minus-B; C original SQL mix/ingestion/CPU unsupported. Existing18episode corpus/consumed test and historical count forecast SHA-bound in three_model_maintenance/protocols/readiness_20261022.json. Audit will reconstruct source families and joint SQL/layout/state/complete-history support, availability frontier and consumed-history blockers without fitting/scoring/loading models. No policy predictions or numeric acceptance thresholds invented. Old negative results and all failed/unattempted cohorts retained.

Prelaunch worker3 idle: no Pythonjobs, Spark runningjobs empty; handover fast-forward already restored local/server0131e003. Unrelated dirty legacy model/docs/pycache/archive preserved. Code source prepared, worker3 validation pending (no local tests). Planned detached run results/three_model_readiness_20261022, log results/three_model_readiness_20261022_launch.log, failure receipt results/three_model_readiness_20261022_failure_alert.json; ETA1–2minutes. Exact PID/revision/result SHA will follow. This unit does not implement fitted A/B/C, calibration, a scheduler or new physical collection; blocked support will remain blocked.


### Three-model readiness: observed initial outcome and support-report correction

Worker3 registered audit revision2f78e1f, wrapper1175549,04:12:09UTC22Oct completed without fitting/scoring/SQL. Existing18episodes/3families/9923query/12rewrite rows verified; eligibleA70/B4856, familiesA22/25/23andB1569/1647/1640,4rewrites each. Historical family2 consumed; no new fitting authorized. First report results/three_model_readiness_20261022/result.json retained/mirrored. Source review found support enumeration only included combinations observed somewhere; this omitted all-zero combinations. Register v2 output with Cartesian actualqueryID×actuallayout×pendingstate support census to make unsupported cells explicit; this creates no data/labels. Inputs/eligibility/evidence/acceptance unchanged. This is an audit reporting correction, not model retry or test reevaluation. Forecaster remains historical aggregate diagnostic; no original SQLmix/ingestion/CPU support. Richer A plannedrewrite inputs and feature UTC availability bridge absent from export. Candidate contracts parsed/imported by server; functional prediction validation still awaits actual bound model/request records.


## Three-model candidate readiness — verified completion, 22 October 2026

Implemented separate package/contracts/audit/plan; corrected worker3 auditv2 completed under66ab2ae, wrapper1176176. ReceiptSHA764dacc28c7cc8104f759c496500359a3270d575d6cf853ba0293866eb16e5e3 mirrored and matched server. All9923queries/12rewrites/18episodes/3families remain recorded; completehistoryA70/B4856, familyA22/25/23,B1569/1647/1640,4rewrites each. V2 emits24query×layout×state cells per family, including4unsupported onefile/pendingTrue cells each (12total); no synthetic rows or forced coverage. First audit retained; no fit/testscore/SQL/joblibloading or new physical runs, no failures. Missing4997completehistories remains explicit. No new independent fitting authorized on consumed families. See three_model_maintenance/docs/READINESS_REVIEW_2026-10-22.md and IMPLEMENTATION_PLAN_2026-10-22.md for raw UTCavailability adapter, fresh source/fit-registration gates, A/B/shared comparison and past-only C packaging next. Contract source parsed/imported only; semantic runtime prediction validation remains pending real bound artifacts. Queue code/ownership and unrelated dirtyfiles preserved; targeted GitHub push/serverff/HEAD+intendedSHA agreement performed. No model/calibration/scheduler/novelty acceptance.


## Queue continuation: post-hoc repeatability/clock inventory registered — 22 October 2026
Queue chat resumes separately from Main three-model track. Added analysis/analyze_timing_repeatability.py and protocols/posthoc_queue_clock_inventory_20261022.json under queue_aware_maintenance. Purpose: independently hash terminal8arm raw ledgers and reconcile actual foreground SQL service plus outside-call gaps to last-result walltime; distinguish accumulated request waiting, due-request gaps, actual-offered backlog gaps, per-template measured call distributions and within-action repeat changes. Original comparison/sourceCSV hashes and diagnostic source hash bound; every3094request arm required, no survivors. Inventory original20minute source-clock bins/minute counts without selecting launches or inventing empty intervals/idleCPU/independent eligibility. All post-hoc/descriptive: outside-call time is NOT assumed removable observer overhead or causal maintenance harm. No fitting, newSQL, altered old policy, changed cutoff or physical rerun. Worker3check after transient approval-review timeout succeeded; no competing queue/train process found, Main completed read-only readinessv2. Validation pending detached failure-alert wrapper, unique results/queue_repeatability_clock_20261022; expected check about2minutes. Old failed/incomplete scopes and unrelated dirtyfiles preserved. Actual outcome/PID/log/hashes will follow.


## Queue repeatability/clock inventory — completed 22 October 2026
Detached worker3 diagnostic5d46ce7 wrapper/client1177468/1177469 passed04:18:19–04:18:38UTC; noSQL/fitting/physical rerun, no failures. ProtocolSHAb27a42de95d59697b062bce151780ea5d8b846f86a486f968328f8fab16c248b; sourceSHA16d50afe241bf51a216b1e99ee0d9281944437b2fadce8f7e0a1a5716dffb677. Mirrored results/queue_repeatability_clock_20261022/analysis/result.json SHA8d8ffdcddb288d266f37316d0348d25b0ba9491460b418777e82bd86f33e0e9f; itemizedchecksumdryrun no differences. Every raw ledger hash and integer call+gap walltime/response partition matched. Outside-foreground-call walltime23.05–28.96%; immediate repeats: service2714.68→2704.20s, outsidecall1106.61→812.72s, so293.89of304.36s elapsed improvement (~96.6%) outsidecalls. This is accounting, NOT causal/removable overhead; gap includes metadata/archive/freshness/client/scheduling and possible maintenance overlap. About99.93% summedresponse is waiting; walltime versus accumulatedwaiting explicitly distinguished. Source inventory2,760,971arrivals/894nonempty20minute bins1688–3370arrivals; not complete-window/independence/idleCPU/launch selection. Review queue_aware_maintenance/docs/reviews/MEASUREMENT_REPEATABILITY_2026-10-22.md. Next gate recordedREST/wait/archive interval-overlap diagnosis, then strictly gated measurement-repeatability proof before another physical campaign or small-gain claim. Old raw bulkbackup process absent, local1.7GB vsserver~2.5GB; resumed detached transportPID39793, logs/terminalchecksumreceipt results/queue_backup_resume_20261022, stillpending rather than claiming complete mirror. Frozen runtime and unrelated dirt retained, Mainthree-model package untouched.


## Three-model integrity work: source and raw feature binding registration — 22 October 2026

User explicitly requests genuine three-model implementation, no dummy code/false reporting/fallback predictions. Expanded package implementation plan with staged source/raw/split/A-B-shared/C/newdata/calibration/claims gates. Implemented hash-pinned bounded source_integrity audit and preparation.bind_raw_features. New path forbids legacy weight-loader/trace/queue imports; old live entrypoint and decide raise behavior checked structurally; historical metadata inventoried but not accepted or deserialized. Raw binder checks candidate UUID/SQL/table/snapshot/layout/host/call/target against18realrawlogs and compares timestamp-derived flags/counts with actual prior-log-prefix state. EventLog recorded time is capture before fsync: no exact durability timestamp fabricated; bound output retains capture, actual later callbound, exactavailabilityNone and runtimeacceptanceFalse. All prior candidates/tests/results preserved. Standalone empirical baselines remain competitors; new unsupported inference must not silently substitute them.

Source/data job registration: three_model_maintenance/protocols/source_integrity_20261022.json and raw_feature_binding_20261022.json, expected1–3minutes each under detached worker3 failure wrappers, outputs results/three_model_source_integrity_20261022 and results/three_model_raw_features_20261022. Before edits actual sharedHEAD5d46ce7/localserver equal, noPythonjobs/Sparkrunningjobs. Queue owner diagnostic completed and raw transport may still run; no competing physical/heavyfit launched. Validation pending; no claim repository-wide semantic purity or A*acceptance, no model fitting or scheduler launch. Exact logs/PIDs/results/limitations follow.


## Three-model integrity audits — actual completion, 22 October 2026

Implementation29834c9047f97b5d3715323030b64730ecf73de1. Detached worker3 failure-alert wrappers1179956(source)/1180090(raw) completed, no execution failures. Source audit passed registered13-file structural boundaries only, receiptSHAf303a77e70830837f234483881b0a4abd15a67e44d8b3c49386f0c792d982625. Raw binder checked9923queries/18episodes against real raw logs, receiptSHA7ea62756ce2d4dd2cd5453633a8ad20bd8ba9b30a43a231fb7cd46834415606e; one ambiguity retained: sf1_consistent_20261016_14/5883c0cba14a482788d2f60243156d7e timestamp-derived pending differs from prior-log-prefix. No silent relabel or oldCSV edits; historical_binding_consistentFalse. Exact feature publication remains unknown because recorded stamp precedes fsync; later actual call is a bound, runtime_adapter_acceptedFalse throughout. All consumed-history rows remain fresh_training_eligibleFalse. Local legacy metadata8features versus preserved server13features (correction to local-only earlier statement); neither accepted, no weights loaded. No fit/testscore/SQL/newphysical run or scheduler. Raw audit04:27:23.977–04:27:32.212UTC; logs results/three_model_source_integrity_20261022_launch.log and three_model_raw_features_20261022_launch.log. Result directories and boundJSONL mirrored, local/server SHA agreement; boundSHA95bd3748b7734dc66c9cc07c441eda26de2269e95b4370064ebee8fbf1323db3. Detailed review three_model_maintenance/docs/INTEGRITY_REVIEW_2026-10-22.md. Next source-registry/fit-registration gate, then honest A/B/shared and past-only C candidates; fresh independent data/calibration/decision evidence needed. Source checks are bounded assurance, not repository-wide purity or A*readiness. Shared queue code and unrelated dirt preserved; targeted publication/serverff/SHA verification required for this completion record.


## Three-model consumed-source gate registration — 22 October 2026

Implemented preparation/fit_registration.py and SHA-bound consumed_inventory_20261022.json. Purpose: prevent a new family label or split from laundering consumed historical data. Inventory reconciles actual18episode manifest, raw binding, readiness and consumed-test receipt; preserves one ambiguous measurement. Dependency guard compares overlapping source-clock intervals or shared dependence group within a registered namespace, whole-family roles only. Structural prospective registration requires declared predictor contract, no prediction substitution, candidate-only status; always fit_authorizedFalse pending raw bounds/identity and immutable pre-outcome freeze audit. No genuine fresh registration exists, so do not claim prospective path end-to-end validation. Namespace is conservatively the historical cohort, not independently verified global warehouse identity; new names never prove independence. Missing lookback/target-expanded bounds remain a blocker, not invented. Planned actual detached worker3 inventory (~1minute), unique results/three_model_consumed_inventory_20261022, failure wrapper and actual consumed-family guard checks. No fitting/old-testscore/SQL/newcollection. Final PID/result/hash follows after execution; queue code/unrelated dirt untouched.


## Consumed-source inventory — actual completion, 22 October 2026

Source revision3efc02ea7052c9f46151e574775064464f9edc37, sourceSHA431251d3d3509388c851195f11daba9222e840b40e9783b7fca6fd56520e0949, protocolSHAc206e34884cdea28a6746e7b008c863a42e9272328c8f6b88bf0184081e8518e. Detached worker3 run05:24:32.984–05:24:32.997UTC completed_consumed_inventory_not_fit_authorization. Launcher shell PID1194025 was captured; wrapper/client PIDs were not separately retained (do not misreport launcher as wrapper). Log results/three_model_consumed_inventory_20261022_launch.log; actual report result.json SHA25d810b5c62a2f5e0fc82adedb39fe98330ab702d811236a74d3656cac7416d7 and consumed_registry.json SHAe7918bdb77440e2e041572414432d54990c42f3edb1fed8317983a3035308495 under results/three_model_consumed_inventory_20261022. Mirrored exact local/server hashes. Actual18episodes/9923queries reconciled into3families; each real historical family detected by consumed_dependencies helper used by prospective guard. Single known mismatch retained; no attempt to manufacture clean source histories. No execution failure, model fit/test scoring/SQL/physical collection. Prospective full validation remains unexercised without real new registration; no namespace/expanded-bound/freeze/clock proof implied by this inventory. fit_authorizedFalse remains explicit. Next implement estimator source under this boundary, and independently inventory/register fresh source bounds before any training; no calibration or publication acceptance. Shared queue code and unrelated dirtyfiles preserved. Completion documentation targeted commit/push/serverff and exact intended hashes required.


## Step 1/2 source implementation and organization registration — 22 October 2026

User requested organized package plus simultaneous A/B/shared implementation and measurement repair. Added models/latency.py (separateA/B/shared with explicit compact logRidge/tree specifications, independent SQL/SQL-layout/SQL-layout-state medians, no substitution), evaluation/paired.py (all-ID unsupported ledger/common equalepisodeMAE/null when empty), runtime/publication.py (locked/versioned this-client queue/maintenance state, after-fsync observed bounds, capture/process/boot identity, actual opt-in cursor wrappers with freshness/cutoff/refusal/failure evidence). Training entry requires independently verified permission bound to actual row/evidence hashes/specifications; no existing source grants it. Common features/rows do not imply equal aggregate parameter count for two separate versus one shared model. Explicit parameters and conservative numeric-box/joint-cell support rationale in three_model_maintenance/docs/plans/MODELS_AND_CAPTURE_2026-10-22.md. Newcode separated models/runtime/evaluation; legacy docs/protocols/frozen physical paths left unchanged for hash integrity. No queue ownership changes.

Registered read-only actual-evidence audit: protocols/model_measurement_20261022.json, output results/three_model_model_measurement_20261022, expected1–2minutes detached worker3 failurewrapper. It will decode actual9923rows, reject historical receipts as live publication, preserve quarantine, construct estimator families without fits, check actual inventory blocks training and all-unsupported coverage has null scores. No dummy records/cursors/labels or old-test predictions. Fresh prospective fit, new journal concurrency/persistence/cursor behavior and physical integration remain unvalidated; no automatic runtime acceptance, exact storage-commit claim or calibration. Queue/server active-work inventory found no competing matching Pythonfit/measurementjob; original unrelated dirtyfiles preserved. Actual logs/PIDs/results/hashes follow after run.
