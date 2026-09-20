#!/usr/bin/env bash
# Dung cac daemon cua HDFS.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/hadoop_env.sh"
export HADOOP_CONF_DIR="${PROJECT_DIR}/data/hdfs/runtime"

for d in datanode namenode; do
  "${HADOOP_HOME}/bin/hdfs" --daemon stop "${d}" 2>/dev/null && echo ">> Da dung ${d}"
done
