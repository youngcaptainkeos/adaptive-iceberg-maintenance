# Phase 3B Dataset Dynamic Audit Report

## 1. Summary Statistics
- **Total Observations**: 168
- **Unique Configuration Count**: 12
- **Missing Value Count**: 0
- **Duplicate Row Count**: 0
- **QIR Distribution**: Mean = 3.64%, Median = 2.63%, Std = 6.98%, Min = -14.56%, Max = 35.05%
- **SLA Class Balance**: Class 0 ($\\le 10\\% \\text{ QIR}$) = 145 (86.3%), Class 1 ($> 10\\% \\text{ QIR}$) = 23 (13.7%)

## 2. Configuration Breakdown

| Configuration ID | Observation Count | Fragmentation Level | Workload Type | Scheduler Mode |
|------------------|-------------------|---------------------|---------------|----------------|
| `frag50_single_stream_FIFO` | 4 | 50.0 files | `single_stream` | `FIFO` |
| `frag50_multi_stream_FIFO` | 24 | 50.0 files | `multi_stream` | `FIFO` |
| `frag200_single_stream_FIFO` | 4 | 200.0 files | `single_stream` | `FIFO` |
| `frag200_multi_stream_FIFO` | 24 | 200.0 files | `multi_stream` | `FIFO` |
| `frag500_single_stream_FIFO` | 4 | 500.0 files | `single_stream` | `FIFO` |
| `frag500_multi_stream_FIFO` | 24 | 500.0 files | `multi_stream` | `FIFO` |
| `frag50_single_stream_FAIR` | 4 | 50.0 files | `single_stream` | `FAIR` |
| `frag50_multi_stream_FAIR` | 24 | 50.0 files | `multi_stream` | `FAIR` |
| `frag200_single_stream_FAIR` | 4 | 200.0 files | `single_stream` | `FAIR` |
| `frag200_multi_stream_FAIR` | 24 | 200.0 files | `multi_stream` | `FAIR` |
| `frag500_single_stream_FAIR` | 4 | 500.0 files | `single_stream` | `FAIR` |
| `frag500_multi_stream_FAIR` | 24 | 500.0 files | `multi_stream` | `FAIR` |

## 3. Available Columns & Exact Target Names
- **Feature Columns ($X_{\\text{pred}}$)**: `frag_files`, `table_size_mb`, `avg_file_size_kb`, `pre_cpu_util_pct`, `pre_mem_used_pct`, `pre_disk_read_bytes_sec`, `pre_disk_write_bytes_sec`, `pre_disk_read_iops`, `pre_disk_write_iops`, `baseline_duration_ms`, `workload_type`, `scheduler_mode`, `query`
- **Target Column (Continuous QIR)**: `qir_pct`
- **Target Column (Binary SLA Violation)**: `sla_violation_10pct`
