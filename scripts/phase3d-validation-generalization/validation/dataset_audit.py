#!/usr/bin/env python3
import os
import sys
import csv
import math

WORKSPACE_DIR = "/home/shashank/Link to PDocuments/Capstone/implementation"
PHASE3B_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3b-predictive-signals")
PHASE3D_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase3d-validation-generalization")
RESULTS_DIR = os.path.join(PHASE3D_DIR, "results")

os.makedirs(RESULTS_DIR, exist_ok=True)

def audit():
    dataset_csv = os.path.join(PHASE3B_DIR, "results/dataset_predictive_signals.csv")
    if not os.path.exists(dataset_csv):
        print(f"Error: Dataset {dataset_csv} missing!", file=sys.stderr)
        sys.exit(1)

    with open(dataset_csv, "r") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    total_obs = len(rows)
    config_counts = {}
    workload_counts = {}
    scheduler_counts = {}
    frag_counts = {}
    missing_vals = 0
    duplicate_rows = 0
    seen_hashes = set()

    qir_vals = []
    sla_violations = []

    for r in rows:
        cfg = r["config_id"]
        config_counts[cfg] = config_counts.get(cfg, 0) + 1

        w = r["workload_type"]
        workload_counts[w] = workload_counts.get(w, 0) + 1

        s = r["scheduler_mode"]
        scheduler_counts[s] = scheduler_counts.get(s, 0) + 1

        fg = r["frag_files"]
        frag_counts[fg] = frag_counts.get(fg, 0) + 1

        # Check missing values
        for k, v in r.items():
            if v is None or v == "":
                missing_vals += 1

        # Duplicate check
        row_tuple = tuple(r.items())
        if row_tuple in seen_hashes:
            duplicate_rows += 1
        else:
            seen_hashes.add(row_tuple)

        qir_vals.append(float(r["qir_pct"]))
        sla_violations.append(int(r["sla_violation_10pct"]))

    mean_qir = sum(qir_vals) / total_obs
    s_qir = sorted(qir_vals)
    median_qir = s_qir[total_obs // 2]
    min_qir = min(qir_vals)
    max_qir = max(qir_vals)
    std_qir = math.sqrt(sum((x - mean_qir)**2 for x in qir_vals) / total_obs)

    n_sla = sum(sla_violations)
    n_non_sla = total_obs - n_sla
    sla_pct = (n_sla / total_obs) * 100.0

    print("=== Phase 3B Dataset Audit ===")
    print(f"Total Observations: {total_obs}")
    print(f"Unique Configurations: {len(config_counts)}")
    print(f"Missing Values: {missing_vals}, Duplicate Rows: {duplicate_rows}")
    print(f"QIR Distribution: Mean={mean_qir:.2f}%, Median={median_qir:.2f}%, Std={std_qir:.2f}%, Min={min_qir:.2f}%, Max={max_qir:.2f}%")
    print(f"SLA Class Balance: Class 0 (<=10% QIR)={n_non_sla} ({100.0-sla_pct:.1f}%), Class 1 (>10% QIR)={n_sla} ({sla_pct:.1f}%)")

    # Write dataset_audit.csv
    audit_csv = os.path.join(RESULTS_DIR, "dataset_audit.csv")
    with open(audit_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["total_observations", total_obs])
        writer.writerow(["unique_config_ids", len(config_counts)])
        writer.writerow(["missing_values", missing_vals])
        writer.writerow(["duplicate_rows", duplicate_rows])
        writer.writerow(["mean_qir_pct", f"{mean_qir:.4f}"])
        writer.writerow(["median_qir_pct", f"{median_qir:.4f}"])
        writer.writerow(["std_qir_pct", f"{std_qir:.4f}"])
        writer.writerow(["min_qir_pct", f"{min_qir:.4f}"])
        writer.writerow(["max_qir_pct", f"{max_qir:.4f}"])
        writer.writerow(["sla_class_0_count", n_non_sla])
        writer.writerow(["sla_class_1_count", n_sla])
        writer.writerow(["sla_violation_pct", f"{sla_pct:.2f}"])

        for cfg, cnt in config_counts.items():
            writer.writerow([f"config_obs_count_{cfg}", cnt])

    # Write dataset_audit.md
    audit_md = os.path.join(RESULTS_DIR, "dataset_audit.md")
    with open(audit_md, "w") as f:
        f.write("# Phase 3B Dataset Dynamic Audit Report\n\n")
        f.write("## 1. Summary Statistics\n")
        f.write(f"- **Total Observations**: {total_obs}\n")
        f.write(f"- **Unique Configuration Count**: {len(config_counts)}\n")
        f.write(f"- **Missing Value Count**: {missing_vals}\n")
        f.write(f"- **Duplicate Row Count**: {duplicate_rows}\n")
        f.write(f"- **QIR Distribution**: Mean = {mean_qir:.2f}%, Median = {median_qir:.2f}%, Std = {std_qir:.2f}%, Min = {min_qir:.2f}%, Max = {max_qir:.2f}%\n")
        f.write(f"- **SLA Class Balance**: Class 0 ($\\\\le 10\\\\% \\\\text{{ QIR}}$) = {n_non_sla} ({(100.0-sla_pct):.1f}%), Class 1 ($> 10\\\\% \\\\text{{ QIR}}$) = {n_sla} ({sla_pct:.1f}%)\n\n")

        f.write("## 2. Configuration Breakdown\n\n")
        f.write("| Configuration ID | Observation Count | Fragmentation Level | Workload Type | Scheduler Mode |\n")
        f.write("|------------------|-------------------|---------------------|---------------|----------------|\n")
        for cfg, cnt in config_counts.items():
            matching_row = next(r for r in rows if r["config_id"] == cfg)
            f.write(f"| `{cfg}` | {cnt} | {matching_row['frag_files']} files | `{matching_row['workload_type']}` | `{matching_row['scheduler_mode']}` |\n")

        f.write("\n## 3. Available Columns & Exact Target Names\n")
        f.write("- **Feature Columns ($X_{\\\\text{pred}}$)**: `frag_files`, `table_size_mb`, `avg_file_size_kb`, `pre_cpu_util_pct`, `pre_mem_used_pct`, `pre_disk_read_bytes_sec`, `pre_disk_write_bytes_sec`, `pre_disk_read_iops`, `pre_disk_write_iops`, `baseline_duration_ms`, `workload_type`, `scheduler_mode`, `query`\n")
        f.write("- **Target Column (Continuous QIR)**: `qir_pct`\n")
        f.write("- **Target Column (Binary SLA Violation)**: `sla_violation_10pct`\n")

    print(f"Audit artifacts written to {audit_csv} and {audit_md}")

if __name__ == "__main__":
    audit()
