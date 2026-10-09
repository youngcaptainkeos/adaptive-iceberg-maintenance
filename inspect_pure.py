import csv, glob, os

files = [
    "scripts/phase3-concurrent-interference/results/task_telemetry.csv",
    "scripts/phase3-concurrent-interference/results/query_runs.csv",
    "scripts/phase3b-predictive-signals/results/phase3b_system_metrics.csv",
    "scripts/phase3b-predictive-signals/results/phase3b_task_telemetry.csv",
    "scripts/phase3c-uncertainty-aware-scheduler/results/policy_decisions.csv",
    "scripts/phase3d-validation-generalization/results/ood_system_metrics.csv"
]

for f in files:
    if os.path.exists(f):
        print(f"=== {f} ===")
        with open(f, 'r') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader, None)
            row1 = next(reader, None)
            print("Headers:", headers)
            print("Row 1:", row1)
        print()
