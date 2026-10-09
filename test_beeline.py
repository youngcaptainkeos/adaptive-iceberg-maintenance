import subprocess
import sys
sys.path.append('scripts/phase3b-predictive-signals/runner')
from run_phase3b_experiment import start_thrift_server, stop_thrift_server, get_spark_env

start_thrift_server('FIFO')
beeline_cmd = ["beeline", "-u", "jdbc:hive2://127.0.0.1:10000/default", "-n", "anonymous", "-p", "", "-e", "DROP TABLE IF EXISTS local.experiment.interference_treatment;"]
env = get_spark_env()
result = subprocess.run(beeline_cmd, env=env, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
stop_thrift_server()
