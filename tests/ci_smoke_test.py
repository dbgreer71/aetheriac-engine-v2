"""CI Smoke Test - Minimal API validation for CI gate."""

import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from ae2.api.main import app


def test_build_index_if_missing():
    """Ensure index exists for smoke tests."""
    index_dir = Path("data/index")
    if not (index_dir / "sections.jsonl").exists():
        # Build index if missing
        subprocess.run([sys.executable, "scripts/build_index.py"], check=True)


def test_healthz_endpoint():
    """Test /healthz endpoint."""
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["ok"] is True


def test_readyz_endpoint():
    """Test /readyz endpoint."""
    with TestClient(app) as client:
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["sections"] > 0


def test_query_endpoint():
    """Test /query endpoint with auto mode."""
    with TestClient(app) as client:
        response = client.post("/query?mode=auto", json={"query": "what is ospf"})
        assert response.status_code == 200


def test_debug_index_endpoint():
    """Test /debug/index endpoint."""
    with TestClient(app) as client:
        response = client.get("/debug/index")
        assert response.status_code == 200
        data = response.json()
        assert "sections" in data
        assert "rfc_numbers" in data
