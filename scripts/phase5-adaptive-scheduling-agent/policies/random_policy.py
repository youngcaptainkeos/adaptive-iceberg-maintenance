import random
from policies.policy_interface import PolicyInterface

class RandomPolicy(PolicyInterface):
    def decide(self, system_state, point_prediction, conformal_ub, tracker):
        return 'RUN' if random.random() > 0.5 else 'DEFER'
        
    @property
    def name(self) -> str:
        return "Random"
