from abc import ABC, abstractmethod

class PolicyInterface(ABC):
    """Abstract base for all scheduling policies."""
    
    @abstractmethod
    def decide(self, system_state: dict, point_prediction: float,
               conformal_ub: float, tracker) -> str:
        """
        Args:
            system_state: dict with keys like 'cpu_utilization_pct', 'compaction_active', etc.
            point_prediction: model's point estimate of future query duration (ms)
            conformal_ub: upper bound from conformal prediction (ms)
            tracker: StateTracker instance (for starvation-aware policies)
        Returns:
            'RUN' or 'DEFER'
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
