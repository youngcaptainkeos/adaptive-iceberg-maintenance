class StateTracker:
    def __init__(self):
        self.consecutive_deferrals = 0
        self.total_runs = 0
        self.total_deferrals = 0
        self.forced_overrides = 0
        
    def record_decision(self, decision: str, was_forced: bool = False):
        if decision == 'RUN':
            self.consecutive_deferrals = 0
            self.total_runs += 1
            if was_forced:
                self.forced_overrides += 1
        elif decision == 'DEFER':
            self.consecutive_deferrals += 1
            self.total_deferrals += 1
            
    def should_force_run(self, max_deferrals: int) -> bool:
        return self.consecutive_deferrals >= max_deferrals
        
    def get_summary(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "total_deferrals": self.total_deferrals,
            "forced_overrides": self.forced_overrides,
            "current_consecutive_deferrals": self.consecutive_deferrals
        }
