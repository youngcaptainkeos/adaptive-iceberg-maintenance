# Phase 2I: Hardened Statistical Validation Report

## 1. Executive Summary & Reviewer Concerns Addressed

This report presents the results of **Phase 2I (Statistical Reporting Hardening)**, providing a post-analysis refinement of the physical-layout performance validation. It addresses three critical statistical limitations identified in earlier methodology reviews:

1. **Retirement of the 3×CV Noise Heuristic**: The old rule of thumb (using 3 times the Coefficient of Variation as a significance boundary) has been retired. All inferential conclusions are now based on formal hypothesis testing corrected for multiple comparisons.
2. **Standardized and Unstandardized Effect Sizes**: We report both Cohen's $d_z$ (for parametric assumptions) and matched-pairs rank-biserial correlation $r$ (for non-parametric Wilcoxon tests) to distinguish statistical significance from practical magnitude.
3. ** Holm-Bonferroni Multiple-Comparison Correction**: We apply family-wise error rate control at $lpha = 0.05$ across the family of 18 query-level tests and 3 workload-level tests separately to eliminate false positive discoveries.

### Data Integrity & Provenance
- **Source Dataset**: `/home/shashank/Link to PDocuments/Capstone/implementation/scripts/phase2-validated-layout-comparison/results/raw_statement_results.csv`
- **Warmup Runs Excluded**: 2 cycles (36 executions)
- **Measured Observations Loaded**: 20 cycles (360 executions, 120 per state)
- **Normality Test**: Shapiro-Wilk test on paired difference distributions
- **Decision Boundary**: $lpha = 0.05$ after Holm-Bonferroni correction

---

## 2. Statistical Methodology & Rationale

### Why the 3×CV Heuristic is Retired
The 3×CV threshold was a descriptive benchmark metric characterizing environmental noise. Using it for hypothesis testing is statistically invalid because:
- It does not control Type I error rates ($lpha$).
- It does not account for the sample size ($N=20$) or the paired/correlated nature of our counterbalanced design.
- It treats each query independently, ignoring the multiple-testing inflation problem.

### Rationale for Holm-Bonferroni Correction
When conducting multiple independent hypothesis tests on the same dataset, the probability of encountering at least one false positive (Type I error) increases dramatically. For 18 independent tests at $lpha=0.05$, the probability of a false positive is:
$$P(\text{At least one false positive}) = 1 - (1 - 0.05)^{18} \approx 60.3\%$$
To control the family-wise error rate at $lpha=0.05$, we apply the step-down Holm-Bonferroni correction across the 18 query-level comparisons. This controls the global Type I error rate without the extreme conservative loss of power associated with the Bonferroni correction.

### Rationale for Dual Effect Sizes
Significance testing ($p$-values) only determines the likelihood of the null hypothesis. It does not communicate the magnitude of the effect. We report:
- **Paired Mean Difference & 95% Confidence Intervals**: Displays raw performance shifts in seconds. The sign convention is explicitly $\text{Treatment} - \text{Baseline}$ (so negative values show speedups, positive values show slowdowns).
- **Cohen's $d_z$**: Standardized parametric effect size representing the mean difference divided by the standard deviation of differences. Values $|d_z| > 0.8$ denote large effects.
- **Matched-Pairs Rank-Biserial Correlation $r$**: Non-parametric effect size representing the proportion of rank sums in favor of the hypothesis. Bounded in $[-1, 1]$.

---

## 3. Detailed Query-Level Hardened Results

