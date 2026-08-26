# Team Setup Notes

To ensure all team members run workload benchmarks and PySpark scripts against the identical Spark installation and classpath:

## 1. Environment Setup

Always source the `setup_env.sh` script in your shell before running any Spark, PySpark, or LST-Bench tasks:

```bash
source setup_env.sh
```

This script sets the following environment variables:
- `JAVA_HOME`: Points to the OpenJDK 11 installation (`/usr/lib/jvm/java-11-openjdk-amd64`).
- `SPARK_HOME`: Points to the standalone custom Spark 3.3.4 installation (`/home/shashank/Link to PDocuments/Capstone/implementation/software/spark-3.3.4`).
- `PATH`: Prepends `$SPARK_HOME/bin` and `$HOME/.local/bin` to the PATH so that the correct `spark-submit` and `pip`-installed binaries are executed.

## 2. Standalone Spark and Iceberg Jar Configuration

- Standalone Spark installation is located at `software/spark-3.3.4`.
- The Apache Iceberg Spark Runtime JAR is placed directly in the Spark classpath under `software/spark-3.3.4/jars/iceberg-spark-runtime-3.3_2.12-1.4.3.jar`.
- By setting `SPARK_HOME` to this standalone directory, PySpark automatically loads this standalone Spark instance's JVM and jars folder. Therefore, the Iceberg jar is automatically on the classpath of all PySpark sessions.
