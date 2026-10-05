# Pivot Topics: Lakehouse Storage Maintenance Scheduling Research

**Context:** Fallback directions if the core "learned, uncertainty-aware scheduler for *when* to
execute lakehouse compaction relative to concurrent query load" project proves infeasible at some
gate in the milestone timeline (see `unified_research_plan_single_paper.md`). Ordered from smallest
pivot (same infrastructure, adjacent question) to largest (different core contribution), so the
project can retreat gracefully at whichever gate fails.

Target venue considerations noted per pivot where they differ from the original PVLDB target.

---

## Pivot 1 — Empirical Characterization Paper
**Triggered by:** Gate 3 failure — interference signal too noisy to model above Spark's
run-to-run variance.

Drop the "learned scheduler" framing entirely. Publish the interference-measurement harness
itself (Workstream B) as the contribution: a rigorous, reproducible characterization of *when*
compaction–query interference is and isn't measurable above system noise, across compaction
size × concurrent load × time-of-day.

- **What's salvaged:** ~100% of Workstream B engineering investment (the harness, the paired
  control/treatment LST-Bench runs, the Alibaba-trace-driven load generation).
- **What's dropped:** the learned model, the uncertainty calibration, the scheduler itself.
- **Structural template:** Sarkar et al., "Constructing and Analyzing the LSM Compaction Design
  Space" (PVLDB 2021) — already identified as a related-work anchor; this pivot follows the same
  "no new system, pure characterization" paper type, which is a respected tier at PVLDB.
- **Risk profile:** Lowest risk, lowest ceiling. Still a real systems contribution — nobody has
  published a rigorous characterization of compaction/query interference under realistic
  concurrent load, so even without the ML layer this fills a documented gap (AutoComp's own
  cost model only accounts for executor memory; Smart Compaction operates on static snapshots
  with no query-load features at all).

---

## Pivot 2 — "Learning Uniformly Wins" or Honest Negative Result
**Triggered by:** Gate 5 failure — no clean, characterizable helps-vs-fails region for learned
timing across the three motivating-study workload families.

Two sub-variants depending on what the data actually shows:

- **(a) Learned timing dominates everywhere tested.** Reframe as: "when is a learned scheduler
  worth the complexity over a heuristic, full stop?" Still a legitimate practical systems
  contribution — the interesting finding becomes the magnitude and consistency of the gain
  rather than a helps/fails boundary.
- **(b) Timing barely matters relative to candidate selection.** An honest negative result
  showing AutoComp's *what*-to-compact decision dominates the *when* decision in practice.
  Less exciting but defensible if rigorously documented, especially paired with Pivot 1's
  interference characterization as supporting evidence for *why* timing turned out not to
  matter much (e.g., interference costs are small and roughly constant across time-of-day in
  the tested regime).
- **Risk profile:** Medium — requires the same infrastructure as the main plan, just a softer
  landing on the conclusion. Reviewers generally respect well-documented negative results more
  than inflated positive claims, so this is not a "failure" outcome if executed carefully.

---

## Pivot 3 — Narrow to the Uncertainty-Calibrated Interference-Cost Predictor
**Triggered by:** The end-to-end scheduler (forecaster + now/off-peak/defer decision + fallback
logic) proves too ambitious to build and evaluate well in the remaining time, but the core
interference-cost regression model (RQ1) works and calibrates cleanly.

Drop the full scheduling system. Publish a standalone paper on *predicting and calibrating*
compaction-interference cost as a signal, analogous in structure to Smart Compaction's regression
contribution (XGBoost predicting file-reduction ratio, R² = 0.998) — but with workload-interference
features as the novelty, since Smart Compaction's feature set is manifest-only and explicitly
lacks any query-load signal.

- **Title direction:** "Predicting and Calibrating Concurrent-Workload Interference Cost for
  Lakehouse Maintenance"
- **What's salvaged:** the forecaster, the labeled interference dataset (Workstream B output),
  the uncertainty-calibration methodology work.
- **What's dropped:** the scheduler's decision logic and fallback mechanism (RQ3/RQ4 as an
  end-to-end system); calibration becomes the endpoint rather than an input to a downstream
  policy.
- **Venue fit:** Closer to a strong short paper or a SIGMOD industry/experience-track piece than
  a full VLDB research paper — smaller, cleaner, more achievable within a compressed timeline.
- **Risk profile:** Low-medium. Requires the hardest part (Workstream B + forecaster) to have
  already succeeded, so this is really a scope-reduction pivot rather than a direction change.