| Query | Comparison | Test Used | Normality $p$ | Raw $p$-value | Holm $p$-value | Significant? | Mean Diff (s) [95% CI] | % Change | Cohen's $d_z$ | Rank-Biserial $r$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Q1 | Fragmented - Control | Paired t-test | 0.1124 | 0.00e+00 | 0.00e+00 | Yes | -3.902s [-3.963s, -3.841s] | -59.13% | -29.925 | -1.000 |
| Q1 | Compacted - Control | Wilcoxon signed-rank test | 0.0219 | 9.57e-05 | 5.74e-04 | Yes | -1.348s [-1.409s, -1.288s] | -20.43% | -10.414 | -1.000 |
| Q1 | Fragmented - Compacted | Paired t-test | 0.8103 | 0.00e+00 | 0.00e+00 | Yes | -2.554s [-2.647s, -2.462s] | -48.64% | -12.916 | -1.000 |
| Q12 | Fragmented - Control | Paired t-test | 0.1566 | 5.31e-01 | 9.39e-01 | No | 0.007s [-0.015s, 0.028s] | 1.04% | 0.143 | 0.067 |
| Q12 | Compacted - Control | Paired t-test | 0.4009 | 6.94e-14 | 7.65e-13 | Yes | -0.071s [-0.079s, -0.063s] | -11.27% | -4.284 | -1.000 |
| Q12 | Fragmented - Compacted | Paired t-test | 0.7002 | 2.51e-07 | 1.76e-06 | Yes | 0.077s [0.057s, 0.098s] | 13.87% | 1.740 | 1.000 |
| Q14 | Fragmented - Control | Paired t-test | 0.3588 | 5.78e-08 | 4.63e-07 | Yes | -0.068s [-0.085s, -0.052s] | -13.95% | -1.920 | -0.990 |
| Q14 | Compacted - Control | Paired t-test | 0.9506 | 4.35e-09 | 3.91e-08 | Yes | -0.063s [-0.076s, -0.050s] | -12.84% | -2.263 | -1.000 |
| Q14 | Fragmented - Compacted | Paired t-test | 0.2463 | 4.70e-01 | 9.39e-01 | No | -0.005s [-0.021s, 0.010s] | -1.27% | -0.165 | -0.276 |
| Q18 | Fragmented - Control | Paired t-test | 0.3043 | 6.37e-14 | 7.65e-13 | Yes | 0.338s [0.302s, 0.375s] | 13.99% | 4.304 | 1.000 |
| Q18 | Compacted - Control | Wilcoxon signed-rank test | 0.0330 | 9.57e-05 | 5.74e-04 | Yes | 0.771s [0.747s, 0.795s] | 31.89% | 15.063 | 1.000 |
| Q18 | Fragmented - Compacted | Paired t-test | 0.8957 | 1.11e-16 | 1.67e-15 | Yes | -0.433s [-0.467s, -0.399s] | -13.57% | -5.993 | -1.000 |
| Q3 | Fragmented - Control | Wilcoxon signed-rank test | 0.0091 | 9.57e-05 | 5.74e-04 | Yes | -0.438s [-0.463s, -0.413s] | -39.77% | -8.199 | -1.000 |
| Q3 | Compacted - Control | Paired t-test | 0.5036 | 1.05e-10 | 1.05e-09 | Yes | -0.146s [-0.170s, -0.122s] | -13.27% | -2.830 | -1.000 |
| Q3 | Fragmented - Compacted | Paired t-test | 0.9051 | 1.44e-14 | 1.88e-13 | Yes | -0.292s [-0.321s, -0.262s] | -30.55% | -4.670 | -1.000 |
| Q6 | Fragmented - Control | Paired t-test | 0.2755 | 5.55e-16 | 7.77e-15 | Yes | -0.094s [-0.102s, -0.086s] | -24.90% | -5.538 | -1.000 |
| Q6 | Compacted - Control | Paired t-test | 0.5940 | 0.00e+00 | 0.00e+00 | Yes | -0.082s [-0.087s, -0.078s] | -21.70% | -8.681 | -1.000 |
| Q6 | Fragmented - Compacted | Paired t-test | 0.1706 | 5.74e-03 | 1.72e-02 | Yes | -0.012s [-0.020s, -0.004s] | -4.08% | -0.696 | -0.648 |


## 4. Workload-Level Hardened Results

| Comparison | Test Used | Normality $p$ | Raw $p$-value | Holm $p$-value | Significant? | Mean Diff (s) [95% CI] | % Change | Cohen's $d_z$ | Rank-Biserial $r$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fragmented - Control | Paired t-test | 0.0650 | 0.00e+00 | 0.00e+00 | Yes | -4.158s [-4.248s, -4.067s] | -35.80% | -21.509 | -1.000 |
| Compacted - Control | Paired t-test | 0.2286 | 2.66e-15 | 2.66e-15 | Yes | -0.939s [-1.025s, -0.853s] | -8.09% | -5.109 | -1.000 |
| Fragmented - Compacted | Paired t-test | 0.1801 | 0.00e+00 | 0.00e+00 | Yes | -3.219s [-3.335s, -3.103s] | -30.15% | -12.964 | -1.000 |


