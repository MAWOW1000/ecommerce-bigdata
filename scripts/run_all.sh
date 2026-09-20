#!/usr/bin/env bash
# Chay toan bo pipeline tu dau: du lieu -> phan tich -> bao cao.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

echo "=============== 1/5  Khoi dong MongoDB ==============="
./scripts/start_mongodb.sh

echo "=============== 2/5  Chuong 2: CSDL quan he =========="
uv run python -m ecommerce_bigdata.seed_sql

echo "=============== 3/5  Chuong 3: MongoDB ==============="
uv run python -m ecommerce_bigdata.seed_mongo

echo "=============== 4/5  Chuong 4: Phan tich ============="
uv run python scripts/generate_erd.py
uv run python -m ecommerce_bigdata.analytics

echo "=============== 5/5  Sinh bao cao .docx =============="
uv run python -m ecommerce_bigdata.report

echo
echo ">> Xong. Khoi dong web demo:  ./scripts/restart_web.sh"
