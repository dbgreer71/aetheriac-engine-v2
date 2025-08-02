#!/bin/bash

# AE v2 Serving Script
# This script serves as the container entrypoint for AE v2

set -e

# Default values
AE_BIND_PORT=${AE_BIND_PORT:-8001}
ENABLE_DENSE=${ENABLE_DENSE:-0}
AE_INDEX_DIR=${AE_INDEX_DIR:-/app/data/index}

echo "Starting AE v2 API server..."
echo "  Bind port: $AE_BIND_PORT"
echo "  Enable dense: $ENABLE_DENSE"
echo "  Index directory: $AE_INDEX_DIR"

# Check if index exists
if [ ! -f "$AE_INDEX_DIR/sections.jsonl" ]; then
    echo "Warning: Index not found at $AE_INDEX_DIR/sections.jsonl"
    echo "Please ensure the index is built and mounted correctly"
fi

# Start the API server
exec python -m ae2.api.main
