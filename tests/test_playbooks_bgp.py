"""
Golden tests for BGP neighbor-down playbook system.

This module contains deterministic test scenarios for the BGP neighbor-down
troubleshooting playbook to ensure consistent behavior across vendors.
"""

import pytest
import hashlib
from fastapi.testclient import TestClient
from ae2.api.main import app
from ae2.playbooks.models import PlayContext
from ae2.playbooks.bgp_neighbor_down import (
    run_bgp_playbook,
    create_bgp_neighbor_playbook,
)
from ae2.retriever.index_store import IndexStore
import os


@pytest.fixture
def client():
    """Create test client with index store."""
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


@pytest.fixture
def store():
    """Create index store for testing."""
    index_dir = os.path.join("data", "index")
    if os.path.exists(index_dir):
        return IndexStore(index_dir)
    return None


class TestBGPNeighborPlaybook:
    """Test BGP neighbor-down troubleshooting playbook."""

    def test_playbook_creation(self):
        """Test that BGP neighbor playbook is created correctly."""
        playbook = create_bgp_neighbor_playbook()

        assert playbook.id == "bgp-neighbor-down"
        assert "BGP" in playbook.applies_to
        assert len(playbook.rules) == 8  # Expected number of rules

        # Check specific rules exist in deterministic order
        rule_ids = [rule.id for rule in playbook.rules]
        expected_rules = [
            "check_neighbor_fsm_state",
            "check_interface_status_mtu",
            "check_authentication_md5_keychain",
            "check_ebgp_multihop_ttl_gtsm",
            "check_keepalive_hold_timers_mismatch",
            "check_afi_safi_mismatch",
            "check_route_policy_filters",
            "check_peer_asn_mismatch",
        ]

        assert rule_ids == expected_rules

        # Check RFC citations are present
        for rule in playbook.rules:
            assert len(rule.citations) > 0
            assert len(rule.citations) <= 3  # Max 3 citations per step

    def test_iosxe_commands(self):
        """Test IOS-XE BGP command rendering."""
        from ae2.vendor_ir.models import VendorCommandIR

        # Test BGP summary
        cmd = VendorCommandIR(intent="show_bgp_summary", params={})
        commands = cmd.render("iosxe")
        assert commands == ["show ip bgp summary"]

        # Test BGP neighbor
        cmd = VendorCommandIR(intent="show_bgp_neighbor", params={"peer": "192.0.2.1"})
        commands = cmd.render("iosxe")
        assert commands == ["show ip bgp neighbors 192.0.2.1"]

        # Test BGP config
        cmd = VendorCommandIR(intent="show_bgp_config", params={})
        commands = cmd.render("iosxe")
        assert commands == ["show running-config | section ^router bgp"]

    def test_junos_commands(self):
        """Test Junos BGP command rendering."""
        from ae2.vendor_ir.models import VendorCommandIR

        # Test BGP summary
        cmd = VendorCommandIR(intent="show_bgp_summary", params={})
        commands = cmd.render("junos")
        assert commands == ["show bgp summary"]

        # Test BGP neighbor
        cmd = VendorCommandIR(intent="show_bgp_neighbor", params={"peer": "192.0.2.1"})
        commands = cmd.render("junos")
        assert commands == ["show bgp neighbor 192.0.2.1"]

        # Test BGP config
        cmd = VendorCommandIR(intent="show_bgp_config", params={})
        commands = cmd.render("junos")
        assert commands == ["show configuration protocols bgp | display set"]

    def test_playbook_execution_iosxe(self, store):
        """Test BGP playbook execution for IOS-XE."""
        if store is None:
            pytest.skip("Index store not available")

        ctx = PlayContext(
            vendor="iosxe",
            peer="192.0.2.1",
            iface="GigabitEthernet0/0",
            ttl=1,
            multihop=False,
        )

        result = run_bgp_playbook(ctx, store)

        assert result.playbook_id == "bgp-neighbor-down"
        assert len(result.steps) == 8  # Fixed number of steps

        # Check first step is FSM state check
        first_step = result.steps[0]
        assert first_step.rule_id == "check_neighbor_fsm_state"
        assert "FSM state" in first_step.check

        # Check interface status step
        interface_step = result.steps[1]
        assert interface_step.rule_id == "check_interface_status_mtu"
        assert "interface" in interface_step.check

        # Check GTSM step has RFC5082 citation
        gtsm_step = result.steps[3]
        assert gtsm_step.rule_id == "check_ebgp_multihop_ttl_gtsm"
        gtsm_citations = [c.rfc for c in gtsm_step.citations]
        assert 5082 in gtsm_citations

    def test_playbook_execution_junos(self, store):
        """Test BGP playbook execution for Junos."""
        if store is None:
            pytest.skip("Index store not available")

        ctx = PlayContext(
            vendor="junos",
            peer="192.0.2.1",
            iface="ge-0/0/0",
            ttl=1,
            multihop=False,
        )

        result = run_bgp_playbook(ctx, store)

        assert result.playbook_id == "bgp-neighbor-down"
        assert len(result.steps) == 8  # Fixed number of steps

        # Check all steps have commands
        for step in result.steps:
            assert len(step.commands) > 0

        # Check authentication step
        auth_step = result.steps[2]
        assert auth_step.rule_id == "check_authentication_md5_keychain"
        assert "authentication" in auth_step.check.lower()


