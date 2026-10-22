"""Separately versioned controller candidate with pinned whole-call cost semantics."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
from queue_aware_maintenance.policies.policy import MaintenancePolicy
from queue_aware_maintenance.models.snapshot_simulator import choose

class SnapshotMaintenancePolicy(MaintenancePolicy):
 _choose=staticmethod(choose)
