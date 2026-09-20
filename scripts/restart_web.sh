#!/usr/bin/env bash
# Khoi dong lai web server demo tren port 8000.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"
mkdir -p data/logs

# Dung tien trinh cu dang giu port 8000 (neu co)
OLD_PID="$(ss -lptn 'sport = :8000' 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)"
[[ -n "${OLD_PID}" ]] && kill "${OLD_PID}" 2>/dev/null && sleep 1

nohup uv run uvicorn ecommerce_bigdata.web.app:app \
      --host 127.0.0.1 --port 8000 > data/logs/web.log 2>&1 &

for _ in $(seq 1 30); do
  curl -sf -o /dev/null http://127.0.0.1:8000/api/categories && { echo ">> Web san sang: http://127.0.0.1:8000"; exit 0; }
  sleep 0.4
done
echo ">> Khong khoi dong duoc, xem data/logs/web.log"; tail -20 data/logs/web.log; exit 1
