# Technical Architecture
## Components
- **Workload Execution:** LST-Bench → JDBC → Spark Thrift Server → Spark 3.3.4 → Iceberg 1.4.3
- **Telemetry:** DuckDB sink.
- **Physical layout:** TPC-H loaded locally.
- **State:** TPC-H SF1 baseline with 16 files (~9.08 MB avg).

## Autonomous Agent Architecture
- **Framework:** Antigravity `invoke_subagent`
- **Orchestration:** Centralized through the Research Director (Parent).
- **Communication:** Parent-Subagent model. Subagents do not communicate directly.
- **Review:** Independent, parallel verification by the Research Reviewer and Reproducibility Auditor.
