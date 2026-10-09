import pandas as pd
import glob
import os

files_to_check = [
    "scripts/phase3-concurrent-interference/results/task_telemetry.csv",
    "scripts/phase3b-predictive-signals/results/phase3b_task_telemetry.csv",
    "scripts/phase3b-predictive-signals/results/phase3b_system_metrics.csv",
    "scripts/phase3-concurrent-interference/results/telemetry_extracted.csv",
    "scripts/phase3c-uncertainty-aware-scheduler/results/policy_decisions.csv",
    "cab/benchmark-results/snowflake_shared_1h_2s_1tb/query_telemetry.csv", # if it exists
]

for f in files_to_check:
    if os.path.exists(f):
        print(f"=== {f} ===")
        try:
            df = pd.read_csv(f, nrows=5)
            print("Columns:", df.columns.tolist())
            print(df.head(2))
        except Exception as e:
            print("Error:", e)
        print("\n")
