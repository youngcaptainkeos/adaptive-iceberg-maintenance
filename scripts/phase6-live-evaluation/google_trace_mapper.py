"""Verified observed trace replay. Historical module name retained for imports."""
import numpy as np
import pandas as pd
from experiment_validation import trace_manifest, require, finite_number


class GoogleTraceMapper:
    def __init__(self, *, trace_manifest_path, test_duration_hours, start_offset_seconds=0):
        config, path, self.provenance = trace_manifest(trace_manifest_path)
        duration = finite_number(test_duration_hours, 'test_duration_hours', positive=True) * 3600
        start = finite_number(start_offset_seconds, 'start_offset_seconds')
        require(start >= 0, 'Trace start cannot be negative.')
        frame = pd.read_csv(path)
        require({'elapsed_s', 'observed_demand'} <= set(frame),
                'Derived trace must contain elapsed_s and observed_demand.')
        require(len(frame) >= 2, 'Trace needs an observed time span.')
        values = frame[['elapsed_s', 'observed_demand']].to_numpy(dtype=float)
        require(np.isfinite(values).all(), 'Trace has missing or nonfinite measurements.')
        self.times, demand = values[:, 0], values[:, 1]
        require(self.times[0] == 0 and np.all(np.diff(self.times) > 0),
                'Trace must start at zero with strictly increasing original elapsed times.')
        require(np.all(demand >= 0), 'Observed demand cannot be negative.')
        lo, hi = config['normalization_min'], config['normalization_max']
        require(np.all((demand >= lo) & (demand <= hi)), 'Trace exceeds declared normalization range.')
        require(start + duration <= self.times[-1], 'Trace does not cover the original-time run.')
        self.normalized_curve = (demand - lo) / (hi - lo)
        self.total_bins = len(self.times)
        self.duration_seconds, self.start_offset_seconds = duration, start
        self.boundaries = config['regime_boundaries']
        self.manifest = config

    def get_intensity(self, elapsed_seconds):
        elapsed_seconds = finite_number(elapsed_seconds, 'elapsed_seconds')
        require(0 <= elapsed_seconds <= self.duration_seconds, 'Time is outside the verified replay interval.')
        index = np.searchsorted(self.times, self.start_offset_seconds + elapsed_seconds, side='right') - 1
        return float(self.normalized_curve[index])

    def get_regime(self, elapsed_seconds):
        index = np.searchsorted(self.boundaries, self.get_intensity(elapsed_seconds), side='right')
        return ('LOW', 'MODERATE', 'HIGH', 'BURST')[index]
