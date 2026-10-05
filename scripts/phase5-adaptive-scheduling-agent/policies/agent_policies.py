import random
from policies.policy_interface import PolicyInterface
from agent.state_tracker import StateTracker

class AlwaysRunPolicy(PolicyInterface):
    def decide(self, system_state: dict, point_prediction: float, conformal_ub: float, tracker: StateTracker) -> str:
        return 'RUN'

class AlwaysDeferPolicy(PolicyInterface):
    def decide(self, system_state: dict, point_prediction: float, conformal_ub: float, tracker: StateTracker) -> str:
        return 'DEFER'

class RandomPolicy(PolicyInterface):
    def decide(self, system_state: dict, point_prediction: float, conformal_ub: float, tracker: StateTracker) -> str:
        return 'RUN' if random.random() > 0.5 else 'DEFER'

class CronPolicy(PolicyInterface):
    def __init__(self, max_deferrals: int = 3):
        self.max_deferrals = max_deferrals

    def decide(self, system_state: dict, point_prediction: float, conformal_ub: float, tracker: StateTracker) -> str:
        if tracker.consecutive_deferrals >= self.max_deferrals:
            return 'RUN'
        return 'DEFER'

class HeuristicPolicy(PolicyInterface):
    def decide(self, system_state: dict, point_prediction: float, conformal_ub: float, tracker: StateTracker) -> str:
        # Avoid running if CPU is too high or disk write is too high
        cpu = system_state.get('cpu_utilization_pct', 0.0)
        disk_write = system_state.get('disk_write_bytes_sec', 0.0)
        
        if cpu > 45.0 or disk_write > 30000000:
            return 'DEFER'
        return 'RUN'

class PointPredictionPolicy(PolicyInterface):
    def __init__(self, sla_threshold: float = 10.0):
        self.sla_threshold = sla_threshold

    def decide(self, system_state: dict, point_prediction: float, conformal_ub: float, tracker: StateTracker) -> str:
        if point_prediction <= self.sla_threshold:
            return 'RUN'
        return 'DEFER'

class ConformalRiskPolicy(PolicyInterface):
    def __init__(self, sla_threshold: float = 10.0):
        self.sla_threshold = sla_threshold

    def decide(self, system_state: dict, point_prediction: float, conformal_ub: float, tracker: StateTracker) -> str:
        if conformal_ub <= self.sla_threshold:
            return 'RUN'
        return 'DEFER'

class TemporalConformalPolicy(PolicyInterface):
    def __init__(self, sla_threshold: float = 10.0):
        self.sla_threshold = sla_threshold

    def decide(self, system_state: dict, point_prediction: float, conformal_ub: float, tracker: StateTracker) -> str:
        # Same as ConformalRiskPolicy, but explicitly designed to operate on temporal sequences
        if conformal_ub <= self.sla_threshold:
            return 'RUN'
        return 'DEFER'
