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
