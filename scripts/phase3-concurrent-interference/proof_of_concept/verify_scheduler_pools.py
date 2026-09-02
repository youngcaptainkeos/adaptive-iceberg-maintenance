import os
import sys
import json
import time
import subprocess
import threading

def run_beeline_query(pool_name, query_text):
    print(f"Starting beeline query for pool: {pool_name}...")
    beeline_path = "./software/spark-3.3.4/bin/beeline"
    jdbc_url = "jdbc:hive2://127.0.0.1:10000/default"
    
    # We set the pool and execute the query
    sql_cmd = f"SET spark.scheduler.pool={pool_name}; {query_text}"
    
    cmd = [
        beeline_path,
        "-u", jdbc_url,
        "-e", sql_cmd
    ]
    
    env = os.environ.copy()
    env["SPARK_LOCAL_IP"] = "127.0.0.1"
    env["SPARK_LOCAL_HOSTNAME"] = "localhost"
    
    start_time = time.time()
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    duration = time.time() - start_time
    
    if result.returncode == 0:
        print(f"Successfully completed query for pool {pool_name} in {duration:.2f}s.")
    else:
        print(f"Error in beeline query for pool {pool_name} (Exit code {result.returncode}):")
        print(result.stderr[:1000])
        
    return result.returncode == 0

def find_latest_event_log(log_dir):
    if not os.path.exists(log_dir):
        print(f"Directory {log_dir} does not exist!")
        return None
    files = os.listdir(log_dir)
    print(f"All files in {log_dir}: {files}")
    if not files:
        return None
    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)))
    return os.path.join(log_dir, latest_file)

def check_scheduler_pools(event_log_path):
    print(f"Parsing event log: {event_log_path}")
    
    # We want to check all SparkListenerJobStart events
    job_pool_mappings = []
    
    with open(event_log_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except:
                continue
            
            if event.get("Event") == "SparkListenerJobStart":
                job_id = event.get("Job ID")
                properties = event.get("Properties", {})
                
                # Check for pool configuration keys
                pool = properties.get("spark.scheduler.pool")
                thrift_pool = properties.get("spark.sql.thriftserver.pool")
                group_id = properties.get("spark.jobGroup.id")
                
                job_pool_mappings.append({
                    "job_id": job_id,
                    "group_id": group_id,
                    "pool": pool,
                    "thrift_pool": thrift_pool,
                    "all_properties": properties
                })
                
    print("\n--- Spark Job Pool Assignments Found ---")
    for mapping in job_pool_mappings:
        print(f"Job ID: {mapping['job_id']}")
        print(f"  Job Group ID: {mapping['group_id']}")
        print(f"  spark.scheduler.pool: {mapping['pool']}")
        print(f"  spark.sql.thriftserver.pool: {mapping['thrift_pool']}")
        
    # Check if we successfully propagated both pools
    pools_found = [m["pool"] for m in job_pool_mappings if m["pool"] is not None]
    
    foreground_ok = "foreground" in pools_found
    background_ok = "background" in pools_found
    
    print("\nVerification Summary:")
    print(f"  Foreground Pool Propagated: {'PASSED' if foreground_ok else 'FAILED'}")
    print(f"  Background Pool Propagated: {'PASSED' if background_ok else 'FAILED'}")
    
    return foreground_ok and background_ok

def main():
    log_dir = "/tmp/spark-events"
    
    # Query: a simple select count on nation table (very fast, doesn't lock tables)
    query_text = "SELECT count(*) FROM local.tpch.nation;"
    
    # Run the queries concurrently using threading
    t1 = threading.Thread(target=run_beeline_query, args=("foreground", query_text))
    t2 = threading.Thread(target=run_beeline_query, args=("background", query_text))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    # Wait a bit for event log writer to flush events
    time.sleep(2)
    
    latest_log = find_latest_event_log(log_dir)
    if not latest_log:
        print("Error: No Spark event log file was created!")
        sys.exit(1)
        
    success = check_scheduler_pools(latest_log)
    if success:
        print("\nSUCCESS: FAIR Scheduler pool propagation is validated!")
        sys.exit(0)
    else:
        print("\nFAILURE: Pool propagation was not verified.")
        sys.exit(1)

if __name__ == "__main__":
    main()
