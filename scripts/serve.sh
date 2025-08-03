#!/usr/bin/env bash
set -euo pipefail

# Config
: "${AE_BIND_HOST:=0.0.0.0}"
: "${AE_BIND_PORT:=8001}"
: "${AE_INDEX_DIR:=/app/data/index}"
: "${ENABLE_DENSE:=0}"

echo "[serve] starting aev2 (host=${AE_BIND_HOST} port=${AE_BIND_PORT} index=${AE_INDEX_DIR} dense=${ENABLE_DENSE})"

# Ensure index exists (build if missing)
if [ ! -d "${AE_INDEX_DIR}" ] || [ -z "$(ls -A "${AE_INDEX_DIR}" 2>/dev/null || true)" ]; then
  echo "[serve] index missing, building..."
  mkdir -p "${AE_INDEX_DIR}"
  python scripts/build_index.py
fi

# Start API with exec for proper signal handling
exec AE_BIND_PORT="${AE_BIND_PORT}" AE_BIND_HOST="${AE_BIND_HOST}" AE_INDEX_DIR="${AE_INDEX_DIR}" ENABLE_DENSE="${ENABLE_DENSE}" \
  python -m ae2.api.main
