"""Unvalidated configurable baseline prototypes; no faithful AutoComp reproduction.

No evaluator currently invokes these helpers. Parameters must come from a declared
paper scenario or training-only protocol. Missing measurements never become zeros.
Historical defaults/citation claims are retained in Git history, not active code.
"""
import math
from numbers import Integral
from typing import Dict, Any


def measured_counts(metadata):
    small,total=metadata['candidate_small_files'],metadata['frag_file_count']
    if any(not isinstance(x,Integral) or isinstance(x,bool) for x in (small,total)) or not 0<=small<=total:
        raise ValueError('Require measured nonnegative integer small/total file counts')
    return int(small),int(total)


def positive_parameter(value,name):
    if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<=0:
        raise ValueError('Declare positive finite '+name)
    return float(value)


class BaselinePolicyInterface:
    def decide(self, table_metadata: Dict[str, Any], *, elapsed_s: float) -> str:
        raise NotImplementedError


class AutoCompPolicy(BaselinePolicyInterface):
    """Retired misattribution; use a separately named threshold prototype."""
    def __init__(self, **kwargs):
        raise ValueError('Faithful AutoComp is not implemented. Historical ratio/count heuristic must not be presented as its reproduction.')


class SmallFileThresholdPolicy(BaselinePolicyInterface):
    """Configured ratio/count candidate-action heuristic, not estimated file reduction."""
    def __init__(self, *, small_file_ratio_threshold, min_candidate_files):
        self.ratio=positive_parameter(small_file_ratio_threshold,'small-file ratio')
        if self.ratio>1 or not isinstance(min_candidate_files,Integral) or isinstance(min_candidate_files,bool) or min_candidate_files<=0:
            raise ValueError('Declare ratio in (0,1] and positive measured-count threshold')
        self.minimum=int(min_candidate_files)

    def decide(self, table_metadata, *, elapsed_s):
        small,total=measured_counts(table_metadata)
        if total==0: return 'DEFER'
        return 'RUN' if small>=self.minimum or small/total>=self.ratio else 'DEFER'


class PeriodicCronPolicy(BaselinePolicyInterface):
    """Configured periodic candidate action; executor separately verifies real work."""
    def __init__(self, *, interval_minutes):
        self.interval_seconds=positive_parameter(interval_minutes,'period')*60  # Unit conversion.
        self.last_run_seconds=0.0  # Elapsed experiment origin, not an invented observation.
        self.last_seen_seconds=0.0

    def decide(self, table_metadata, *, elapsed_s):
        measured_counts(table_metadata)
        if not isinstance(elapsed_s,(int,float)) or isinstance(elapsed_s,bool) or not math.isfinite(elapsed_s) or elapsed_s<self.last_seen_seconds:
            raise ValueError('Use actual finite nondecreasing elapsed experiment time')
        self.last_seen_seconds=elapsed_s
        if elapsed_s-self.last_run_seconds>=self.interval_seconds:
            self.last_run_seconds=elapsed_s
            return 'RUN'
        return 'DEFER'


class TunedThresholdPolicy(BaselinePolicyInterface):
    """Explicit small-file count threshold; tuned status requires external evidence."""
    def __init__(self, *, frag_threshold):
        if not isinstance(frag_threshold,Integral) or isinstance(frag_threshold,bool) or frag_threshold<=0:
            raise ValueError('Declare positive count threshold from protocol')
        self.threshold=int(frag_threshold)

    def decide(self, table_metadata, *, elapsed_s):
        small,_=measured_counts(table_metadata)
        return 'RUN' if small>=self.threshold else 'DEFER'
