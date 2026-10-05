from policies.policy_interface import PolicyInterface

class CronPolicy(PolicyInterface):
    def __init__(self, run_every: int = 3):
        self.run_every = run_every
        self.calls = 0
        
    def decide(self, system_state, point_prediction, conformal_ub, tracker):
        self.calls += 1
        if self.calls % self.run_every == 0:
            return 'RUN'
        return 'DEFER'
        
    @property
    def name(self) -> str:
        return "Cron"
