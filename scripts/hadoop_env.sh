#!/usr/bin/env bash
# Bien moi truong dung chung cho cac script Hadoop/Spark.
# Dung: source scripts/hadoop_env.sh

HADOOP_VER="3.4.1"
export HADOOP_HOME="${HOME}/.local/hadoop/hadoop-${HADOOP_VER}"
export PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HADOOP_CONF_DIR="${PROJECT_DIR}/conf/hadoop"

# Hadoop 3.4 chay on dinh tren Java 17; may co the dang mac dinh Java 21.
export JAVA_HOME="${JAVA_HOME_OVERRIDE:-/usr/lib/jvm/java-17-openjdk-amd64}"

export HADOOP_LOG_DIR="${PROJECT_DIR}/data/logs/hadoop"
export PATH="${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin:${PATH}"

# Dia chi HDFS dung trong moi script
export HDFS_URI="hdfs://127.0.0.1:9000"
