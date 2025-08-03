#!/usr/bin/env bash
set -euo pipefail
mkdir -p data/rfc_raw && cd data/rfc_raw
for n in 826 2328 4271 9293 791 1812 8200 1918; do
  curl -fsSLO "https://www.rfc-editor.org/rfc/rfc${n}.txt"
done
echo "[OK] synced minimal RFC set"
