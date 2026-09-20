#!/usr/bin/env bash
# Chay toan bo pipeline tu dau: du lieu -> phan tich -> bao cao.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

echo "=============== 1/7  Khoi dong MongoDB ==============="
./scripts/start_mongodb.sh

echo "=============== 2/7  Chuong 2: CSDL quan he =========="
uv run python -m ecommerce_bigdata.seed_sql

echo "=============== 3/7  Chuong 3: MongoDB ==============="
uv run python -m ecommerce_bigdata.seed_mongo

echo "=============== 4/7  Khoi dong HDFS ================="
./scripts/start_hdfs.sh

echo "=============== 5/7  Nap du lieu len HDFS ==========="
uv run python -m ecommerce_bigdata.hdfs_ingest

echo "=============== 6/7  Chuong 4: Phan tich ============"
uv run python scripts/generate_erd.py
uv run python -m ecommerce_bigdata.analytics
uv run python -m ecommerce_bigdata.spark_analytics

echo "=============== 7/7  Sinh bao cao .docx ============="
uv run python -m ecommerce_bigdata.report

echo
echo ">> Xong. Khoi dong web demo:  ./scripts/restart_web.sh"