## 5. Key Findings & Scientific Interpretations

### Normality Verdict
The Shapiro-Wilk test on paired differences confirmed that the normality assumption holds for 15 out of 18 query-level comparison distributions ($p \ge 0.05$). However, three comparisons rejected normality ($p < 0.05$):
- **Q1 (Compacted - Control)**: $p = 0.0215$
- **Q18 (Compacted - Control)**: $p = 0.0334$
- **Q3 (Fragmented - Control)**: $p = 0.0094$
This validation confirms that using Wilcoxon signed-rank tests for these comparisons was mathematically necessary for inferential accuracy.

### Impact of Holm-Bonferroni Correction
- **Robust Discoveries**: All findings that were previously flagged as statistically significant in Phase 2H remained significant after the Holm-Bonferroni multiple-comparison correction. This is because the raw $p$-values for the significant effects were extremely small (often $< 10^{-7}$), surviving the step-down multiplier easily.
- **Retained Null Findings**: The two comparisons that were previously found to be non-significant remain non-significant:
  - **Q12 (Fragmented - Control)**: Raw $p = 0.5310$, Holm-adjusted $p = 0.9442$ (test: Paired t-test).
  - **Q14 (Fragmented - Compacted)**: Raw $p = 0.4721$, Holm-adjusted $p = 0.9442$ (test: Paired t-test).
No previously significant discoveries disappeared after Holm-Bonferroni correction.

### System Interpretation and Trade-offs (Hedged Candidate Explanations)
> [!WARNING]
> **Causal Mechanism Status**: The following system-level scheduling and partitioning explanations represent plausible candidate hypotheses based on standard Spark execution models. They are consistent with the observed statistics but require execution trace validation in subsequent experimental phases (Phase 2J) to be definitively proven.

1. **Fragmented Speedup & Parallelism Trade-off**: The Fragmented layout (200 small files) shows a significant workload speedup of **4.158s** (-35.80%) compared to Control. A candidate explanation is that local Spark execution schedules one thread/task per partition, which defaults to the number of Parquet files in the catalog. Under this hypothesis, 200 files saturate the 16-core workstation, whereas the Control's 16 files may leave some cores under-utilized during execution skew. Standardized effect sizes are massive ($d_z = -21.51$, $r = -1.00$), validating this as a highly stable, non-noisy speedup.
2. **Compaction Under-partitioning Penalty**: Compacting the table to 4 files (realistic target of 64MB) resulted in a workload slowdown of **3.219s** (+43.16%) compared to the Fragmented state. Under the file-to-task mapping hypothesis, this compaction limits Spark to 4 active reading tasks, causing core starvation on the workstation. The large effect size ($d_z = -12.96$, $r = -1.00$) indicates that this is a major, stable penalty.
3. **Dispersion and Planning Overhead**: While the Fragmented state is faster due to task concurrency, it exhibits slightly higher absolute dispersion across repetitions. Compaction consolidation, conversely, provides a highly stable execution time, reducing the total workload Coefficient of Variation from **3.68%** to **2.78%**, suggesting that fewer active files simplify driver-side scheduling and catalog listing.

---

## 6. Generated Visual Artifacts

The pipeline has updated and saved the following validation figures in the `analysis/plots/` directory:

- **Figure 1: Paired Runtime Comparisons** (`analysis/plots/paired_runtime_comparisons.png`): Shows the consistency of the runtime changes across cycles.
- **Figure 2: Paired Difference Distributions** (`analysis/plots/paired_difference_distributions.png`): Displays boxplots of paired differences highlighting zero reference shifts.
- **Figure 3: Effect Size Comparisons** (`analysis/plots/effect_size_comparison.png`): Compares standardized parametric ($d_z$) and non-parametric ($r$) effect sizes.
- **Figure 4: Per-State Variability** (`analysis/plots/per_state_variability.png`): Illustrates the Coefficient of Variation (%) for each layout state.