class TestGoldenScenarios:
    """Test golden scenarios for BGP neighbor-down troubleshooting."""

    def test_scenario_down_state_iosxe(self, client):
        """Test BGP neighbor down state scenario for IOS-XE."""
        response = client.post(
            "/troubleshoot/bgp-neighbor",
            json={
                "vendor": "iosxe",
                "peer": "192.0.2.1",
                "iface": "GigabitEthernet0/0",
                "ttl": 1,
                "multihop": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["playbook_id"] == "bgp-neighbor-down"
        assert len(data["steps"]) == 8  # Fixed number of steps

        # Check specific steps contain expected content
        step_titles = [step["check"] for step in data["steps"]]

        # Must contain state check
        assert any("FSM state" in title for title in step_titles)

        # Must contain interface check
        assert any("interface" in title for title in step_titles)

        # Must contain TTL check
        assert any("TTL" in title for title in step_titles)

        # Must contain auth check
        assert any("authentication" in title.lower() for title in step_titles)

    def test_scenario_gtsm_mismatch_junos(self, client):
        """Test GTSM mismatch scenario for Junos."""
        response = client.post(
            "/troubleshoot/bgp-neighbor",
            json={
                "vendor": "junos",
                "peer": "192.0.2.1",
                "iface": "ge-0/0/0",
                "ttl": 1,
                "multihop": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Find GTSM step
        gtsm_step = None
        for step in data["steps"]:
            if "TTL" in step["check"] or "GTSM" in step["check"]:
                gtsm_step = step
                break

        assert gtsm_step is not None
        # Check that RFC 5082 is in the citations
        citations = gtsm_step["citations"]
        rfc_5082_found = any(citation.get("rfc") == 5082 for citation in citations)
        assert rfc_5082_found, f"RFC 5082 not found in citations: {citations}"

    def test_deterministic_order(self, client):
        """Test that BGP playbook produces identical results on multiple runs."""
        request_data = {
            "vendor": "iosxe",
            "peer": "192.0.2.1",
            "iface": "GigabitEthernet0/0",
            "ttl": 1,
            "multihop": False,
        }

        # Run twice
        response1 = client.post("/troubleshoot/bgp-neighbor", json=request_data)
        response2 = client.post("/troubleshoot/bgp-neighbor", json=request_data)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Check identical structure
        assert data1["playbook_id"] == data2["playbook_id"]
        assert len(data1["steps"]) == len(data2["steps"])

        # Check identical step order
        step_titles1 = [step["check"] for step in data1["steps"]]
        step_titles2 = [step["check"] for step in data2["steps"]]
        assert step_titles1 == step_titles2

        # Check identical step hashes
        def hash_steps(steps):
            content = "".join([step["check"] + str(step["commands"]) for step in steps])
            return hashlib.md5(content.encode()).hexdigest()

        assert hash_steps(data1["steps"]) == hash_steps(data2["steps"])

    def test_explain_playbook_endpoint(self, client):
        """Test BGP playbook explanation endpoint."""
        response = client.get(
            "/debug/explain_playbook?slug=bgp-neighbor-down&vendor=iosxe"
        )

        assert response.status_code == 200
        data = response.json()

        # The response structure may vary, so let's check for the expected fields
        assert "rules" in data
        assert len(data["rules"]) == 8

        # Check first rule
        first_rule = data["rules"][0]
        assert first_rule["id"] == "check_neighbor_fsm_state"
        assert "FSM state" in first_rule["check"]

        # Check GTSM rule has RFC5082 citation
        gtsm_rule = data["rules"][3]  # 4th rule (0-indexed)
        assert gtsm_rule["id"] == "check_ebgp_multihop_ttl_gtsm"
        citations = gtsm_rule["citations"]
        rfc_5082_found = any(citation.get("rfc") == 5082 for citation in citations)
        assert rfc_5082_found, f"RFC 5082 not found in citations: {citations}"


class TestBGPIntegration:
    """Test BGP integration with router and assembler."""

    def test_router_bgp_intent(self, client):
        """Test that BGP queries route to BGP playbook."""
        response = client.get("/debug/route?query=iosxe bgp neighbor down")

        assert response.status_code == 200
        data = response.json()

        assert data["intent"] == "TROUBLESHOOT"
        assert data["target"] == "bgp-neighbor-down"
        assert data["confidence"] > 0.5

    def test_router_bgp_keywords(self, client):
        """Test BGP keyword detection."""
        test_queries = [
            "iosxe bgp neighbor down",
            "junos bgp peer idle",
            "iosxe bgp session not established",
            "junos bgp opensent state",
        ]

        for query in test_queries:
            response = client.get(f"/debug/route?query={query}")
            assert response.status_code == 200
            data = response.json()
            assert data["intent"] == "TROUBLESHOOT"
            assert data["target"] == "bgp-neighbor-down"
