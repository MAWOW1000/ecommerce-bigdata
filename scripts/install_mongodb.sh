#!/usr/bin/env bash
# Cai dat MongoDB 8.0 + mongosh native (khong can sudo, khong dung Docker).
# Giai nen vao ~/.local/mongodb, du lieu nam trong <project>/data/mongo
set -euo pipefail

MONGO_VER="8.0.15"
MONGOSH_VER="2.3.8"
PREFIX="${HOME}/.local/mongodb"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="${PROJECT_DIR}/.cache"

mkdir -p "${PREFIX}/bin" "${CACHE}" "${PROJECT_DIR}/data/mongo" "${PROJECT_DIR}/data/logs"

if [[ ! -x "${PREFIX}/bin/mongod" ]]; then
  echo ">> Tai MongoDB ${MONGO_VER} ..."
  curl -fSL --retry 3 \
    "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2404-${MONGO_VER}.tgz" \
    -o "${CACHE}/mongodb.tgz"
  tar -xzf "${CACHE}/mongodb.tgz" -C "${CACHE}"
  cp "${CACHE}/mongodb-linux-x86_64-ubuntu2404-${MONGO_VER}"/bin/* "${PREFIX}/bin/"
  echo ">> mongod -> ${PREFIX}/bin/mongod"
else
  echo ">> mongod da co san, bo qua."
fi

if [[ ! -x "${PREFIX}/bin/mongosh" ]]; then
  echo ">> Tai mongosh ${MONGOSH_VER} ..."
  curl -fSL --retry 3 \
    "https://downloads.mongodb.com/compass/mongosh-${MONGOSH_VER}-linux-x64.tgz" \
    -o "${CACHE}/mongosh.tgz"
  tar -xzf "${CACHE}/mongosh.tgz" -C "${CACHE}"
  cp "${CACHE}/mongosh-${MONGOSH_VER}-linux-x64"/bin/* "${PREFIX}/bin/"
  echo ">> mongosh -> ${PREFIX}/bin/mongosh"
else
  echo ">> mongosh da co san, bo qua."
fi

"${PREFIX}/bin/mongod" --version | head -1
"${PREFIX}/bin/mongosh" --version
echo ">> Xong. Khoi dong bang: scripts/start_mongodb.sh"
