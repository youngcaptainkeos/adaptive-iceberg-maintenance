import os
import sys
import json
import socket
import platform
import psutil
from datetime import datetime

# Path definitions
BASE_DIR = "scripts/phase2-validated-layout-comparison"
RESULTS_DIR = os.path.join(BASE_DIR, "results")

def main():
    print("Collecting system environment and benchmark metadata...")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # 1. OS details
    os_name = platform.system()
    os_release = platform.release()
    os_version = platform.version()
    
    # 2. CPU details
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)
    
    cpu_model = "Unknown CPU"
    try:
        if os_name == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_model = line.split(":")[1].strip()
                        break
    except Exception as e:
        print(f"Warning: could not read model name from /proc/cpuinfo: {e}")

    # 3. RAM details
    mem = psutil.virtual_memory()
    total_ram = f"{round(mem.total / (1024 * 1024 * 1024), 2)} GB"
    
    # 4. Check if workstation is relatively idle
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    cpu_usage = psutil.cpu_percent(interval=1)
    
    # Workstation is considered idle if 1-minute load average divided by cores is < 0.3
    is_idle = (load_avg[0] / logical_cores) < 0.3 if logical_cores else False
    idle_status = (
        f"Relatively idle (1-min load avg: {load_avg[0]:.2f}, CPU usage: {cpu_usage:.1f}%)" 
        if is_idle else 
        f"Active/Shared workstation (1-min load avg: {load_avg[0]:.2f}, CPU usage: {cpu_usage:.1f}%)"
    )

    # 5. Environment variables
    spark_home = os.environ.get("SPARK_HOME", "software/spark-3.3.4")
    java_home = os.environ.get("JAVA_HOME", "software/java-11")

    # 6. Extract Iceberg version from pom.xml or metadata
    iceberg_version = "1.4.3" # Hardcoded based on project spec and POM
    
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "hostname": socket.gethostname(),
        "os_name": os_name,
        "os_release": os_release,
        "os_version": os_version,
        "cpu_model": cpu_model,
        "logical_cpu_cores": logical_cores,
        "physical_cpu_cores": physical_cores,
        "total_physical_memory": total_ram,
        "workstation_idle_status": idle_status,
        "spark_version": "3.3.4",
        "java_version": "openjdk 11.0.24",
        "iceberg_version": iceberg_version,
        "scale_factor": "1",
        "repetitions": 22,
        "warmup_policy": "2 warmups (repetitions 0, 1), 20 measured (repetitions 2 to 21)",
        "spark_home": spark_home,
        "java_home": java_home,
        "spark_conf": {
            "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
            "spark.sql.catalog.local": "org.apache.iceberg.spark.SparkCatalog",
            "spark.sql.catalog.local.type": "hadoop",
            "spark.sql.catalog.local.warehouse": "file:///home/shashank/Link to PDocuments/Capstone/implementation/warehouse"
        }
    }
    
    out_path = os.path.join(RESULTS_DIR, "environment_metadata.json")
    with open(out_path, 'w') as f:
        json.dump(metadata, f, indent=4)
        
    print(f"Environment metadata written to {out_path}")

if __name__ == "__main__":
    main()