---

## Pivot 4 — Security of Learned Components in Lakehouse Maintenance Systems
**Triggered by:** The timing project collapses entirely (e.g., both Gate 3 and Gate 5 fail, or
the VLDB reviewer-qualification issue forces a full redirect).

Route back into the security/poisoning-of-learned-components direction that was explicitly
identified during the original research-gap validation process and set aside as a future/separate
paper (see project context: "Security/poisoning of learned components in lakehouses — genuinely
novel... but set aside as the primary direction"). Concretely: study adversarial workload
injection designed to manipulate a learned compaction scheduler (yours, or a reimplementation of
the AutoComp-style MOOP ranking, or a Smart-Compaction-style utility predictor) into mistimed or
resource-exhausting maintenance decisions.

- **Why this is viable:** As lakehouse systems increasingly adopt learned components for
  maintenance decisions (AutoComp's future-work section explicitly calls for ML-based
  prediction; Smart Compaction delivers one; Databricks/Snowflake/Google Dataproc all run
  undocumented learned/heuristic triggers in production), the attack surface this creates is
  completely unexamined in the literature — nobody has studied what happens when the *inputs*
  to a compaction-timing or compaction-utility model are adversarially manipulated (e.g.,
  crafted write patterns designed to make a learned scheduler defer maintenance indefinitely,
  or trigger it at maximally disruptive times).
- **Leverages existing expertise directly:** This is a close structural cousin of the TDSC/BSS-FVS
  multi-agent security work (structural containment of compromised components), just applied to
  a new domain (lakehouse ML-driven maintenance) instead of multi-agent LLM systems.
  Directly reusable: threat-modeling methodology, containment/verification framing, empirical
  attack-simulation approach.
- **Risk profile:** Highest pivot distance (different core research question and threat model,
  not just a scope change) but near-zero ramp-up cost given existing background, and touches a
  genuinely unexplored intersection of two literatures neither of which currently talks to the
  other.

---

## Pivot 5 — Cross-Engine-Aware Timing (Joint Timing + Routing Decision)
**Triggered by:** Timing-relative-to-load proves hard to get clean signal on specifically because
"peak vs. off-peak" is a noisy, indirectly-observable scalar, but the broader "when/where should
maintenance run" question is still viable with a different decision surface.

Merge the timing question with the engine-selection framing from Strausz et al.'s cross-engine
learned cost model (LCM) paper. Instead of asking *when* to compact, ask: should compaction run
now on the query-serving engine, be deferred, or be offloaded to a dedicated
compaction engine/provisioning — and can a learned cost model decide this jointly with query
routing?

- **Why this might be easier:** Engine/provisioning choice is more directly observable and
  controllable than "peak vs. off-peak," which could make for a cleaner learning signal than the
  scalar time-choice problem. Strausz et al.'s multi-head predictor architecture (shared query
  embedding, per-engine/provisioning predictor heads, cheap fine-tuning for new engines) is a
  directly reusable structural pattern for a "per-timing-option cost head" formulation.
- **What's salvaged:** the core motivating problem (resource contention between maintenance and
  query workloads), much of the interference-measurement instinct, and gives a concrete
  structural precedent (Strausz et al.'s GNN-based plan encoder + multi-task cost heads) to build
  from rather than starting the modeling approach from scratch.
- **What changes:** the decision surface — from a scalar time-choice to a joint
  engine/provisioning/timing choice — and the primary related-work anchor shifts from
  AutoComp/PTO toward the cross-engine-optimization literature (BRAD, Strausz et al.).
- **Risk profile:** Medium — genuinely different framing, but reuses both your interference-cost
  intuition and a concrete published architecture as a starting point, rather than requiring an
  entirely new literature base or threat model (contrast with Pivot 4).

---

## Recommended Safety Nets

Given current infrastructure investment (Workstream B design, LST-Bench/Alibaba-trace tooling,
the forecaster work), **Pivot 1** and **Pivot 3** are the most realistic near-term safety nets —
both salvage the bulk of the hardest engineering work even if the full "uncertainty-aware
scheduler" doesn't come together in time for the February 2027 PVLDB cycle. Pivot 2 is a "soft
landing" available at essentially no extra cost regardless of which other pivot is chosen, since
it's a reframing of results rather than a change in what gets built. Pivots 4 and 5 are larger,
more distinct redirects to keep in reserve if the timing angle collapses more fundamentally
(e.g., before Workstream B produces usable data at all, or if the VLDB reviewer-qualification
issue forces a broader rethink).
