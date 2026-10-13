# Methodology & Master Working Document (v2: Cost-Benefit Optimizer)
## Learned, Uncertainty-Aware Scheduling for Lakehouse Storage Maintenance

**Status:** Living Master Document. Updated October 6, 2026.  
**Audience:** Peer Researchers, Advisors, and Project Collaborators.

---

## 1. Executive Summary & Research Question

### 1.1 Core Research Question
> **Given that lakehouse storage maintenance (e.g., Apache Iceberg `rewrite_data_files` compaction) must be performed, *when* should it be executed to maximize storage efficiency while minimizing interference with concurrent analytical query workloads?**

### 1.2 Key Differentiation
- **What this project IS:** A dynamic, uncertainty-aware timing and scheduling decision engine.
- **What this project IS NOT:** A new compaction algorithm or table-layout optimizer.
- **Novelty:** Existing work determines *what* or *whether* to compact. None model maintenance interference as an explicit function of concurrent workload state, and none provide calibrated, distribution-free uncertainty bounds (conformal prediction).

### 1.3 The Phase 6 Pivot: From Reactive to Proactive
In Phases 3–5, the scheduling agent was **Reactive**: it asked "Is it safe to compact right now?" and used a hardcoded starvation limit ($k=3$ max deferrals) as a safety net. This led to a 34% forced override rate, undermining the ML framework.

In Phase 6, we pivot to a **Proactive Cost-Benefit Optimizer** (Model Predictive Control). The agent asks: "Is the predicted damage of compacting now less than the predicted damage of letting fragmentation grow?" The ML model autonomously dictates the deferral limit. No hardcoded $k$.

### 1.4 Decision Space
At any evaluation timestep, the scheduling agent outputs:
- `RUN`: Execute maintenance immediately (cost of compacting < cost of deferring).
- `DEFER`: Postpone maintenance (cost of deferring < cost of compacting).

There is **no FORCED_OVERRIDE** action. The model itself handles starvation naturally: as fragmentation grows, $C_{defer}$ rises until it inevitably exceeds $C_{compact}$.

---

## 2. Prior Phase Summary (Phases 0–5)

All prior work is retained from the original methodology document. Key milestones:
- **Phase 0–2:** Spark 3.3.4 + Iceberg 1.4.3 setup, noise-floor baseline (CV=3.25%), task-level telemetry proof.
- **Phase 3A–3B:** 528 query + 44 compaction physical trials, audit (fixed scaling & timestamp leakage), OOD extrapolation proof (MAE 117%, coverage collapse at 24.6%).
- **Phase 4:** 4.13-hour continuous run, Director's Audit (caught stochastic compaction bug, conformal contamination), 15-min vindication run.
- **Phase 5:** 8-policy offline evaluation suite. ConformalRisk policy achieved 83.23% completion with 0% SLA violations. TemporalConformal reached 87% completion with 4.5% forced overrides.

