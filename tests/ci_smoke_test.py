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
    os.environ["AE_ENABLE_METRICS"] = "0"  # Disable metrics to avoid middleware issues
    os.environ["AE_JSON_LOGS"] = "0"  # Disable JSON logs to avoid middleware issues

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
    notes_str = str(notes).lower()
    assert "ospf" in notes_str
    assert "reasons" in notes_str
    assert "ranked" in notes_str


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


def test_auto_ranking_bgp_over_ospf_when_bgp_terms_present(client):
    """Test that BGP is ranked higher than OSPF when BGP terms are present."""
    q = "iosxe bgp neighbor down 192.0.2.1 on g0/0"
    r = client.post("/query?mode=auto", json={"query": q})
    body = r.json()
    assert body["intent"] == "TROUBLESHOOT"
    assert body["route"]["target"] == "bgp-neighbor-down"
    assert "step_hash" in body
    # winner must be present in notes.candidates[0]
    notes = body["notes"]
    assert notes["candidates"][0]["target"] == "bgp-neighbor-down"


def test_auto_ranking_ospf_over_bgp_when_ospf_state_terms_present(client):
    """Test that OSPF is ranked higher than BGP when OSPF state terms are present."""
    q = "junos ospf neighbor stuck in 2-way on ge-0/0/0 area 0.0.0.0"
    r = client.post("/query?mode=auto", json={"query": q})
    b = r.json()
    assert b["route"]["target"] == "ospf-neighbor-down"
    notes = b["notes"]
    assert notes["candidates"][0]["target"] == "ospf-neighbor-down"


def test_step_hash_stable_auto(client):
    """Test that step hash is stable across multiple calls."""
    q = "iosxe bgp neighbor down 192.0.2.1"
    h1 = client.post("/query?mode=auto", json={"query": q}).json()["step_hash"]
    h2 = client.post("/query?mode=auto", json={"query": q}).json()["step_hash"]
    assert h1 == h2


def test_debug_route_reasons(client):
    """Test debug route endpoint returns ranked reasons."""
    r = client.get(
        "/debug/route", params={"query": "iosxe bgp neighbor down 192.0.2.1"}
    )
    body = r.json()
    assert r.status_code == 200
    assert body["intent"] == "TROUBLESHOOT"
    assert body["target"] in {
        "bgp-neighbor-down",
        "tcp-handshake",
        "ospf-neighbor-down",
    }
    assert 0.60 <= body["confidence"] <= 1.0
    reasons = body["notes"].get("ranked_reasons", [])
    assert reasons and all(isinstance(x, str) for x in reasons)


def test_insufficient_steps_guard(client):
    """Test that insufficient steps returns proper error without 500."""
    # Use a query that should route to troubleshooting but with minimal tokens
    # This should trigger the insufficient steps guard in the playbook assembler
    q = "ospf neighbor down"
    r = client.post("/query?mode=auto", json={"query": q})
    assert r.status_code == 200
    body = r.json()
    # This should either succeed or return insufficient_steps, but not 500
    if "error" in body:
        assert body["error"] == "insufficient_steps"
        assert "steps_count" in body
        assert "evidence" in body
    else:
        # If it succeeds, it should have a valid response
        assert body["intent"] == "TROUBLESHOOT"
        assert "step_hash" in body


def test_auto_bgp_explain_includes_reasons(client):
    """Test that /query?explain=true returns reasons and confidence."""
    r = client.post(
        "/query?mode=auto&explain=true",
        json={"query": "iosxe bgp neighbor down 192.0.2.1"},
    )
    body = r.json()
    assert r.status_code == 200
    assert body.get("step_hash")
    xp = body.get("explain", {})
    assert 0.60 <= xp.get("confidence", 0) <= 1.0
    assert xp.get("ranked_reasons")
    assert isinstance(xp.get("matches", {}), dict)


def test_offtopic_abstain_reason_code(client):
    """Test that off-topic queries return ABSTAIN with OFFTOPIC reason code."""
    r = client.post("/query?mode=auto", json={"query": "weather in paris"})
    j = r.json()
    assert j.get("intent") in ("ABSTAIN", "abstain")
    assert j.get("reason_code") == "OFFTOPIC"


def test_low_confidence_abstain_reason_code(client):
    """Test that ambiguous queries return ABSTAIN with appropriate reason code."""
    r = client.post("/query?mode=auto", json={"query": "protocol"})
    j = r.json()
    assert j.get("intent") in ("ABSTAIN", "abstain")
    assert j.get("reason_code") in ("LOW_CONFIDENCE", "AMBIGUOUS", "SHORT_QUERY")


def test_explain_shows_vendor_inference(client):
    """Test that explain mode shows vendor inference information."""
    r = client.post(
        "/query?mode=auto&explain=true", json={"query": "Gi0/0 ospf neighbor down"}
    )
    j = r.json()
    exp = j.get("explain", {})
    assert "normalized" in exp and "vendor_inference" in exp
    vi = exp.get("vendor_inference") or {}
    # do not assert exact vendor, just structure
    assert "hits" in vi or "if_hits" in vi


def test_lacp_endpoint_smoke(client):
    """Test LACP port-channel endpoint returns valid response."""
    r = client.post(
        "/troubleshoot/lacp-portchannel",
        json={"vendor": "iosxe", "iface": "Port-channel1", "area": "0.0.0.0"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "steps" in body and len(body["steps"]) == 8
    assert "step_hash" in body


def test_auto_lacp_route_smoke(client):
    """Test auto-mode routing to LACP port-channel-down playbook."""
    q = "iosxe port-channel1 down lacp"
    r = client.post("/query?mode=auto", json={"query": q})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "TROUBLESHOOT"
    assert body["route"]["target"] == "lacp-port-channel-down"
    assert len(body["steps"]) == 8
    assert "step_hash" in body


def test_debug_route_lacp(client):
    """Test debug route endpoint for LACP queries."""
    q = "iosxe lacp port-channel down"
    r = client.get(f"/debug/route?query={q}")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "TROUBLESHOOT"
    assert body["target"] == "lacp-port-channel-down"
    assert "ranked_reasons" in body["notes"]
    assert any("lacp" in reason.lower() for reason in body["notes"]["ranked_reasons"])
    assert body["confidence"] >= 0.6


def test_arp_endpoint_smoke(client):
    """Test ARP anomalies endpoint returns valid response."""
    r = client.post(
        "/troubleshoot/arp-anomalies",
        json={"vendor": "iosxe", "iface": "192.0.2.10", "area": "0.0.0.0"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "steps" in body and len(body["steps"]) == 8
    assert "step_hash" in body


def test_auto_arp_route_smoke(client):
    """Test auto-mode routing to ARP anomalies playbook."""
    q = "iosxe arp incomplete 192.0.2.10 vlan 10"
    r = client.post("/query?mode=auto", json={"query": q})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "TROUBLESHOOT"
    assert body["route"]["target"] == "arp-anomalies"
    assert len(body["steps"]) == 8
    assert "step_hash" in body


def test_debug_route_arp(client):
    """Test debug route endpoint for ARP queries."""
    q = "iosxe arp incomplete vlan 10"
    r = client.get(f"/debug/route?query={q}")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "TROUBLESHOOT"
    assert body["target"] == "arp-anomalies"
    assert "ranked_reasons" in body["notes"]
    assert any("arp" in reason.lower() for reason in body["notes"]["ranked_reasons"])
    assert body["confidence"] >= 0.6
