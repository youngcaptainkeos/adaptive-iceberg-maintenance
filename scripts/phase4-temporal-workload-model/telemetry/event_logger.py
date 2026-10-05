import os
import csv
import time

class EventLogger:
    def __init__(self, base_dir):
        self.log_path = os.path.join(base_dir, "results/event_log.csv")
        self.fields = ["timestamp", "event_type", "event_id", "details"]
        
        # Initialize file
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.fields)

    def log_event(self, event_type, event_id, details=""):
        timestamp = time.time()
        row = [timestamp, event_type, event_id, details]
        with open(self.log_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)

if __name__ == "__main__":
    logger = EventLogger("/media/shashank/Data1/PDocuments/Capstone/implementation/scripts/phase4-temporal-workload-model")
    logger.log_event("QUERY_START", "Q1", "READ")
    logger.log_event("COMPACTION_START", "C1", "Targeting 100 files")
    print(f"Logged mock events to {logger.log_path}")
