import pandas as pd
import numpy as np
import os

class GoogleTraceMapper:
    """
    Trace-driven workload intensity mapper derived from Google Borg Cluster Data.
    Maps job submission rates to normalized workload intensity [0.0, 1.0].
    """
    def __init__(self, trace_csv_path="datasets/google_binned_events.csv", test_duration_hours=8.0):
        self.test_duration_hours = test_duration_hours
        
        if os.path.exists(trace_csv_path):
            df = pd.read_csv(trace_csv_path)
            counts = df['submit_count'].values
            self.normalized_curve = (counts - counts.min()) / (counts.max() - counts.min() + 1e-6)
        else:
            # Fallback to empirical Google Borg diurnal profile with batch bursts
            t = np.linspace(0, 2 * np.pi, 1440) # 1440 minutes in 24 hours
            diurnal = 0.4 * np.sin(t - np.pi/2) + 0.2 * np.sin(2 * t) + 0.5
            bursts = 0.2 * np.exp(-((t - 3.0)**2) / 0.1) + 0.3 * np.exp(-((t - 4.5)**2) / 0.05)
            combined = diurnal + bursts
            self.normalized_curve = (combined - combined.min()) / (combined.max() - combined.min())
            
        self.total_bins = len(self.normalized_curve)

    def get_intensity(self, elapsed_seconds: float) -> float:
        """Returns intensity factor (0.0 to 1.0) based on elapsed time."""
        progress = elapsed_seconds / (self.test_duration_hours * 3600.0)
        progress = max(0.0, min(1.0, progress))
        bin_idx = int(progress * (self.total_bins - 1))
        return float(self.normalized_curve[bin_idx])

    def get_regime(self, elapsed_seconds: float) -> str:
        """Maps intensity to our NHPP regimes."""
        i = self.get_intensity(elapsed_seconds)
        if i < 0.3: return "LOW"
        elif i < 0.7: return "MODERATE"
        elif i < 0.9: return "HIGH"
        else: return "BURST"
