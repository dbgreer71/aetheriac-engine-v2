"""
Golden tests for unified router and assembler system.

This module contains deterministic test scenarios for the unified router
and assembler to ensure consistent behavior across all three paths.
"""

import pytest
from fastapi.testclient import TestClient
from ae2.api.main import app
import ae2.api.main as api_main
from ae2.retriever.index_store import IndexStore
from ae2.concepts.store import ConceptStore
import os


@pytest.fixture
def client():
    """Create test client with stores initialized."""
    # Set environment for testing
    os.environ["ENABLE_DENSE"] = "0"
    os.environ["AE_INDEX_DIR"] = "data/index"

    # Use TestClient with proper lifespan management
    with TestClient(app) as test_client:
        # Manually initialize the stores for testing
        api_main.store = IndexStore("data/index")
        api_main.concept_store = ConceptStore()

        yield test_client


class TestDefinitionRouting:
    """Test definition intent routing and assembly."""

    def test_ospf_definition(self, client):
        """Test OSPF definition query."""
        response = client.post("/query?mode=auto", json={"query": "what is ospf"})
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "DEFINE"
        assert data["route"]["target"] == "2328"  # OSPF RFC
        assert "answer" in data
        assert len(data["citations"]) > 0
        assert data["mode"] == "auto"

    def test_arp_definition(self, client):
        """Test ARP definition query."""
        response = client.post("/query?mode=auto", json={"query": "arp definition"})
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "DEFINE"
        assert data["route"]["target"] == "826"  # ARP RFC
        assert "answer" in data
        assert len(data["citations"]) > 0

    def test_tcp_overview(self, client):
        """Test TCP overview query."""
        response = client.post("/query?mode=auto", json={"query": "tcp overview"})
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "DEFINE"
        assert data["route"]["target"] == "9293"  # TCP RFC
        assert "answer" in data
        assert len(data["citations"]) > 0


class TestConceptRouting:
    """Test concept intent routing and assembly."""

    def test_arp_concept_card(self, client):
        """Test ARP concept card query."""
        response = client.post("/query?mode=auto", json={"query": "arp concept card"})
        assert response.status_code == 200

        data = response.json()
        # Should route to concept if card exists, otherwise fall back to definition
        if data["intent"] == "CONCEPT":
            assert "card" in data
            assert len(data["citations"]) > 0
        else:
            assert data["intent"] == "DEFINE"
            assert "answer" in data

    def test_show_me_arp_concept(self, client):
        """Test 'show me' concept query."""
        response = client.post(
            "/query?mode=auto", json={"query": "show me the arp concept"}
        )
        assert response.status_code == 200

        data = response.json()
        # Should route to concept if card exists, otherwise fall back to definition
        if data["intent"] == "CONCEPT":
            assert "card" in data
        else:
            assert data["intent"] == "DEFINE"
            assert "answer" in data

    def test_default_route_concept(self, client):
        """Test default route concept query."""
        response = client.post(
            "/query?mode=auto", json={"query": "default route concept"}
        )
        assert response.status_code == 200

        data = response.json()
        # Should route to concept if card exists, otherwise fall back to definition
        if data["intent"] == "CONCEPT":
            assert "card" in data
        else:
            assert data["intent"] == "DEFINE"
            assert "answer" in data


