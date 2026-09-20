#!/usr/bin/env bash
# Khoi dong HDFS che do pseudo-distributed (NameNode + DataNode tren mot may).
#
# Khong dung start-dfs.sh vi script do goi SSH sang localhost, ma may nay
# khong bat sshd. Khoi dong thang tung daemon thi khong can SSH.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/hadoop_env.sh"

DATA_DIR="${PROJECT_DIR}/data"
mkdir -p "${HADOOP_LOG_DIR}" "${DATA_DIR}/hdfs"

# Thay cho giu cho DATA_DIR trong file cau hinh bang duong dan that
for f in core-site.xml hdfs-site.xml; do
  sed "s|DATA_DIR|${DATA_DIR}|g" "${HADOOP_CONF_DIR}/${f}" \
      > "${HADOOP_CONF_DIR}/${f}.generated"
done
mkdir -p "${DATA_DIR}/hdfs/runtime"
cp "${HADOOP_CONF_DIR}/core-site.xml.generated" "${DATA_DIR}/hdfs/runtime/core-site.xml"
cp "${HADOOP_CONF_DIR}/hdfs-site.xml.generated" "${DATA_DIR}/hdfs/runtime/hdfs-site.xml"
cp "${HADOOP_CONF_DIR}/hadoop-env.sh"           "${DATA_DIR}/hdfs/runtime/hadoop-env.sh"
rm -f "${HADOOP_CONF_DIR}"/*.generated
export HADOOP_CONF_DIR="${DATA_DIR}/hdfs/runtime"

# Lan dau chay: dinh dang NameNode (tao metadata rong)
if [[ ! -d "${DATA_DIR}/hdfs/name/current" ]]; then
  echo ">> Dinh dang NameNode lan dau ..."
  "${HADOOP_HOME}/bin/hdfs" namenode -format -force -nonInteractive >/dev/null 2>&1
  echo ">> Da dinh dang xong"
fi

start_daemon() {
  local name="$1"
  if jps 2>/dev/null | grep -qw "$2"; then
    echo ">> ${name} dang chay roi"
    return
  fi
  "${HADOOP_HOME}/bin/hdfs" --daemon start "${name}"
  echo ">> Da khoi dong ${name}"
}

start_daemon namenode NameNode
start_daemon datanode DataNode

# Cho NameNode thoat che do an toan roi moi cho dung
for _ in $(seq 1 30); do
  if "${HADOOP_HOME}/bin/hdfs" dfsadmin -safemode get 2>/dev/null | grep -q OFF; then
    break
  fi
  sleep 1
done
"${HADOOP_HOME}/bin/hdfs" dfsadmin -safemode wait >/dev/null 2>&1 || true

echo
echo ">> HDFS san sang: ${HDFS_URI}"
echo ">> Giao dien web NameNode: http://127.0.0.1:9870"
"${HADOOP_HOME}/bin/hdfs" dfsadmin -report 2>/dev/null | head -12
