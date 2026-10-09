import sys
import subprocess
import time
sys.path.append('scripts/phase3b-predictive-signals/runner')
from run_phase3b_experiment import start_thrift_server, stop_thrift_server, get_spark_env

def run():
    print("Starting thrift server...")
    start_thrift_server('FIFO')
    
    print("Running beeline query...")
    beeline_cmd = [
        "beeline",
        "-u", "jdbc:hive2://127.0.0.1:10000/default",
        "-n", "anonymous",
        "-p", "",
        "-e", "SELECT COUNT(*) FROM local.tpch.lineitem"
    ]
    env = get_spark_env()
    
    # Bypass sandbox network issue by adding localhost resolution to /etc/hosts if it fails, or it might just work if in same PID namespace
    result = subprocess.run(beeline_cmd, env=env, capture_output=True, text=True)
    
    print("Beeline stdout:")
    print(result.stdout)
    print("Beeline stderr:")
    print(result.stderr)
    
    print("Stopping thrift server...")
    stop_thrift_server()
    
if __name__ == '__main__':
    run()
