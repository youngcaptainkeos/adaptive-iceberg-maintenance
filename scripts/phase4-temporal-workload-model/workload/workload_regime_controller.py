import random
import time

class Regime:
    def __init__(self, name, lambda_rate, min_duration, max_duration, next_states):
        self.name = name
        self.lambda_rate = lambda_rate  # Arrivals per second
        self.min_duration = min_duration # Seconds
        self.max_duration = max_duration # Seconds
        self.next_states = next_states   # List of (state_name, probability) tuples

class WorkloadRegimeController:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        
        # Define the regimes
        self.regimes = {
            "LOW": Regime("LOW", 0.01, 300, 900, [("MODERATE", 0.7), ("HIGH", 0.2), ("BURST", 0.1)]),
            "MODERATE": Regime("MODERATE", 0.05, 300, 900, [("LOW", 0.3), ("HIGH", 0.6), ("BURST", 0.1)]),
            "HIGH": Regime("HIGH", 0.15, 300, 600, [("MODERATE", 0.4), ("BURST", 0.4), ("LOW", 0.2)]),
            "BURST": Regime("BURST", 0.50, 30, 120, [("RECOVERY", 1.0)]),
            "RECOVERY": Regime("RECOVERY", 0.005, 120, 300, [("LOW", 0.8), ("MODERATE", 0.2)])
        }
        
        self.current_regime = self.regimes["LOW"]
        self.regime_end_time = 0
        
    def start(self, current_time):
        self.current_regime = self.regimes["LOW"]
        duration = self.rng.uniform(self.current_regime.min_duration, self.current_regime.max_duration)
        self.regime_end_time = current_time + duration
        
    def update_regime(self, current_time):
        if current_time >= self.regime_end_time:
            # Transition
            choices = [s for s, p in self.current_regime.next_states]
            probs = [p for s, p in self.current_regime.next_states]
            next_state_name = self.rng.choices(choices, weights=probs, k=1)[0]
            
            self.current_regime = self.regimes[next_state_name]
            duration = self.rng.uniform(self.current_regime.min_duration, self.current_regime.max_duration)
            self.regime_end_time = current_time + duration
            return True # Indicates transition occurred
        return False
        
    def get_current_rate(self):
        return self.current_regime.lambda_rate
        
    def get_current_regime_name(self):
        return self.current_regime.name
