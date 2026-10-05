from policies.policy_interface import PolicyInterface

class ConformalRiskPolicy(PolicyInterface):
    def __init__(self, sla_threshold: float, max_consecutive_deferrals: int = 3):
        self.sla_threshold = sla_threshold
        
    def decide(self, system_state, point_prediction, conformal_ub, tracker):
        if conformal_ub <= self.sla_threshold:
            return 'RUN'
        return 'DEFER'
        
    @property
    def name(self) -> str:
        return "ConformalRisk"
