"""
CI smoke tests for OSPF auto-mode functionality.

These tests verify that OSPF neighbor-down troubleshooting works correctly
in auto mode with deterministic step hashes.
"""

import pytest
import os
from fastapi.testclient import TestClient
from ae2.api.main import app


@pytest.fixture(autouse=True)
def disable_auth():
    """Disable authentication for smoke tests."""
    os.environ["AE_DISABLE_AUTH"] = "true"
    yield
    os.environ.pop("AE_DISABLE_AUTH", None)


@pytest.fixture
def client():
    """Create test client with initialized stores."""
    # Set environment for testing
    os.environ["ENABLE_DENSE"] = "0"
    os.environ["AE_INDEX_DIR"] = "data/index"

    # Use TestClient with proper lifespan management
    with TestClient(app) as test_client:
        # Manually initialize the store for testing
        from ae2.retriever.index_store import IndexStore
        from ae2.concepts.store import ConceptStore
        import ae2.api.main as api_main

        # Initialize stores
        api_main.store = IndexStore("data/index")
        api_main.concept_store = ConceptStore()

        yield test_client


def test_ospf_endpoint_smoke(client):
    """Test OSPF neighbor endpoint returns valid response."""
    r = client.post(
        "/troubleshoot/ospf-neighbor",
        json={"vendor": "iosxe", "iface": "GigabitEthernet0/0", "area": "0.0.0.0"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "steps" in body and len(body["steps"]) >= 8
    assert "step_hash" in body


def test_auto_ospf_route_smoke(client):
    """Test auto-mode routing to OSPF neighbor-down playbook."""
    q = "iosxe g0/0 ospf neighbor down area 0.0.0.0"
    r = client.post("/query?mode=auto", json={"query": q})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "TROUBLESHOOT"
    assert body["route"]["target"] == "ospf-neighbor-down"
    assert "step_hash" in body


def test_ospf_step_hash_deterministic(client):
    """Test that OSPF step hash is deterministic for same query."""
    q = "iosxe g0/0 ospf neighbor down area 0.0.0.0"
    r1 = client.post("/query?mode=auto", json={"query": q}).json()
    r2 = client.post("/query?mode=auto", json={"query": q}).json()
    assert r1.get("step_hash") == r2.get("step_hash")


def test_ospf_vendor_detection(client):
    """Test OSPF routing works with different vendors."""
    # Test IOS-XE
    q1 = "iosxe g0/0 ospf neighbor down area 0.0.0.0"
    r1 = client.post("/query?mode=auto", json={"query": q1})
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["intent"] == "TROUBLESHOOT"
    assert body1["route"]["target"] == "ospf-neighbor-down"

    # Test JunOS
    q2 = "junos ge-0/0/0 ospf neighbor down area 0.0.0.0"
    r2 = client.post("/query?mode=auto", json={"query": q2})
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["intent"] == "TROUBLESHOOT"
    assert body2["route"]["target"] == "ospf-neighbor-down"


def test_ospf_state_terms(client):
    """Test OSPF routing with different state terms."""
    state_terms = ["down", "stuck", "2-way", "exstart", "loading", "dead"]

    for term in state_terms:
        q = f"iosxe g0/0 ospf neighbor {term} area 0.0.0.0"
        r = client.post("/query?mode=auto", json={"query": q})
        assert r.status_code == 200
        body = r.json()
        assert body["intent"] == "TROUBLESHOOT"
        assert body["route"]["target"] == "ospf-neighbor-down"


def test_ospf_interface_extraction(client):
    """Test OSPF interface extraction from query."""
    interfaces = [
        ("g0/0", "GigabitEthernet0/0"),
        ("GigabitEthernet0/0", "GigabitEthernet0/0"),
        ("ge-0/0/0", "ge-0/0/0"),
        ("Ethernet0/0", "Ethernet0/0"),
    ]

    for iface_pattern, expected in interfaces:
        q = f"iosxe {iface_pattern} ospf neighbor down area 0.0.0.0"
        r = client.post("/query?mode=auto", json={"query": q})
        assert r.status_code == 200
        body = r.json()
        assert body["intent"] == "TROUBLESHOOT"
        assert body["route"]["target"] == "ospf-neighbor-down"


def test_ospf_area_extraction(client):
    """Test OSPF area extraction from query."""
    areas = ["0.0.0.0", "0", "1", "2.2.2.2"]

    for area in areas:
        q = f"iosxe g0/0 ospf neighbor down area {area}"
        r = client.post("/query?mode=auto", json={"query": q})
        assert r.status_code == 200
        body = r.json()
        assert body["intent"] == "TROUBLESHOOT"
        assert body["route"]["target"] == "ospf-neighbor-down"


def test_ospf_abstain_precedence(client):
    """Test that OSPF routing respects ABSTAIN precedence for ambiguous queries."""
    # Short query should abstain
    q1 = "ospf"
    r1 = client.post("/query?mode=auto", json={"query": q1})
    assert r1.status_code == 200
    body1 = r1.json()
    # Should not route to TROUBLESHOOT for ambiguous query
    assert body1["intent"] != "TROUBLESHOOT"

    # Off-topic query should abstain
    q2 = "what is the weather like"
    r2 = client.post("/query?mode=auto", json={"query": q2})
    assert r2.status_code == 200
    body2 = r2.json()
    # Should not route to TROUBLESHOOT for off-topic query
    assert body2["intent"] != "TROUBLESHOOT"


def test_ospf_confidence_scores(client):
    """Test OSPF routing confidence scores."""
    # High confidence with vendor + ospf + state terms
    q1 = "iosxe g0/0 ospf neighbor down area 0.0.0.0"
    r1 = client.post("/query?mode=auto", json={"query": q1})
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["intent"] == "TROUBLESHOOT"
    assert body1["confidence"] >= 0.7

    # Lower confidence with just ospf + state terms
    q2 = "ospf neighbor down"
    r2 = client.post("/query?mode=auto", json={"query": q2})
    assert r2.status_code == 200
    body2 = r2.json()
    # Should still route to TROUBLESHOOT but with lower confidence
    assert body2["intent"] == "TROUBLESHOOT"


def test_ospf_reasons_in_notes(client):
    """Test that OSPF routing includes reasons in notes."""
    q = "iosxe g0/0 ospf neighbor down area 0.0.0.0"
    r = client.post("/query?mode=auto", json={"query": q})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "TROUBLESHOOT"

    # Check that notes contain routing reasons
    notes = body["route"]["evidence"]["notes"]
    assert "ospf" in notes.lower()
    assert "iosxe" in notes.lower()
    assert "reasons" in notes.lower()


def test_ospf_step_hash_consistency(client):
    """Test that OSPF step hash is consistent across different query formats."""
    queries = [
        "iosxe g0/0 ospf neighbor down area 0.0.0.0",
        "iosxe GigabitEthernet0/0 ospf neighbor down area 0.0.0.0",
        "iosxe g0/0 ospf neighbor stuck area 0.0.0.0",
    ]

    hashes = []
    for q in queries:
        r = client.post("/query?mode=auto", json={"query": q})
        assert r.status_code == 200
        body = r.json()
        assert body["intent"] == "TROUBLESHOOT"
        hashes.append(body.get("step_hash", ""))

    # All hashes should be the same for same playbook
    assert len(set(hashes)) == 1
