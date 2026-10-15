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
