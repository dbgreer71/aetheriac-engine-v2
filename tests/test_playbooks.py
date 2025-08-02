"""
Golden tests for playbook system.

This module contains deterministic test scenarios for the OSPF neighbor-down
troubleshooting playbook to ensure consistent behavior across vendors.
"""

import pytest
from fastapi.testclient import TestClient
from ae2.api.main import app
from ae2.playbooks.models import PlayContext
from ae2.playbooks.engine import run_playbook, get_playbook_explanation
from ae2.playbooks.bgp_neighbor_down import run_bgp_playbook, get_bgp_playbook_explanation
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


class TestOSPFNeighborPlaybook:
    """Test OSPF neighbor-down troubleshooting playbook."""

    def test_playbook_creation(self):
        """Test that OSPF neighbor playbook is created correctly."""
        from ae2.playbooks.engine import create_ospf_neighbor_playbook

        playbook = create_ospf_neighbor_playbook()

        assert playbook.id == "ospf-neighbor-down"
        assert "OSPF" in playbook.applies_to
        assert len(playbook.rules) == 8  # Expected number of rules

        # Check specific rules exist
        rule_ids = [rule.id for rule in playbook.rules]
        expected_rules = [
            "check_neighbor_state",
            "check_interface_status",
            "check_ospf_interface_config",
            "check_mtu_mismatch",
            "check_authentication",
            "check_ospf_process",
            "check_network_type",
            "check_hello_dead_intervals",
        ]

        for expected_rule in expected_rules:
            assert expected_rule in rule_ids

    def test_iosxe_commands(self):
        """Test IOS-XE command rendering."""
        from ae2.vendor_ir.models import VendorCommandIR

        # Test neighbor state check
        cmd = VendorCommandIR(intent="show_neighbors", params={})
        commands = cmd.render("iosxe")
        assert commands == ["show ip ospf neighbor"]

        # Test interface check
        cmd = VendorCommandIR(
            intent="show_iface", params={"iface": "GigabitEthernet0/0"}
        )
        commands = cmd.render("iosxe")
        assert commands == ["show interface GigabitEthernet0/0"]

        # Test OSPF interface check
        cmd = VendorCommandIR(
            intent="show_ospf_iface", params={"iface": "GigabitEthernet0/0"}
        )
        commands = cmd.render("iosxe")
        assert commands == ["show ip ospf interface GigabitEthernet0/0"]

    def test_junos_commands(self):
        """Test Junos command rendering."""
        from ae2.vendor_ir.models import VendorCommandIR

        # Test neighbor state check
        cmd = VendorCommandIR(intent="show_neighbors", params={})
        commands = cmd.render("junos")
        assert commands == ["show ospf neighbor"]

        # Test interface check
        cmd = VendorCommandIR(intent="show_iface", params={"iface": "ge-0/0/0"})
        commands = cmd.render("junos")
        assert commands == ["show interfaces ge-0/0/0 terse"]

        # Test OSPF interface check
        cmd = VendorCommandIR(intent="show_ospf_iface", params={"iface": "ge-0/0/0"})
        commands = cmd.render("junos")
        assert commands == ["show ospf interface ge-0/0/0 detail"]

    def test_playbook_execution_iosxe(self, store):
        """Test OSPF neighbor playbook execution for IOS-XE."""
        if store is None:
            pytest.skip("Index store not available")

        ctx = PlayContext(
            vendor="iosxe",
            iface="GigabitEthernet0/0",
            area="0.0.0.0",
            auth="md5",
            mtu=1500,
        )

        result = run_playbook("ospf-neighbor-down", ctx, store)

        assert result.playbook_id == "ospf-neighbor-down"
        assert len(result.steps) == 8  # All rules should execute

        # Check first step (neighbor state check)
        first_step = result.steps[0]
        assert first_step.rule_id == "check_neighbor_state"
        assert "show ip ospf neighbor" in first_step.commands

        # Check MTU step has multiple commands
        mtu_step = next(
            step for step in result.steps if step.rule_id == "check_mtu_mismatch"
        )
        assert len(mtu_step.commands) >= 2  # show_mtu + show_ospf_iface

    def test_playbook_execution_junos(self, store):
        """Test OSPF neighbor playbook execution for Junos."""
        if store is None:
            pytest.skip("Index store not available")

        ctx = PlayContext(
            vendor="junos", iface="ge-0/0/0", area="0.0.0.0", auth="md5", mtu=1500
        )

        result = run_playbook("ospf-neighbor-down", ctx, store)

        assert result.playbook_id == "ospf-neighbor-down"
        assert len(result.steps) == 8

        # Check first step uses Junos commands
        first_step = result.steps[0]
        assert first_step.rule_id == "check_neighbor_state"
        assert "show ospf neighbor" in first_step.commands

        # Check interface step uses Junos syntax
        iface_step = next(
            step for step in result.steps if step.rule_id == "check_interface_status"
        )
        assert "show interfaces ge-0/0/0 terse" in iface_step.commands

    def test_playbook_explanation(self):
        """Test playbook explanation endpoint."""
        explanation = get_playbook_explanation("ospf-neighbor-down", "iosxe")

        assert explanation["playbook_id"] == "ospf-neighbor-down"
        assert explanation["vendor"] == "iosxe"
        assert len(explanation["rules"]) == 8

        # Check first rule explanation
        first_rule = explanation["rules"][0]
        assert first_rule["rule_id"] == "check_neighbor_state"
        assert "show ip ospf neighbor" in first_rule["commands"]
        assert len(first_rule["citations"]) > 0


