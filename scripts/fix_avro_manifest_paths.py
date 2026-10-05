#!/usr/bin/env python3
import os
import sys
import fastavro

OLD_PREFIX = "file:/media/shashank/Data1/PDocuments/Capstone/implementation"
NEW_PREFIX = "file:/mnt/nfs-storage/student-group-shashanksteam-workspace-group-65-pvc-a7f5bdf1-d041-4da0-b944-bb68f22df1d9/implementation"

def replace_paths_in_item(item):
    if isinstance(item, str):
        if item.startswith(OLD_PREFIX):
            return item.replace(OLD_PREFIX, NEW_PREFIX)
        return item
    elif isinstance(item, dict):
        return {k: replace_paths_in_item(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [replace_paths_in_item(x) for x in item]
    else:
        return item

def fix_avro_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            reader = fastavro.reader(f)
            schema = reader.writer_schema
            records = [replace_paths_in_item(r) for r in reader]
        
        tmp_file = filepath + ".tmp"
        with open(tmp_file, 'wb') as f:
            fastavro.writer(f, schema, records)
        
        os.replace(tmp_file, filepath)
        print(f"Successfully repaired Avro manifest: {filepath}")
        return True
    except Exception as e:
        print(f"Error repairing {filepath}: {e}")
        return False

def main():
    warehouse_dir = sys.argv[1] if len(sys.argv) > 1 else "warehouse"
    count = 0
    for root, dirs, files in os.walk(warehouse_dir):
        for f in files:
            if f.endswith(".avro"):
                p = os.path.join(root, f)
                if fix_avro_file(p):
                    count += 1
    print(f"Finished repairing {count} Avro manifest files in {warehouse_dir}.")

if __name__ == "__main__":
    main()
