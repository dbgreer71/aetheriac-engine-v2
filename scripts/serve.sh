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

# Start API
trap 'echo "[serve] SIGTERM received, shutting down"; exit 0' TERM INT
AE_BIND_PORT="${AE_BIND_PORT}" AE_INDEX_DIR="${AE_INDEX_DIR}" ENABLE_DENSE="${ENABLE_DENSE}" \
  python -m ae2.api.main &
PID=$!

# Wait for readiness (10s)
for i in {1..20}; do
  if curl -sf "http://127.0.0.1:${AE_BIND_PORT}/readyz" >/dev/null; then
    echo "[serve] ready"
    break
  fi
  sleep 0.5
done

wait "${PID}"