class TestGoldenScenarios:
    """Golden test scenarios for deterministic behavior."""

    def test_scenario_1_down_state(self, client):
        """Golden scenario 1: Neighbor down (no adjacency)."""
        ctx = {
            "vendor": "iosxe",
            "iface": "GigabitEthernet0/0",
            "area": "0.0.0.0",
            "auth": None,
            "mtu": None,
        }

        response = client.post("/troubleshoot/ospf-neighbor", json=ctx)
        assert response.status_code == 200

        data = response.json()
        assert data["playbook_id"] == "ospf-neighbor-down"
        assert len(data["steps"]) == 8
        assert data["debug"]["vendor"] == "iosxe"

        # Check first step has neighbor check command
        first_step = data["steps"][0]
        assert first_step["rule_id"] == "check_neighbor_state"
        assert "show ip ospf neighbor" in first_step["commands"]

    def test_scenario_2_exstart_loop(self, client):
        """Golden scenario 2: EXSTART loop (MTU mismatch)."""
        ctx = {
            "vendor": "junos",
            "iface": "ge-0/0/0",
            "area": "0.0.0.0",
            "auth": None,
            "mtu": 9000,  # Jumbo frames
        }

        response = client.post("/troubleshoot/ospf-neighbor", json=ctx)
        assert response.status_code == 200

        data = response.json()
        assert data["playbook_id"] == "ospf-neighbor-down"

        # Find MTU mismatch step
        mtu_step = next(
            step for step in data["steps"] if step["rule_id"] == "check_mtu_mismatch"
        )
        assert "show interfaces ge-0/0/0 | match MTU" in mtu_step["commands"]
        assert "show ospf interface ge-0/0/0 detail" in mtu_step["commands"]

    def test_scenario_3_mtu_mismatch(self, client):
        """Golden scenario 3: MTU mismatch detection."""
        ctx = {
            "vendor": "iosxe",
            "iface": "GigabitEthernet0/1",
            "area": "0.0.0.0",
            "auth": None,
            "mtu": 1500,
        }

        response = client.post("/troubleshoot/ospf-neighbor", json=ctx)
        assert response.status_code == 200

        data = response.json()

        # Check MTU step has fix and verify
        mtu_step = next(
            step for step in data["steps"] if step["rule_id"] == "check_mtu_mismatch"
        )
        assert mtu_step["fix"] is not None
        assert mtu_step["verify"] is not None
        assert "MTU" in mtu_step["fix"]

    def test_scenario_4_auth_mismatch(self, client):
        """Golden scenario 4: Authentication mismatch."""
        ctx = {
            "vendor": "junos",
            "iface": "ge-0/0/1",
            "area": "0.0.0.0",
            "auth": "md5",
            "mtu": 1500,
        }

        response = client.post("/troubleshoot/ospf-neighbor", json=ctx)
        assert response.status_code == 200

        data = response.json()

        # Check auth step has authentication commands
        auth_step = next(
            step for step in data["steps"] if step["rule_id"] == "check_authentication"
        )
        assert (
            "show ospf interface ge-0/0/1 detail | match Authentication"
            in auth_step["commands"]
        )
        assert auth_step["fix"] is not None
        assert "authentication" in auth_step["fix"].lower()

    def test_explain_playbook_endpoint(self, client):
        """Test the explain playbook debug endpoint."""
        response = client.get(
            "/debug/explain_playbook",
            params={"slug": "ospf-neighbor-down", "vendor": "iosxe"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["playbook_id"] == "ospf-neighbor-down"
        assert data["vendor"] == "iosxe"
        assert len(data["rules"]) == 8

        # Check rule structure
        first_rule = data["rules"][0]
        assert "rule_id" in first_rule
        assert "if_condition" in first_rule
        assert "check" in first_rule
        assert "commands" in first_rule
        assert "citations" in first_rule

    def test_deterministic_behavior(self, client):
        """Test that playbook execution is deterministic."""
        ctx = {
            "vendor": "iosxe",
            "iface": "GigabitEthernet0/0",
            "area": "0.0.0.0",
            "auth": "md5",
            "mtu": 1500,
        }

        # Run twice with same context
        response1 = client.post("/troubleshoot/ospf-neighbor", json=ctx)
        response2 = client.post("/troubleshoot/ospf-neighbor", json=ctx)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Results should be identical
        assert data1 == data2

        # Check step order is consistent
        step_ids1 = [step["rule_id"] for step in data1["steps"]]
        step_ids2 = [step["rule_id"] for step in data2["steps"]]
        assert step_ids1 == step_ids2


class TestBGPNeighborPlaybook:
    """Test BGP neighbor-down troubleshooting playbook."""

    def test_playbook_creation(self):
        """Test that BGP neighbor playbook is created correctly."""
        from ae2.playbooks.bgp_neighbor_down import create_bgp_neighbor_playbook

        playbook = create_bgp_neighbor_playbook()

        assert playbook.id == "bgp-neighbor-down"
        assert "BGP" in playbook.applies_to
        assert len(playbook.rules) == 8  # Expected number of rules

        # Check specific rules exist
        rule_ids = [rule.id for rule in playbook.rules]
        expected_rules = [
            "check_session_state",
            "check_transport_reachability",
            "check_authentication",
            "check_ttl_gtsm",
            "check_timers",
            "check_afi_safi",
            "check_policy",
            "check_interface_link",
        ]

        for expected_rule in expected_rules:
            assert expected_rule in rule_ids

    def test_neighbor_down_basic_iosxe(self, client):
        """Test basic BGP neighbor down scenario for IOS-XE."""
        params = {
            "vendor": "iosxe",
            "peer": "192.0.2.1",
            "iface": "GigabitEthernet0/0",
        }

        response = client.post("/troubleshoot/bgp-neighbor", json=params)
        assert response.status_code == 200

        result = response.json()
        assert result["playbook_id"] == "bgp-neighbor-down"
        assert len(result["steps"]) == 8  # All rules should be included
        assert result["debug"]["vendor"] == "iosxe"
        assert result["debug"]["peer"] == "192.0.2.1"

        # Check first step has expected content
        first_step = result["steps"][0]
        assert first_step["rule_id"] == "check_session_state"
        assert "BGP neighbor session state" in first_step["check"]
        assert len(first_step["commands"]) > 0
        assert len(first_step["citations"]) > 0

    def test_auth_mismatch_iosxe(self, client):
        """Test BGP authentication mismatch scenario for IOS-XE."""
        params = {
            "vendor": "iosxe",
            "peer": "192.0.2.1",
            "iface": "GigabitEthernet0/0",
        }

        response = client.post("/troubleshoot/bgp-neighbor", json=params)
        assert response.status_code == 200

        result = response.json()
        
        # Find authentication step
        auth_step = None
        for step in result["steps"]:
            if step["rule_id"] == "check_authentication":
                auth_step = step
                break
        
        assert auth_step is not None
        assert "authentication" in auth_step["check"].lower()
        assert "TCP-MD5" in auth_step["check"]
        assert len(auth_step["commands"]) >= 2
        assert len(auth_step["citations"]) > 0

    def test_gtsm_iosxe(self, client):
        """Test BGP GTSM/TTL scenario for IOS-XE."""
        params = {
            "vendor": "iosxe",
            "peer": "192.0.2.1",
            "iface": "GigabitEthernet0/0",
        }

        response = client.post("/troubleshoot/bgp-neighbor", json=params)
        assert response.status_code == 200

        result = response.json()
        
        # Find TTL/GTSM step
        ttl_step = None
        for step in result["steps"]:
            if step["rule_id"] == "check_ttl_gtsm":
                ttl_step = step
                break
        
        assert ttl_step is not None
        assert "TTL" in ttl_step["check"] or "GTSM" in ttl_step["check"]
        assert len(ttl_step["commands"]) >= 2
        assert len(ttl_step["citations"]) > 0

    def test_policy_block_junos(self, client):
        """Test BGP policy blocking scenario for Junos."""
        params = {
            "vendor": "junos",
            "peer": "192.0.2.1",
            "iface": "ge-0/0/0",
        }

        response = client.post("/troubleshoot/bgp-neighbor", json=params)
        assert response.status_code == 200

        result = response.json()
        
        # Find policy step
        policy_step = None
        for step in result["steps"]:
            if step["rule_id"] == "check_policy":
                policy_step = step
                break
        
        assert policy_step is not None
        assert "policies" in policy_step["result"].lower()
        assert "import/export" in policy_step["result"]
        assert len(policy_step["commands"]) >= 2
        assert len(policy_step["citations"]) > 0

    def test_deterministic_order(self, client):
        """Test that BGP playbook produces deterministic ordered steps."""
        params = {
            "vendor": "iosxe",
            "peer": "192.0.2.1",
            "iface": "GigabitEthernet0/0",
        }

        response1 = client.post("/troubleshoot/bgp-neighbor", json=params)
        response2 = client.post("/troubleshoot/bgp-neighbor", json=params)

        assert response1.status_code == 200
        assert response2.status_code == 200

        result1 = response1.json()
        result2 = response2.json()

        # Should have same number of steps
        assert len(result1["steps"]) == len(result2["steps"])

        # Should have same step IDs in same order
        steps1 = [step["rule_id"] for step in result1["steps"]]
        steps2 = [step["rule_id"] for step in result2["steps"]]
        assert steps1 == steps2

        # Verify expected order
        expected_order = [
            "check_session_state",
            "check_transport_reachability", 
            "check_authentication",
            "check_ttl_gtsm",
            "check_timers",
            "check_afi_safi",
            "check_policy",
            "check_interface_link",
        ]
        assert steps1 == expected_order
