#!/usr/bin/env bash
# Cai Hadoop 3.4.1 (ban lean) native, khong Docker, khong sudo.
# Giai nen truc tiep tu luong tai ve de khong ton gap doi dung luong dia.
set -euo pipefail

HADOOP_VER="3.4.1"
PREFIX="${HOME}/.local/hadoop"
HADOOP_HOME="${PREFIX}/hadoop-${HADOOP_VER}"
URL="https://dlcdn.apache.org/hadoop/common/hadoop-${HADOOP_VER}/hadoop-${HADOOP_VER}-lean.tar.gz"

if [[ -x "${HADOOP_HOME}/bin/hdfs" ]]; then
  echo ">> Hadoop da co san tai ${HADOOP_HOME}"
else
  mkdir -p "${PREFIX}"
  echo ">> Tai va giai nen Hadoop ${HADOOP_VER} (khoang 471 MB) ..."
  curl -fSL --retry 3 "${URL}" | tar -xz -C "${PREFIX}"
  echo ">> Da cai vao ${HADOOP_HOME}"
fi

"${HADOOP_HOME}/bin/hadoop" version | head -1
