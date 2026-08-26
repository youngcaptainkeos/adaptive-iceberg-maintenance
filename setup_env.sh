#!/usr/bin/env bash

# Determine the directory where this script is located
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# Set JAVA_HOME to OpenJDK 11
export JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"

# Set SPARK_HOME to point to our custom standalone Spark installation
export SPARK_HOME="$SCRIPT_DIR/software/spark-3.3.4"

# Prepend Spark binaries and local Python pip binaries to PATH
export PATH="$SPARK_HOME/bin:$HOME/.local/bin:$PATH"

echo "Environment configured:"
echo "  JAVA_HOME=$JAVA_HOME"
echo "  SPARK_HOME=$SPARK_HOME"
echo "  PATH updated with Spark and local user binaries."
