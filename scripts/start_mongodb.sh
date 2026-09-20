#!/usr/bin/env bash
# Khoi dong mongod o che do standalone, port 27017, ghi log vao data/logs.
set -euo pipefail
PREFIX="${HOME}/.local/mongodb"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "${PROJECT_DIR}/data/mongo" "${PROJECT_DIR}/data/logs"

if pgrep -f "mongod --dbpath ${PROJECT_DIR}/data/mongo" >/dev/null; then
  echo ">> mongod dang chay roi (port 27017)."
  exit 0
fi

"${PREFIX}/bin/mongod" \
  --dbpath "${PROJECT_DIR}/data/mongo" \
  --logpath "${PROJECT_DIR}/data/logs/mongod.log" \
  --port 27017 --bind_ip 127.0.0.1 --fork

echo ">> mongod dang chay tai 127.0.0.1:27017"
