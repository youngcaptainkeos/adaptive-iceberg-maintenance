import os
import sys
import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler

import os
WORKSPACE_DIR = os.environ.get("REPO_DIR", "/media/shashank/Data1/PDocuments/Capstone/implementation")
PHASE5_DIR = os.path.join(WORKSPACE_DIR, "scripts/phase5-adaptive-scheduling-agent")
sys.path.append(PHASE5_DIR)

from agent.state_tracker import StateTracker
from agent.conformal_predictor import ConformalPredictor
from evaluation.metrics import PolicyMetrics

from policies.always_run import AlwaysRunPolicy
from policies.always_defer import AlwaysDeferPolicy
from policies.random_policy import RandomPolicy
from policies.cron_policy import CronPolicy
from policies.heuristic_policy import HeuristicPolicy
from policies.point_prediction_policy import PointPredictionPolicy
from policies.conformal_risk_policy import ConformalRiskPolicy
from policies.temporal_conformal_policy import TemporalConformalPolicy

def main():
    config_path = os.path.join(PHASE5_DIR, "config/agent_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    sla_threshold_percentile = config.get("sla_threshold_percentile", 90)
    risk_budget = config.get("risk_budget_alpha", 0.05)
    max_deferrals = config.get("max_consecutive_deferrals", 3)

    data_path = os.path.join(WORKSPACE_DIR, "scripts/phase4-temporal-workload-model/results/temporal_windows.csv")
    df = pd.read_csv(data_path)

    temporal_features = [
        'cpu_utilization_pct', 'memory_used_pct', 
        'disk_read_iops', 'disk_write_iops',
        'active_spark_jobs', 'compaction_active',
        'cpu_utilization_pct_mean_60s', 'cpu_utilization_pct_std_60s',
        'memory_used_pct_mean_60s', 'memory_used_pct_std_60s',
        'disk_read_iops_mean_60s', 'disk_read_iops_std_60s',
        'disk_write_iops_mean_60s', 'disk_write_iops_std_60s'
    ]
    target = 'target_avg_query_duration_300s'

    train_df = df[df['split'] == 'train']
    val_df = df[df['split'] == 'val']
    test_df = df[df['split'] == 'test']

    # Compute data-driven SLA threshold
    sla_threshold = float(np.percentile(train_df[target], sla_threshold_percentile))
    print(f"Data-driven SLA threshold ({sla_threshold_percentile}th percentile of train targets): {sla_threshold:.2f} ms")

    # Compute data-driven Heuristic thresholds
    cpu_p75 = float(np.percentile(train_df['cpu_utilization_pct'], 75))
    jobs_p75 = float(np.percentile(train_df['active_spark_jobs'], 75))
    print(f"Heuristic thresholds: CPU > {cpu_p75:.1f}%, ActiveJobs > {jobs_p75:.1f}")

    scaler = StandardScaler()
    X_train = scaler.fit_transform(train_df[temporal_features].fillna(0))
    y_train = train_df[target].values

    model = RidgeCV(alphas=np.logspace(-3, 3, 100))
    model.fit(X_train, y_train)

    X_val = scaler.transform(val_df[temporal_features].fillna(0))
    y_val = val_df[target].values
    
    predictor = ConformalPredictor(model, alpha=risk_budget)
    q_hat = predictor.calibrate(X_val, y_val)
    print(f"Computed Conformal q_hat: {q_hat:.2f} ms")

    policies = [
        AlwaysRunPolicy(),
        AlwaysDeferPolicy(),
        RandomPolicy(),
        CronPolicy(run_every=3),
        HeuristicPolicy(cpu_threshold=cpu_p75, jobs_threshold=jobs_p75),
        PointPredictionPolicy(sla_threshold, max_deferrals),
        ConformalRiskPolicy(sla_threshold, max_deferrals),
        TemporalConformalPolicy(sla_threshold, max_deferrals)
    ]

    trackers = {p.name: StateTracker() for p in policies}
    metrics = {p.name: PolicyMetrics() for p in policies}

    X_test = scaler.transform(test_df[temporal_features].fillna(0))
    y_test = test_df[target].values

    for idx, (index, row) in enumerate(test_df.iterrows()):
        state = row.to_dict()
        X_row = X_test[idx].reshape(1, -1)
        point, ub, _ = predictor.predict_with_bounds(X_row)
        point = point[0]
        ub = ub[0]
        
        actual_val = y_test[idx]

        for policy in policies:
            tracker = trackers[policy.name]
            metric = metrics[policy.name]
            
            was_forced = False
            # Check if this policy forces runs based on state tracker (TemporalConformalPolicy explicitly handles it in decide(), 
            # but we need to track if it WAS forced. For simplicity, we can check if it would have been forced before calling)
            if tracker.should_force_run(max_deferrals) and policy.name == "TemporalConformal":
                was_forced = True
                
            decision = policy.decide(state, point, ub, tracker)
            tracker.record_decision(decision, was_forced)
            metric.record(decision, was_forced, actual_val, sla_threshold)

    results = []
    for policy in policies:
        summary = metrics[policy.name].summary()
        summary['Policy'] = policy.name
        results.append(summary)

    results_df = pd.DataFrame(results)
    # Reorder columns
    cols = ['Policy', 'completion_rate_pct', 'sla_violation_rate_pct', 'mean_observed_target_on_runs', 
            'deferral_rate_pct', 'forced_override_rate_pct', 'starvation_events']
    results_df = results_df[[c for c in cols if c in results_df.columns]]

    print("\nOffline Evaluation Summary:")
    print(results_df.to_string(index=False))

    results_path = os.path.join(PHASE5_DIR, "results/offline_policy_evaluation.csv")
    results_df.to_csv(results_path, index=False)

    # Plot Comparison
    plt.figure(figsize=(12, 6))
    plot_df = results_df.melt(id_vars='Policy', value_vars=['completion_rate_pct', 'sla_violation_rate_pct'],
                              var_name='Metric', value_name='Percentage')
    sns.barplot(data=plot_df, x='Policy', y='Percentage', hue='Metric')
    plt.title("Phase 5: Offline Policy Evaluation — 4-Hour Temporal Dataset")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(PHASE5_DIR, "results/policy_comparison.svg"))
    plt.close()

    # Plot Pareto
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=results_df, x='completion_rate_pct', y='sla_violation_rate_pct', s=100)
    for i, row in results_df.iterrows():
        plt.text(row['completion_rate_pct'] + 1, row['sla_violation_rate_pct'], row['Policy'])
    plt.title("Phase 5: Pareto Frontier")
    plt.xlabel("Completion Rate (%)")
    plt.ylabel("SLA Violation Rate (%)")
    plt.tight_layout()
    plt.savefig(os.path.join(PHASE5_DIR, "results/pareto_frontier.svg"))
    plt.close()

if __name__ == "__main__":
    main()
