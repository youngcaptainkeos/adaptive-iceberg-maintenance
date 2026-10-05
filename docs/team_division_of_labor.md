# Team Division of Labor (v2 — clarified)
## Learned, Uncertainty-Aware Scheduling for Lakehouse Storage Maintenance

**How this is split:** four people, four ownership areas, each mapped directly onto one
piece of the project's actual research claim. No one is assigned to "write the paper" —
writing happens naturally once each person has real results to report. Each section
below states, up front, **why this piece matters to the whole project**, not just what
tasks to run.

**Difficulty ranking (hardest → easiest), stated openly so the split is honest:**
1. **You (Shashank) — Uncertainty & Calibration.** Hardest and most important. If this
   is wrong, the project's central claim doesn't hold, no matter how good everything
   else is.
2. **Person 2 — Out-of-Distribution Stress Test.** Second hardest — real experimental
   design judgment required, but mechanically simpler than Track 1.
3. **Person 3 — Evaluation & Baselines.** Substantial, well-defined, mostly
   implementation once designed.
4. **Person 4 — Policy Logic & Fairness Checks.** Most mechanical and most bounded —
   good fit for whoever has the least bandwidth or is newest to the stats-heavy parts.

---

## YOU — Track 1: Uncertainty & Calibration
### This is the piece the entire paper's title depends on.

**The one-sentence goal:** prove — or disprove — that the model actually knows when it
doesn't know, and can safely hand control back to a heuristic when it doesn't.

**Why this is the most critical piece, in plain terms:** the project isn't called
"a model that predicts compaction interference." It's called *uncertainty-aware
scheduling*. Every other track's work is in service of feeding data into this piece or
using its output. If this piece fails, the project quietly becomes "we built AutoComp's
MOOP ranking but with a Random Forest instead of hand-tuned weights" — which is not
novel and does not defend against a VLDB/SIGMOD reviewer who's read the literature
survey you already built. This is also the one piece nobody else on the team can safely
own for you, because it requires judgment calls (is this calibrated? is this
overclaiming?) that need to be made by the person accountable for the paper's central
claim.

**What you own:**
1. **Calibration check on the existing q=0.95 quantile model.** Does its predicted upper
   bound actually contain the true interference value ~95% of the time on data it wasn't
   trained on? Right now nobody has checked this — it's an assumption, not a verified
   fact. You check it.
2. **Build the real calibration mechanism.** If the raw quantile model doesn't hold up
   (likely), implement conformal prediction around the existing regressor — this gives a
   distribution-free calibration guarantee regardless of which underlying model is used,
   which is the more defensible and more publishable approach.
3. **Define the actual fallback rule.** At what confidence level does the scheduler stop
   trusting the model and default to a safe heuristic? This threshold, and the
   justification for it, is a decision only you should make, because it's the one number
   in the whole paper that directly encodes the project's safety claim.
4. **Judge the final result.** Once Person 2's out-of-distribution data comes back
   (Track 2), you decide whether the uncertainty mechanism correctly flagged low
   confidence on unfamiliar configurations. This is the single most important test in
   the entire project — you are the one who reads that result and calls it a pass or
   fail.

**What you consume from others:** Track 2's out-of-distribution dataset (to test
calibration against genuinely new data, not just held-out folds of familiar data).
**What you hand off:** the calibrated model / conformal wrapper + fallback threshold,
which Track 4 wires into the actual scheduling policies.

---

## Person 2 — Track 2: Out-of-Distribution Stress Test
### This is the experiment that decides whether Track 1's answer means anything.

**The one-sentence goal:** find out what happens when the model faces a situation it has
never seen, because that's the only real test of "uncertainty-aware."

**Why this matters:** right now the model has only ever been evaluated on
configurations it was trained near (12 configurations, cross-validated among
themselves). That tells you the model can interpolate. It tells you nothing about
whether it can recognize when it's *extrapolating* — and recognizing that is the entire
point of the uncertainty layer. Without this track's data, Track 1's calibration check
is only testing itself against familiar territory, which is close to a tautology. This
is the second-hardest job because it requires real judgment: choosing configurations
that are genuinely novel (not just a slightly different random seed) without being so
extreme they're unrealistic.

**What you own:**
1. Design 2–3 new experimental configurations outside the original grid (currently:
   3 fragmentation levels × 2 workload intensities × 2 scheduler modes). Pick points
   that are realistically plausible in production but meaningfully outside what's
   already been tested — e.g., a fragmentation level well outside {50, 200, 500} files,
   or a workload mix the model has never encountered.
