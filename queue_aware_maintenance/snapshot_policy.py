"""Separately versioned controller candidate with pinned whole-call cost semantics."""
from policy import MaintenancePolicy
from snapshot_simulator import choose

class SnapshotMaintenancePolicy(MaintenancePolicy):
 _choose=staticmethod(choose)
