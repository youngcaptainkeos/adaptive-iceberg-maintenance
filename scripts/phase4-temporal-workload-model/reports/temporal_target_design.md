# Phase 4 Temporal Target & Schema Design

## 1. Temporal Resolution ($\Delta t$)
We have evaluated 1s, 5s, 10s, 30s, and 60s resolutions. 
**Selection**: **$\Delta t = 5$ seconds**
**Justification**: Query and task lifespans in Spark often range from 2 to 15 seconds. A 1-second resolution introduces excessive noise from the OS polling jitter and Spark REST API latency. Resolutions >= 10 seconds risk 'missing' the start and end of micro-queries within a single window, severely blurring the temporal sequence. 5 seconds provides a crisp, responsive signal without the high-frequency jitter.

## 2. Forecasting Target Evaluation
The fundamental question is: *'When should Iceberg compaction be performed?'*
We evaluate the following candidate targets ($Y_{t+h}$):

### Target Y1: Future QIR / Interference over horizon $h$
- **Pros**: Direct measure of the penalty if compaction is executed. QIR isolates interference from natural workload fluctuations.
- **Cons**: Requires knowing the baseline uncontended runtime to calculate QIR.
### Target Y2: Probability future QIR exceeds SLA threshold
- **Pros**: Formulates as a standard binary classification problem.
- **Cons**: Destroys the magnitude of the violation. A 105% SLA violation is treated identically to a 400% SLA violation, limiting policy utility.
### Target Y3: Future Workload Intensity
- **Pros**: Easy to forecast from pure arrival traces.
- **Cons**: Forecasting workload intensity does not directly answer 'what is the compaction cost?'. High intensity does not automatically mean high interference if the queries are fully disjoint from the compaction dataset.
### Target Y4: Whether the next window is 'safe' for compaction
- **Pros**: Direct policy action.
- **Cons**: Circular definition. 'Safe' depends on a heuristic threshold, forcing the ML model to learn the heuristic rather than the physical reality.
### Target Y5: Future Compaction Interference Cost
- **Pros**: Quantifies total system degradation mathematically.
- **Cons**: Can be noisy if task variance is high.

## 3. Scientific Target Selection
**Selection**: **Target Y1 (Future QIR over horizon $h$)**.
**Justification**: To decide *when* to compact, the agent must weigh the *reward* (reduced future fragmentation) against the *cost* (immediate interference penalty). Y1 directly models the cost. By predicting the continuous QIR degradation over horizon $h$, a downstream policy can mathematically optimize the exact trade-off threshold.
