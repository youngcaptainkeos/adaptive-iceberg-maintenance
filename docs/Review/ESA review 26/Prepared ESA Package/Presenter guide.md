# Presenter guide

Keep explanations concrete. State what the evidence shows before discussing what comes next.

## Slide 1 

Introduce the project and team. State that this is Phase 1 implementation progress, not a claim that the learned scheduler is complete.

## Slide 2 Outline

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 3 Abstract

Compaction merges small files. We want to find a better time to do that work while users are sending queries.

## Slide 4 Suggestions from Review 1 and Review 2

Review 1 asked us to explain the dataset. Review 2 asked to see real implementation screenshots. These are the two specific requests we address.

## Slide 5 Understanding of the Problem

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 6 Objectives and Scope

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 7 Dataset Description

Snowset decides when a request arrives. TPC-H gives the data and SQL that we execute. We are not replaying the original Snowflake queries.

## Slide 8 TPC-H Structure

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 9 Proposed Architecture

Follow the solid path first: input, queue, Spark and measured outcomes. Explain that the dashed feedback path is the proposed learned policy.

## Slide 10 Model Responsibilities

A and B predict service time under observed client maintenance states. C predicts how many requests may arrive. Rewrite cost remains a separate estimate.

## Slide 11 Available Inputs

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 12 Implementation Progress

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 13 Historical SF1 Results

The median won on the historical SF1 reserved family. This is why we keep a strong simple baseline and do not claim that ML must be better.

## Slide 14 Exploratory Model Training

The candidate training pipeline has run on real data. It is exploratory because one source family and different layouts do not establish generalization.

## Slide 15 Implementation Evidence

These are two capture sessions of four different views. Spark was idle when we photographed the services; the displayed workload results were historical.

## Slide 16 Recorded Execution · B01

This is worker3. The Java process runs Spark, the wrapper starts it with Iceberg support, and the review server displays evidence.

## Slide 17 Recorded Execution · B02

These entries are actual completed Spark jobs. Their stage and task counts show real execution, but a successful job does not mean our entire experimental audit passed.

## Slide 18 Recorded Execution · B03

The historical control completed 463 calls and retained 2,668 queued requests. The graph shows measured service times, not predictions.

## Slide 19 Recorded Execution · B04

The audit withheld acceptance. The failed control and unattempted maintenance arm remain visible rather than being hidden or relabelled.

## Slide 20 Screenshot Detail

Use this enlarged crop to point out the Spark backend, Iceberg configuration and dashboard process. It is not a training-process screenshot.

## Slide 21 SF10 Compaction Capability

In a separate capability run, compaction changed 64 files to four. It proves that file rewriting works; it does not establish a timing or query-latency gain.

## Slide 22 What Failed and What We Learned

The audit used job descriptions to recognise our work. Spark generated broadcast jobs without that description marker. Direct SQL execution links later matched all 308 rejected references to our queries. We still need a prospective repair.

## Slide 23 Applicability in Different Domains

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 24 Related Work

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 25 Phase 1 Conclusion

We can show a working foundation, saved model comparisons and a specific diagnosed blocker. A scheduling advantage remains to be tested.

## Slide 26 Next Work

Repair and validate attribution, run a fresh matched comparison, then evaluate stronger models and the policy with independent evidence.

## Slide 27 Architecture Option B

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 28 Architecture Option C

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 29 Earlier Capture · A01

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 30 Earlier Capture · A02

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 31 Earlier Capture · A03

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 32 Earlier Capture · A04

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 33 References and Evidence

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

## Slide 34 Thank You

Explain the visible content and distinguish the current implementation from the proposed or historical result. For an earlier screenshot, say explicitly that it is another capture of the same view, not another experiment.

