# Audit 3: Target Definition Decision

## Objective
Determine which definition of Future QIR best answers the policy question: *'Will compaction initiated now interfere with the upcoming workload?'*

## Candidate Evaluation
### 1. Point QIR at t+h
- **Representativeness**: Low
- **Noise Susceptibility**: High
- **Verdict**: Rejected (Ignores interval cost)

### 2. Mean QIR over [t, t+h]
- **Representativeness**: High
- **Noise Susceptibility**: Low
- **Verdict**: SELECTED (Captures total degradation)

### 3. Max QIR over [t, t+h]
- **Representativeness**: Moderate
- **Noise Susceptibility**: High
- **Verdict**: Rejected (Over-penalizes brief anomalies)

### 4. 95th Percentile QIR
- **Representativeness**: Moderate
- **Noise Susceptibility**: Moderate
- **Verdict**: Rejected (Too conservative for proactive thresholding)

### 5. SLA Violation Indicator
- **Representativeness**: Low
- **Noise Susceptibility**: Low
- **Verdict**: Rejected (Binary loss destroys magnitude gradients)

## Scientific Conclusion
We formally select **Option 2: Mean QIR over [t, t+h]**. Compaction is a long-running process (often spanning minutes). Point metrics or maxima fail to capture the integral of the degradation penalty across the entire compaction window. The Mean QIR directly correlates to total latency cost, providing a continuous loss surface for the model to learn from.