2. Run these through the existing Phase 3A/3B experimental harness (already built —
   you're reusing infrastructure, not building new).
3. Package the results in the same format as the existing Phase 3B dataset so Track 1
   can drop it straight into the calibration check.

**What you consume from others:** nothing blocking — the harness already exists from
Phase 3A/3B.
**What you hand off:** the out-of-distribution dataset, directly to Track 1 (this is the
one hard dependency in the whole plan — Track 1 cannot finish its most important
deliverable without this).

---

## Person 3 — Track 3: Evaluation & Baselines
### This is what makes the comparison believable instead of just impressive-looking.

**The one-sentence goal:** build the evaluation scaffolding that proves any claimed
improvement is real, not a statistical accident or a comparison against a strawman.

**Why this matters:** right now there's a Random Forest achieving 5.38% MAE and nobody
knows if that's actually good, because there's no baseline to compare it against, no
per-fold breakdown showing where it fails, and no proof the model isn't just overfitting
to only 12 configurations. A reviewer's very first question will be "compared to what?"
— this track exists to make sure there's always a good answer.

**What you own:**
1. **Leave-one-configuration-out cross-validation harness.** Instead of one pooled
   accuracy number, build the evaluation so each of the 12 configurations gets held out
   one at a time, and results are reported per-fold. This shows exactly where the model
   struggles, not just an average that could be hiding a failure.
2. **Two missing baseline comparisons:** a simple fixed-threshold rule using raw sensor
   data (no ML at all — this is your "would a dumb rule already solve this" check), and
   a random coin-flip policy (your absolute floor — if the model doesn't beat this by a
   wide, clearly real margin, something is wrong).
3. **A trivial baseline for the regression itself** — what MAE do you get by just always
   guessing the average interference value? This tells everyone whether 5.38% is
   actually impressive.
4. **Diagnose the broken classifier.** The existing SLA-violation classifier performs
   almost randomly (AUC 0.531). Figure out why — check for class imbalance, look at the
   confusion matrix — and write up what you find, whether that's "it's genuinely
   unpredictable" or "here's the fix."

**What you consume from others:** the existing Phase 3B dataset — available now.
**What you hand off:** the evaluation harness + baselines, to Person 4, who plugs actual
scheduling policies into it.

---

## Person 4 — Track 4: Policy Logic & Fairness Checks
### This is where all the other tracks' work gets assembled into an actual scheduler.

**The one-sentence goal:** build the actual RUN / DEFER decision logic, and make sure
it's not secretly cheating.

**Why this matters, and why this is the right track for the lightest workload:** this
is largely assembly work once Tracks 1–3 deliver their pieces — the hard thinking
(what's calibrated uncertainty, what's a fair test, what's a good baseline) has already
been done by the other three tracks. What's left is careful, bounded implementation:
writing the actual if/else decision rules, and running one specific sanity check to make
sure nothing is secretly broken.

**What you own:**
1. **Implement the five scheduling policies:** Always-Run, Always-Defer, a simple
   resource-threshold rule, the model-based policy (using Track 1's calibrated
   predictions), and the conservative/cautious policy (using Track 1's uncertainty
   bound).
2. **The "is this cheating?" check.** Because the broken classifier (Track 3 is
   diagnosing it) and the working regression model are both feeding into similar
   decisions, verify explicitly that any policy's good performance is coming from the
   real, working part of the model — not accidentally leaning on the broken classifier
   without anyone noticing. This is a quick, specific test, not open-ended debugging.
3. **Quantify the tradeoff nobody's measured yet:** does deferring maintenance to avoid
   interference cause maintenance to never actually happen? Track how often each policy
   actually lets maintenance run, not just how much interference it avoids — a policy
   that "wins" by never doing maintenance at all is not a real answer.
4. **Run the final comparison** once Track 1 (calibration), Track 2 (stress-test data),
   and Track 3 (evaluation harness + baselines) have all delivered — this is the last
   step, where everything comes together into the actual result table.

**What you consume from others:** Track 1's calibrated model, Track 2's stress-test
data, Track 3's evaluation harness and baselines — this track is the last domino, and
that's intentional.
**What you hand off:** the final policy comparison results — the actual headline table
for the paper.

---

## How the four pieces fit together (the whole picture)

```
Track 2 (stress test) ──────────────┐
                                     ▼
Track 1 (YOU — calibration) ───► "is the model honest about what it doesn't know?"
                                     │
                                     ▼
Track 4 (policies) ◄──── Track 3 (evaluation + baselines)
                                     │
                                     ▼
                       final result: does a calibrated,
                       uncertainty-aware scheduler beat
                       the honest baselines, safely?
```

Track 1 (you) sits at the center because it's the only piece that directly answers the
project's actual question. Track 2 exists to give you something real to test against.
Tracks 3 and 4 exist to make sure that whatever answer you get is presented in a way a
skeptical reviewer can't poke a hole in.

---

## Practical Notes

- **Tracks 2 and 3 can start immediately, in parallel, with zero coordination needed.**
  Track 2 needs the live experimental environment; Track 3 works entirely from existing
  exported data and needs nothing from anyone.
- **Track 1 (you) can start the calibration-check work on existing data immediately**,
  but your final judgment call has to wait for Track 2's data to land — budget your time
  accordingly, and use the wait productively on the conformal-prediction implementation.
- **Track 4 is intentionally the last piece to fully activate** — have that person help
  with implementation support on Tracks 2/3 early on if they finish policy scaffolding
  before the others are ready to hand off.
- If someone needs to be swapped between tracks later, swap into Track 4 first and
  Track 1 last — Track 1 carries the most context and the most consequential judgment
  calls, so continuity matters most there.

---

## Cross-Referencing Note

Track 1 = open item 13 (quantile calibration). Track 2 = open item 12
(out-of-distribution test). Track 3 = open items 14, 15, 16, 18 (LOCO-CV, baselines,
trivial-baseline comparison, SLA classifier diagnosis). Track 4 = open items 17 and the
circularity ablation (Section 7.5's flagged risk). All correspond exactly to the
numbered list in `methodology_working_doc.md` Section 10 — update that doc's entries as
each track completes its piece, so the whole team has one source of truth.
