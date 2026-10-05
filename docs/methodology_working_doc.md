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
