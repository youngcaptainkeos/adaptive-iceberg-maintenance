from policies.policy_interface import PolicyInterface

class AlwaysDeferPolicy(PolicyInterface):
    def decide(self, system_state, point_prediction, conformal_ub, tracker):
        return 'DEFER'
        
    @property
    def name(self) -> str:
        return "AlwaysDefer"