> **Full archival details:** See [updated_methodology_working_doc.md](file:///home/shashank/.gemini/antigravity/brain/5e14b653-0a3b-4484-b6b2-f8b697861d3b/updated_methodology_working_doc.md)

---

## 3. Phase 6 Architecture: The Cost-Benefit Optimizer

### 3.1 Core Decision Logic (Model Predictive Control)

At every decision tick (every 60 seconds), the agent computes:

$$C_{compact} = \text{Model}_A(\text{SystemState}) + \hat{q}_A$$

$$C_{defer} = \text{Model}_B(\text{SystemState}, \text{frag\_files} + \Delta f) + \hat{q}_B$$

Where:
- $\text{Model}_A$ predicts query latency **during active compaction** given current system load.
- $\text{Model}_B$ predicts query latency **without compaction** given current system load and growing fragmentation.
- $\hat{q}_A$, $\hat{q}_B$ are the conformal calibration bounds for each model (at $\alpha = 0.05$).
- $\Delta f$ is the projected number of new fragments the `WriteDriver` will produce in the next decision window.

**Decision Rule:**
```
if C_compact < C_defer:
    action = "RUN"
else:
    action = "DEFER"
```

### 3.2 Why This Eliminates Hardcoded $k$
- Early in the experiment, fragmentation is low → $C_{defer}$ is small → agent defers.
- As the `WriteDriver` adds files, fragmentation grows → $C_{defer}$ increases.
- Eventually $C_{defer}$ exceeds $C_{compact}$ → the agent autonomously chooses to compact.
- After compaction, fragmentation drops → $C_{defer}$ drops → agent defers again.

This creates a natural, data-driven oscillation with zero hardcoded thresholds.

### 3.3 Why the Existing Phase 3B Model Cannot Be Used

> [!CAUTION]
> The saved `best_regressor.joblib` from Phase 3B has three critical incompatibilities with the Phase 6 Cost-Benefit architecture:

1. **Wrong Prediction Target:** It predicts QIR% (interference ratio during compaction), not absolute query latency. We need two models that predict absolute latency in two different regimes.
2. **Feature Leakage:** It expects `baseline_duration_ms` and `concurrent_duration_ms` as inputs — these are outcomes, not predictors. They cannot be known at inference time.
3. **No Temporal Features:** It was trained on point-in-time snapshots (`pre_cpu_util_pct`), not rolling temporal averages (`cpu_util_avg_1min`, `cpu_util_avg_5min`, `cpu_trend`).

**Resolution:** Phase 6A will collect a new training dataset with the correct schema.

---

## 4. Phase 6 Execution Plan

### Phase 6A: Data Collection Run (~4 hours on `worker3`)
**Goal:** Collect a clean training dataset with temporal features and both compaction/no-compaction regimes.

**Setup:**
- Start Spark Thrift Server with Iceberg on `worker3`.
- Run the `WriteDriver` to continuously fragment the table.
- Run the `WorkloadDriver` (driven by GoogleTraceMapper intensity) to generate read queries.
- Run compactions at **fixed deterministic intervals** (e.g., every 20 minutes) to ensure we capture both regimes.

**What we log at 1Hz:**
| Feature | Source | Type |
|---------|--------|------|
| `cpu_util_pct` | `psutil.cpu_percent()` | Instantaneous |
| `cpu_util_avg_1min` | Rolling mean of last 60 samples | Temporal |
| `cpu_util_avg_5min` | Rolling mean of last 300 samples | Temporal |
| `cpu_trend` | `cpu_avg_1min - cpu_avg_5min` | Temporal |
| `mem_used_pct` | `psutil.virtual_memory().percent` | Instantaneous |
| `disk_io_read_bytes` | `psutil.disk_io_counters()` | Instantaneous |
| `disk_io_write_bytes` | `psutil.disk_io_counters()` | Instantaneous |
| `frag_file_count` | `SELECT count(*) FROM table.files` | Table State |
| `table_size_mb` | `SELECT sum(file_size_in_bytes) FROM table.files` | Table State |
| `avg_file_size_kb` | Derived: `table_size_mb / frag_file_count` | Table State |
| `query_latency_ms` | Per-query wall-clock time | Target (Model B) |
| `compaction_active` | Boolean: is compaction running? | Label |
| `query_latency_during_compaction_ms` | Latency when `compaction_active=True` | Target (Model A) |
| `intensity` | GoogleTraceMapper output | Workload Shape |

**Deliverable:** A CSV with ~14,400 rows (4 hours × 1Hz) containing all of the above.

### Phase 6B: Train Two Models (~1 hour)
**Goal:** Train Model A and Model B on the Phase 6A dataset.

- **Model A (Compaction Regime):** Filter dataset to rows where `compaction_active=True`. Train a GradientBoosting regressor to predict `query_latency_during_compaction_ms` from the temporal system features. Calibrate conformal bound $\hat{q}_A$.
- **Model B (Baseline Regime):** Filter dataset to rows where `compaction_active=False`. Train a GradientBoosting regressor to predict `query_latency_ms` from the temporal system features + `frag_file_count`. Calibrate conformal bound $\hat{q}_B$.
- Split: Chronological 70/15/15 (Train/Calibration/Test). No shuffling.

**Deliverable:** `model_a_compaction.joblib`, `model_b_baseline.joblib`, and their conformal $\hat{q}$ values.

### Phase 6C: The 8-Hour Master Evaluation
**Goal:** Run the final A/B comparison using the Cost-Benefit Optimizer.

1. Run `reset_table_state.py` to set the table to a known fragmented state.
2. **Run A (8 hours):** SOTAThresholdPolicy (industry baseline: compact when `frag_files > threshold`).
3. Run `reset_table_state.py` again.
4. **Run B (8 hours):** CostBenefitPolicy (our ML optimizer using Model A vs Model B).

**Metrics logged per tick:**
- Rolling p95 query latency (last 5 minutes)
- Rolling SLA violation rate (last 5 minutes)
- `frag_file_count` trajectory
- $C_{compact}$ and $C_{defer}$ values (for the "Hero Graph")
- Compaction decisions and durations

**The Hero Graph:** A time-series plot showing:
- The Borg intensity curve (background shading)
- Baseline p95 latency (red line, spikes during peaks)
- Our optimizer's p95 latency (blue line, stays flat because it defers during peaks)
- Vertical markers showing when each policy chose to compact

---

## 5. Comparison: Old vs New Architecture

| Aspect | Phase 5 (Reactive) | Phase 6 (Proactive) |
|--------|---------------------|---------------------|
| Decision | "Is it safe to compact now?" | "Is compacting cheaper than deferring?" |
| Starvation Protection | Hardcoded $k=3$ | Eliminated. Model handles it naturally. |
| ML Role | Bounds the risk of compacting | Weighs two competing costs |
| Forced Overrides | Yes (34% in early sims) | None. Model autonomously decides. |
| Temporal Awareness | None (point-in-time) | Rolling 1min/5min CPU/IO trends |
| Training Data | Phase 3B (528 point-in-time trials) | Phase 6A (4-hour continuous temporal run) |

---

## 6. Project Artifacts & Key Documents

- **Original Methodology:** [updated_methodology_working_doc.md](file:///home/shashank/.gemini/antigravity/brain/5e14b653-0a3b-4484-b6b2-f8b697861d3b/updated_methodology_working_doc.md)
- **Phase 6 Critical Evaluation:** [phase6_critical_evaluation.md](file:///home/shashank/.gemini/antigravity/brain/5e14b653-0a3b-4484-b6b2-f8b697861d3b/phase6_critical_evaluation.md)
- **Director's Audit (Phase 4):** [phase4_audit_report.md](file:///home/shashank/.gemini/antigravity/brain/5e14b653-0a3b-4484-b6b2-f8b697861d3b/phase4_audit_report.md)

---

## 7. Phase 6 Master Evaluation Audit (RUN_002) & Methodological Upgrade (v2.1)

### 7.1 What Was Achieved (Empirical Baseline)
On October 13, 2026, the complete 20-hour master evaluation (`RUN_002`) executed end-to-end on cluster node `worker3` (10 cores, 64 GB RAM, high-speed network storage) against Apache Iceberg on TPC-H SF100 (~60M rows, ~13 GB).
* **Zero system failures:** 20 continuous hours of distributed Spark 3.3.4, PyHive, and Iceberg maintenance without service crash or data corruption.
* **Empirical micro-compaction scaling:** Confirmed that rewriting 3–4 small files takes ~11s, whereas table-wide compaction of 593 files takes 360–420s.

### 7.2 Forensic Audit Findings (Internal Data Analysis & External Peer Review)
A rigorous audit of raw CSV logs and models revealed five critical design defects:

1. **Unmodeled Query Heterogeneity Caused Bimodal ML Inversion:**
   - Workload rotated across 4 queries: Q0, Q2, Q3 took ~3.5–4.2s; Q1 (group-by aggregation) took ~49.0s.
   - The ML models had no `query_id` feature, yielding a 22–25s MAE and forcing conformal quantiles ($\hat{q}$) to ~40–50s.
   - Model B predicted baseline queries took 58.5s while Model A predicted compaction queries took 43.3s ($\text{pred}_b > \text{pred}_a$). The ML agent concluded compaction speeds queries up by 15s.
2. **Compaction Actuation Loop & No-Op Invalidation:**
   - Because $\text{pred}_b > \text{pred}_a$, the agent fired `RUN` 61.3% of all ticks (and 77.9% in BURST).
   - 144 out of 225 compactions (64.0%) completed in $\le 0.5$s (median 0.17s) on tables with $\le 35$ files. Iceberg rewrote 0 files because rewrite thresholds were not met.
3. **Training Data Fragmentation Starvation:**
   - Phase 6A triggered compactions every 5 minutes, trapping `frag_file_count` strictly within $[32, 40]$ ($\sigma=1.58$).
   - The models never observed fragmented states (50–200 files), driving feature importance of file count to 0.01% (Model A) and 1.5% (Model B), with zero correlation to deferral decisions.
4. **Latency Reduction Was an Optical Artifact of Binning:**
   - The reported 7.95% P95 latency reduction was driven by 54 timing-offset windows where the 49s query was in-flight when the 60s window closed.
   - Across all quantiles from p50 to p99, the agent was slower than the baseline (+1.9s at p75, +6.2s at p90) due to continuous compaction contention.
5. **Statistical and Methodological Rigor Gaps:**
   - Model A conformal test split comprised only 12 rows ($11/12 = 91.7\%$).
   - Evaluation compared $N=1$ run against $N=1$ run without counterbalancing, p-values, or effect sizes.
   - Baseline threshold (200 files) was overly conservative (only 3 compactions in 8 hours).
   - 492ms SLA from SF1 was retained post-hoc instead of setting an SF100-calibrated SLA a priori.

### 7.3 Methodological Upgrades (v2.1 Specifications)

1. **Feature Space & Query Normalization:**
   - Add one-hot encoded `query_id` (or query category) to the training and inference feature vector:
     $$\mathbf{x} = [\text{cpu\_1m}, \text{cpu\_5m}, \text{cpu\_trend}, \text{mem\_pct}, \text{frag\_files}, \text{table\_mb}, \text{intensity}, \mathbf{q}_{\text{id}}]$$
   - Target variable prediction MAE drops from ~25s to $<1.0$s, allowing calibrated conformal bounds.
2. **Dynamic Training Ingestion & State Exploration:**
   - In Phase 6A data collection, decouple writes and compactions: allow fragmentation to sweep dynamically across $[33, 150]$ files before initiating compactions.
3. **Principled Action Space & No-Op Prevention (No Magic Numbers):**
   - Eliminate hardcoded magic numbers like `frag_file_count - 33 >= 10`.
   - Instead, query Iceberg table metadata to inspect actual candidate small files:
     `SELECT count(*) FROM table.files WHERE file_size_in_bytes < target_file_size_bytes`
   - If candidate small files $== 0$, compaction is not an eligible action in the action space (you cannot compact non-existent small files).
   - In the execution engine, parse the return value of `CALL rewrite_data_files` (`rewritten_data_files_count`). If 0 files were rewritten, log the tick as `NO_OP`, not as an active compaction event.
4. **Horizon-Based Cost Formulation:**
   - Replace point-in-time single-step latency comparison with cumulative horizon cost:
     $$\text{Cost}_{\text{compact}} = \text{Transient query latency penalty during rewrite window}$$
     $$\text{Cost}_{\text{defer}} = \sum_{t=1}^{H} \Delta \text{Latency}(\text{accumulated small files over next } H \text{ ticks})$$
5. **Rigorous Baselines Against Published Literature (Defeating the Strawman):**
   - Replace the inert 200-file strawman with two peer-reviewed and industry-standard baselines:
     * **Baseline 1: AutoComp Policy (Gruenheid et al., VLDB 2024 / Microsoft & LinkedIn):**
       Evaluates storage traits by computing the uncompacted small-file reduction ratio:
       $$\Delta F_c = \frac{N_{\text{small\_files}}}{N_{\text{total\_files}}}$$
       Triggers compaction whenever $\Delta F_c \ge 0.20$ (or candidate small files $\ge 30$). Crucially, AutoComp optimizes purely based on table storage traits and is *completely blind* to concurrent query traffic and dynamic host CPU load.
     * **Baseline 2: Periodic Cron Baseline (AWS EMR / Databricks default):**
       Executes compaction on a deterministic 60-minute interval regardless of traffic or system contention.
     * **Baseline 3: Tuned Auto-Optimize Threshold:**
       Compacts when small files $\ge 40$, representing an active threshold policy rather than an inert 200-file barrier.
6. **A Priori Grounded SF100 SLA:**
   - Establish baseline P95 on a clean table under read load (~4.5s for fast queries, ~49s for heavy query); calibrate SLA at $1.5 \times \text{clean P95} = 6.75$s (for fast queries) and $75.0$s (for heavy query), documented a priori.
7. **Multi-Trial Counterbalanced Protocol:**
   - Execute 3 repetitions of 4-hour evaluation cycles per condition with interleaved ordering (Baseline $\rightarrow$ Agent, Agent $\rightarrow$ Baseline, Baseline $\rightarrow$ Agent).
   - Restore the Phase 2H/2I statistical verification pipeline: Shapiro-Wilk normality testing, paired Wilcoxon signed-rank tests across matching workload intervals, matched-pairs rank-biserial effect sizes, and Holm-Bonferroni correction.

### 7.4 Phased Implementation Roadmap (Decomposed Workflow)

To prevent implementation overload and guarantee airtight validation at every step, the v2.1 refactoring is divided into six distinct, testable phases:

| Phase | Milestone Name | Primary Deliverables | Acceptance / Exit Criteria |
| :---: | :--- | :--- | :--- |
| **Phase 6.1A** | **Literature Baseline Suite** | Implement `AutoCompPolicy`, `PeriodicCronPolicy`, and `TunedThresholdPolicy` in `policies/literature_baselines.py`. | Standalone unit test passes; policies react to mock and real metadata with correct `RUN`/`DEFER` decisions. |
| **Phase 6.1B** | **Telemetry & Data Collection Refactor** | Update `WorkloadDriver` to track `query_id`; decouple writes and compactions to sweep $[33, 150]$ files. | 15-minute dry run produces CSV with non-null `query_id` and file count growth. |
| **Phase 6.1C** | **Query-Aware Conformal Training Refactor** | Update `train_cost_benefit_models.py` with one-hot encoded `query_id` features and held-out calibration. | Model test MAE drops below 1,500ms; Model B predicts higher latency for higher file counts. |
| **Phase 6.1D** | **Agent Horizon & Action Space Refactor** | Update `run_cost_benefit_agent.py` to evaluate candidate small files, filter 0-file no-ops, and support all baselines. | Agent executes with all 4 policy flags; 0-file no-ops are recorded as `NO_OP`. |
| **Phase 6.1E** | **90-Minute Mini-Validation Pilot** | Run an end-to-end 90-minute live test on `worker3` comparing `CostBenefitPolicy` vs `AutoCompPolicy`. | Agent defers during BURST; AutoComp compacts during BURST (demonstrating the thesis); rewrites take $>5$s. |
| **Phase 6.1F** | **Multi-Trial Production Evaluation** | Execute 3 counterbalanced 4-hour evaluation cycles per condition; run Phase 2H/2I statistical tests. | Wilcoxon p-values, rank-biserial effect sizes, and Holm-Bonferroni corrections calculated for publication report. |
