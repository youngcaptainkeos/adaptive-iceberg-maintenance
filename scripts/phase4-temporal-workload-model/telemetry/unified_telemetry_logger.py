import os
import csv
import time
import threading

class UnifiedTelemetryLogger:
    def __init__(self, base_dir, dt=5.0):
        self.dt = dt
        self.log_path = os.path.join(base_dir, "results/unified_telemetry_log.csv")
        self.running = False
        
        # We will mock the fetching in this pilot version
        self.fields = [
            "timestamp", 
            # Table State
            "num_files", "avg_file_size_mb", "total_table_size_mb", "fragmentation_level", "files_created_since_prev", "maintenance_debt", "time_since_last_compaction_s",
            # Workload State
            "query_arrival_rate_hz", "queries_started", "queries_completed", "active_queries", "queued_queries", "read_queries", "write_update_queries", "workload_intensity",
            # System State
            "cpu_utilization_pct", "memory_utilization_pct", "active_spark_tasks", "queued_spark_tasks",
            # Maintenance State
            "compaction_active", "compaction_elapsed_time_s", "files_being_compacted"
        ]
        
        # Initialize file
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.fields)

    def fetch_metrics(self):
        # In the real experiment, this makes REST calls to Spark and OS psutil
        # For the pilot dry-run, we return dummy/simulated data
        return {
            "num_files": 500,
            "avg_file_size_mb": 12.5,
            "total_table_size_mb": 6250.0,
            "fragmentation_level": 0.8,
            "files_created_since_prev": 2,
            "maintenance_debt": 40.0,
            "time_since_last_compaction_s": 120.0,
            "query_arrival_rate_hz": 0.5,
            "queries_started": 2,
            "queries_completed": 1,
            "active_queries": 4,
            "queued_queries": 0,
            "read_queries": 3,
            "write_update_queries": 1,
            "workload_intensity": 0.4,
            "cpu_utilization_pct": 45.0,
            "memory_utilization_pct": 60.0,
            "active_spark_tasks": 16,
            "queued_spark_tasks": 2,
            "compaction_active": 0,
            "compaction_elapsed_time_s": 0.0,
            "files_being_compacted": 0
        }

    def _loop(self):
        while self.running:
            start_t = time.time()
            metrics = self.fetch_metrics()
            
            row = [start_t] + [metrics.get(f, 0.0) for f in self.fields[1:]]
            
            with open(self.log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)
                
            elapsed = time.time() - start_t
            sleep_time = max(0, self.dt - elapsed)
            time.sleep(sleep_time)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop)
        self.thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()

if __name__ == "__main__":
    # Test the logger for a few cycles
    logger = UnifiedTelemetryLogger("/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model", dt=1.0)
    logger.start()
    time.sleep(3)
    logger.stop()
    print(f"Logged mock metrics to {logger.log_path}")
