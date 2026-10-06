#!/usr/bin/env python3
import sys
import os

try:
    from pyhive import hive
    PYHIVE_AVAILABLE = True
except ImportError:
    PYHIVE_AVAILABLE = False

def reset_table_layout(host="127.0.0.1", port=10000, table="local.tpch_sf100.lineitem"):
    """
    Resets the Iceberg table layout back to its initial snapshot (593 small files)
    using Apache Iceberg's native snapshot management.
    """
    print(f"=== Resetting Table Layout for {table} ===")
    if not PYHIVE_AVAILABLE:
        print("PyHive not installed. Skipping live reset.")
        return False

    try:
        conn = hive.Connection(host=host, port=port, username="ccbd")
        cursor = conn.cursor()
        
        # 1. Fetch snapshot history
        cursor.execute(f"SELECT snapshot_id, committed_at FROM {table}.snapshots ORDER BY committed_at ASC")
        snapshots = cursor.fetchall()
        
        if not snapshots:
            print(f"ERROR: No snapshots found for table {table}.")
            cursor.close()
            conn.close()
            return False
            
        initial_snapshot_id = snapshots[0][0]
        print(f"Found initial snapshot ID: {initial_snapshot_id} (committed at {snapshots[0][1]})")
        
        # 2. Rollback/Set current snapshot back to initial state
        reset_sql = f"CALL local.system.set_current_snapshot(table => '{table}', snapshot_id => {initial_snapshot_id})"
        print(f"Executing: {reset_sql}")
        cursor.execute(reset_sql)
        res = cursor.fetchall()
        print(f"Reset result: {res}")
        
        # 3. Verify file count
        cursor.execute(f"SELECT count(file_path) FROM {table}.files")
        file_count = cursor.fetchall()[0][0]
        print(f"Successfully reset {table}! Active data file count: {file_count}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to reset table snapshot: {e}")
        return False

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
    reset_table_layout(host=host, port=port)
