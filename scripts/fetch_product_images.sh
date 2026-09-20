#!/usr/bin/env bash
# Tai mot bo anh minh hoa ve local de demo khong phu thuoc mang.
# Anh lay tu picsum.photos, dung seed co dinh nen moi lan tai deu ra cung anh.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${PROJECT_DIR}/src/ecommerce_bigdata/web/static/img/products"
COUNT="${1:-48}"

mkdir -p "${OUT}"
echo ">> Tai ${COUNT} anh vao ${OUT}"

for i in $(seq 0 $((COUNT - 1))); do
  f="${OUT}/p${i}.jpg"
  if [[ -s "${f}" ]]; then continue; fi
  curl -fsSL "https://picsum.photos/seed/ecom${i}/400/400" -o "${f}" \
    && printf "." || printf "x"
done
echo
echo ">> Xong: $(ls -1 "${OUT}" | wc -l) anh, $(du -sh "${OUT}" | cut -f1)"
