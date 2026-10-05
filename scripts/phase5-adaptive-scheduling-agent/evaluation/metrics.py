class PolicyMetrics:
    def __init__(self):
        self.total_decisions = 0
        self.run_count = 0
        self.defer_count = 0
        self.forced_override_count = 0
        self.run_target_sum = 0.0
        self.sla_violations = 0
        self.max_consecutive_deferrals = 0
        self.starvation_events = 0
        self.current_deferrals = 0
        
    def record(self, decision: str, was_forced: bool, actual_target_value: float, sla_threshold: float):
        self.total_decisions += 1
        
        if decision == 'RUN':
            self.run_count += 1
            if was_forced:
                self.forced_override_count += 1
            self.run_target_sum += actual_target_value
            if actual_target_value > sla_threshold:
                self.sla_violations += 1
            
            if self.current_deferrals >= 3:
                self.starvation_events += 1
            self.current_deferrals = 0
        elif decision == 'DEFER':
            self.defer_count += 1
            self.current_deferrals += 1
            if self.current_deferrals > self.max_consecutive_deferrals:
                self.max_consecutive_deferrals = self.current_deferrals
                
    def summary(self) -> dict:
        comp_rate = (self.run_count / self.total_decisions * 100) if self.total_decisions > 0 else 0
        def_rate = (self.defer_count / self.total_decisions * 100) if self.total_decisions > 0 else 0
        force_rate = (self.forced_override_count / self.run_count * 100) if self.run_count > 0 else 0
        mean_target = (self.run_target_sum / self.run_count) if self.run_count > 0 else 0
        sla_rate = (self.sla_violations / self.run_count * 100) if self.run_count > 0 else 0
        
        return {
            "total_decisions": self.total_decisions,
            "run_count": self.run_count,
            "defer_count": self.defer_count,
            "forced_override_count": self.forced_override_count,
            "completion_rate_pct": comp_rate,
            "deferral_rate_pct": def_rate,
            "forced_override_rate_pct": force_rate,
            "mean_observed_target_on_runs": mean_target,
            "sla_violations": self.sla_violations,
            "sla_violation_rate_pct": sla_rate,
            "max_consecutive_deferrals": self.max_consecutive_deferrals,
            "starvation_events": self.starvation_events
        }