class TestTroubleshootingRouting:
    """Test troubleshooting intent routing and assembly."""

    def test_ospf_neighbor_down_iosxe(self, client):
        """Test OSPF neighbor down on IOS-XE."""
        response = client.post(
            "/query?mode=auto",
            json={
                "query": "ospf neighbor down on iosxe g0/0",
                "vendor": "iosxe",
                "iface": "GigabitEthernet0/0",
                "area": "0.0.0.0",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "TROUBLESHOOT"
        assert data["route"]["target"] == "ospf-neighbor-down"
        assert "steps" in data
        assert len(data["steps"]) > 0
        assert len(data["citations"]) > 0

    def test_junos_ospf_exstart(self, client):
        """Test Junos OSPF stuck in EXSTART."""
        response = client.post(
            "/query?mode=auto",
            json={
                "query": "junos ospf stuck in exstart",
                "vendor": "junos",
                "iface": "ge-0/0/0",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "TROUBLESHOOT"
        assert data["route"]["target"] == "ospf-neighbor-down"
        assert "steps" in data
        assert len(data["steps"]) > 0
        assert len(data["citations"]) > 0

    def test_ospf_mtu_mismatch(self, client):
        """Test OSPF MTU mismatch troubleshooting."""
        response = client.post(
            "/query?mode=auto",
            json={"query": "iosxe ospf mtu mismatch gigabitethernet0/0"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "TROUBLESHOOT"
        assert data["route"]["target"] == "ospf-neighbor-down"
        assert "steps" in data
        assert len(data["steps"]) > 0
        assert data["mode"] == "auto"

    def test_bgp_troubleshoot_target(self, client):
        """Test BGP neighbor-down troubleshooting routing."""
        response = client.post(
            "/query?mode=auto",
            json={"query": "iosxe bgp neighbor down 192.0.2.1"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "TROUBLESHOOT"
        assert data["route"]["target"] == "bgp-neighbor-down"
        assert "steps" in data
        assert len(data["steps"]) >= 8  # BGP playbook has 8 steps
        assert data["mode"] == "auto"
        assert "step_hash" in data  # Step hash should be present

        # Test deterministic behavior - two consecutive calls should yield identical step_hash
        response2 = client.post(
            "/query?mode=auto",
            json={"query": "iosxe bgp neighbor down 192.0.2.1"},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert (
            data["step_hash"] == data2["step_hash"]
        ), "Step hash should be deterministic across runs"

    def test_tcp_troubleshoot_target(self, client):
        """Test TCP handshake troubleshooting routing."""
        response = client.post(
            "/query?mode=auto",
            json={"query": "iosxe tcp syn timeout 203.0.113.10:443"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "TROUBLESHOOT"
        assert data["route"]["target"] == "tcp-handshake"
        assert "steps" in data
        assert len(data["steps"]) >= 8  # TCP playbook has 8 steps
        assert data["mode"] == "auto"
        assert "step_hash" in data  # Step hash should be present

        # Test deterministic behavior - two consecutive calls should yield identical step_hash
        response2 = client.post(
            "/query?mode=auto",
            json={"query": "iosxe tcp syn timeout 203.0.113.10:443"},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert (
            data["step_hash"] == data2["step_hash"]
        ), "Step hash should be deterministic across runs"


class TestDebugEndpoints:
    """Test debug endpoints for routing and assembly."""

    def test_debug_route_ospf(self, client):
        """Test debug route for OSPF query."""
        response = client.get("/debug/route", params={"query": "what is ospf"})
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "DEFINE"
        assert data["target"] == "2328"
        assert "matches" in data
        assert "confidence" in data
        assert "notes" in data

    def test_debug_route_concept(self, client):
        """Test debug route for concept query."""
        response = client.get("/debug/route", params={"query": "arp concept card"})
        assert response.status_code == 200

        data = response.json()
        # Should be CONCEPT if card exists, otherwise DEFINE
        assert data["intent"] in ["CONCEPT", "DEFINE"]
        assert "matches" in data
        assert "confidence" in data

    def test_debug_route_troubleshoot(self, client):
        """Test debug route for troubleshooting query."""
        response = client.get(
            "/debug/route", params={"query": "iosxe g0/0 ospf neighbor down"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "TROUBLESHOOT"
        assert data["target"] == "ospf-neighbor-down"
        assert "matches" in data
        assert "confidence" in data


class TestDeterministicBehavior:
    """Test deterministic behavior across multiple runs."""

    def test_deterministic_ospf_definition(self, client):
        """Test that OSPF definition queries are deterministic."""
        query = {"query": "what is ospf"}

        response1 = client.post("/query?mode=auto", json=query)
        response2 = client.post("/query?mode=auto", json=query)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Intent and target should be identical
        assert data1["intent"] == data2["intent"]
        assert data1["route"]["target"] == data2["route"]["target"]
        assert (
            data1["route"]["evidence"]["matched_terms"]
            == data2["route"]["evidence"]["matched_terms"]
        )

    def test_deterministic_troubleshooting(self, client):
        """Test that troubleshooting queries are deterministic."""
        query = {
            "query": "ospf neighbor down",
            "vendor": "iosxe",
            "iface": "GigabitEthernet0/0",
        }

        response1 = client.post("/query?mode=auto", json=query)
        response2 = client.post("/query?mode=auto", json=query)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Intent and target should be identical
        assert data1["intent"] == data2["intent"]
        assert data1["route"]["target"] == data2["route"]["target"]
        assert len(data1["steps"]) == len(data2["steps"])


class TestBackwardCompatibility:
    """Test that existing modes still work."""

    def test_hybrid_mode_still_works(self, client):
        """Test that hybrid mode still works."""
        response = client.post("/query?mode=hybrid", json={"query": "what is ospf"})
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert data["mode"] == "hybrid"

    def test_tfidf_mode_still_works(self, client):
        """Test that tfidf mode still works."""
        response = client.post("/query?mode=tfidf", json={"query": "what is ospf"})
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert data["mode"] == "tfidf"

    def test_bm25_mode_still_works(self, client):
        """Test that bm25 mode still works."""
        response = client.post("/query?mode=bm25", json={"query": "what is ospf"})
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert data["mode"] == "bm25"
