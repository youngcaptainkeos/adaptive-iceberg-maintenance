from policies.policy_interface import PolicyInterface

class SOTAThresholdPolicy(PolicyInterface):
    """
    Mimics industry-standard Databricks Auto-Optimize / Iceberg maintenance.
    Triggers compaction solely based on table fragmentation, ignoring concurrent workload.
    """
    def __init__(self, frag_file_threshold=200, min_file_size_mb=16.0):
        self.frag_file_threshold = frag_file_threshold
        self.min_file_size_mb = min_file_size_mb
        
    def decide(self, system_state: dict, point_prediction: float, conformal_ub: float, tracker) -> str:
        frag_files = system_state.get('frag_file_count', 0)
        table_size = system_state.get('table_size_mb', 1)
        avg_size = table_size / max(frag_files, 1)
        
        if frag_files >= self.frag_file_threshold or avg_size < self.min_file_size_mb:
            return 'RUN'
        return 'DEFER'

    @property
    def name(self) -> str:
        return "SOTAThresholdPolicy"
