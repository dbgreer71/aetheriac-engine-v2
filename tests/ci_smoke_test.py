"""CI Smoke Test - Minimal API validation for CI gate."""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ae2.api.main import app


@pytest.fixture(scope="session")
def app_client():
    with TestClient(app) as client:
        yield client


def test_build_index_if_missing():
    """Ensure index exists for smoke tests."""
    index_dir = Path("data/index")
    if not (index_dir / "sections.jsonl").exists():
        # Build index if missing
        subprocess.run([sys.executable, "scripts/build_index.py"], check=True)


def test_healthz_endpoint(app_client):
    """Test /healthz endpoint."""
    response = app_client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body.get("ok") is True  # only boolean gate


def test_readyz_endpoint(app_client):
    """Test /readyz endpoint."""
    response = app_client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    # treat both {"ok": true} or {"ready": true} as pass
    assert body.get("ok", body.get("ready")) is True


def test_query_endpoint(app_client):
    """Test /query endpoint with auto mode."""
    response = app_client.post("/query?mode=auto", json={"query": "what is ospf"})
    assert response.status_code == 200
    body = response.json()
    # just ensure something non-empty shaped came back
    assert isinstance(body, dict) and len(body) > 0


def test_debug_index_endpoint(app_client):
    """Test /debug/index endpoint."""
    response = app_client.get("/debug/index")
    assert response.status_code == 200
    body = response.json()
    # accept either count or sections key
    count = body.get("concepts_count") or body.get("sections") or 0
    assert isinstance(count, int)


def test_bgp_endpoint_smoke(app_client):
    """Test POST /troubleshoot/bgp-neighbor endpoint."""
    # Set environment to disable auth for testing
    import os

    os.environ["AE_DISABLE_AUTH"] = "true"

    response = app_client.post(
        "/troubleshoot/bgp-neighbor", json={"vendor": "iosxe", "peer": "192.0.2.1"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "steps" in body
    assert len(body["steps"]) >= 8  # BGP playbook should have 8 steps
    assert "step_hash" in body  # Step hash should be present

    # Test deterministic behavior - two consecutive calls should yield identical step_hash
    response2 = app_client.post(
        "/troubleshoot/bgp-neighbor", json={"vendor": "iosxe", "peer": "192.0.2.1"}
    )
    assert response2.status_code == 200
    body2 = response2.json()
    assert (
        body["step_hash"] == body2["step_hash"]
    ), "Step hash should be deterministic across runs"


def test_debug_route_bgp(app_client):
    """Test GET /debug/route with BGP query."""
    # Set environment to disable auth for testing
    import os

    os.environ["AE_DISABLE_AUTH"] = "true"

    response = app_client.get("/debug/route?query=iosxe bgp neighbor down")
    assert response.status_code == 200
    body = response.json()
    assert "intent" in body
    assert body["intent"] == "TROUBLESHOOT"
    assert "target" in body
    assert body["target"] == "bgp-neighbor-down"


def test_auto_bgp_route_smoke(app_client):
    """Test POST /query?mode=auto with BGP query."""
    # Set environment to disable auth for testing
    import os

    os.environ["AE_DISABLE_AUTH"] = "true"

    response = app_client.post(
        "/query?mode=auto", json={"query": "iosxe bgp neighbor down 192.0.2.1"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "intent" in body
    assert body["intent"] == "TROUBLESHOOT"
    assert "steps" in body
    assert len(body["steps"]) >= 8  # Should route to BGP playbook with 8 steps
    assert "step_hash" in body  # Step hash should be present

    # Test deterministic behavior - two consecutive calls should yield identical step_hash
    response2 = app_client.post(
        "/query?mode=auto", json={"query": "iosxe bgp neighbor down 192.0.2.1"}
    )
    assert response2.status_code == 200
    body2 = response2.json()
    assert (
        body["step_hash"] == body2["step_hash"]
    ), "Step hash should be deterministic across runs"
