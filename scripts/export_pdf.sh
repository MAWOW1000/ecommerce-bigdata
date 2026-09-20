#!/usr/bin/env bash
# Xuat bao cao .docx sang PDF de nop.
# Can LibreOffice: sudo apt install libreoffice-writer
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCX="${PROJECT_DIR}/BaoCao_ECommerce_BigData.docx"

if [[ ! -f "${DOCX}" ]]; then
  echo ">> Chua co file .docx. Chay truoc: uv run python -m ecommerce_bigdata.report"
  exit 1
fi

if ! command -v soffice >/dev/null 2>&1; then
  echo ">> Khong tim thay LibreOffice. Cai bang:"
  echo "     sudo apt install libreoffice-writer"
  exit 1
fi

soffice --headless --convert-to pdf --outdir "${PROJECT_DIR}" "${DOCX}"
echo ">> Da xuat ${PROJECT_DIR}/BaoCao_ECommerce_BigData.pdf"
echo ">> Luu y: mo file .docx trong Word/LibreOffice, bam Ctrl+A roi F9 de cap nhat"
echo "   muc luc TRUOC khi xuat PDF, neu khong muc luc se trong."
