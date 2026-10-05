from policies.policy_interface import PolicyInterface

class AlwaysRunPolicy(PolicyInterface):
    def decide(self, system_state, point_prediction, conformal_ub, tracker):
        return 'RUN'
        
    @property
    def name(self) -> str:
        return "AlwaysRun"
