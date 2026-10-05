# Research Plan & Workflow

## Autonomous Multi-Agent Pipeline
The following strictly ordered lifecycle ensures rigorous research validation:

`RESEARCH QUESTION` 
$\rightarrow$ `RESEARCH DIRECTOR` 
$\rightarrow$ `EXPERIMENT DESIGN` 
$\rightarrow$ `IMPLEMENTATION SPECIFICATION` 
$\rightarrow$ `IMPLEMENTATION ENGINEER` 
$\rightarrow$ `TESTING` 
$\rightarrow$ `EXPERIMENT EXECUTION` 
$\rightarrow$ `INDEPENDENT VERIFICATION (REVIEWER & AUDITOR)` 
$\rightarrow$ `EXPERIMENT ANALYST` 
$\rightarrow$ `RESEARCH DIRECTOR` 
$\rightarrow$ `NEXT EXPERIMENT`

## Agent Hierarchy & Roles
1. **Research Director** (Opus -> Sonnet -> Gemini Pro)
   - Orchestrates the workflow. Synthesizes findings. Evaluates conflicting recommendations (e.g., continuous workload trace audit) against the primary research methodology and available evidence. Escalates major methodological conflicts to the human.
2. **Research/Experiment Designer** (Sonnet -> Gemini Pro -> Flash)
   - Converts objectives into precise specs. Finalizes OOD configurations, rationale, seeds, metrics, acceptance criteria, and evaluation procedures before execution.
3. **Implementation Engineer** (Gemini Pro -> Flash)
   - Implements approved experiments, modifies code, runs tests, and executes experiments based strictly on the Designer's spec.
4. **Research Reviewer** (Sonnet -> Gemini Pro -> Flash)
   - Independently reviews methodology and implementations. Identifies bugs, data leakage, and statistical problems.
5. **Experiment Analyst** (Gemini Pro -> Flash)
   - Processes outputs, calculates metrics, generates analysis and figures.
6. **Reproducibility Auditor** (GPT-OSS -> Gemini Pro)
   - Independently verifies reproducibility of all reported results (seeds, configs, Git commits, datasets). If Gemini Pro is used as a fallback, explicitly records reduced model-family independence.

## Communication Protocol
- All agent communication flows through the Research Director (Parent).
- The Reviewer and Auditor operate completely independently and must not see each other's conclusions before submitting.

## Human Approval Gates
The Research Director must pause and request human approval before:
1. Executing an experiment.
2. Changing the research question or methodology.
3. Accepting surprising findings.
4. Deleting datasets or experiments.
5. Finalizing paper claims.
