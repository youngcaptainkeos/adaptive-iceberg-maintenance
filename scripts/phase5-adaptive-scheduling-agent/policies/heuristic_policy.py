from policies.policy_interface import PolicyInterface

class HeuristicPolicy(PolicyInterface):
    def __init__(self, cpu_threshold: float, jobs_threshold: float):
        self.cpu_threshold = cpu_threshold
        self.jobs_threshold = jobs_threshold
        
    def decide(self, system_state, point_prediction, conformal_ub, tracker):
        cpu = float(system_state.get('cpu_utilization_pct', 0.0))
        active_jobs = int(system_state.get('active_spark_jobs', 0))
        
        if cpu > self.cpu_threshold or active_jobs > self.jobs_threshold:
            return 'DEFER'
        return 'RUN'
        
    @property
    def name(self) -> str:
        return "Heuristic"
