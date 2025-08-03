"""
Golden tests for ARP anomalies playbook.

These tests verify deterministic behavior and vendor-specific command generation
for the ARP troubleshooting playbook.
"""

import pytest
import os
from ae2.playbooks.arp_anomalies import (
    run_arp_playbook,
    create_arp_anomalies_playbook,
    get_arp_assumptions,
    get_arp_operator_actions,
)
from ae2.playbooks.models import PlayContext
from ae2.retriever.index_store import IndexStore


@pytest.fixture
def index_store():
    """Create index store for testing."""
    os.environ["ENABLE_DENSE"] = "0"
    return IndexStore("data/index")


def test_arp_iosxe_vendor_cmds(index_store):
    """Test IOS-XE ARP commands are generated correctly."""
    ctx = PlayContext(
        vendor="iosxe",
        iface="192.0.2.10",
        area="0.0.0.0",
        auth=None,
        mtu=1500,
    )

    result = run_arp_playbook(ctx, index_store)

    # Verify we get exactly 8 steps
    assert len(result.steps) == 8

    # Check first few steps have expected commands
    step1 = result.steps[0]
    assert step1.rule_id == "check_svi_status"
    assert "show ip interface vlan 192.0.2.10" in step1.commands

    step2 = result.steps[1]
    assert step2.rule_id == "check_arp_entry_lookup"
    assert "show ip arp 192.0.2.10" in step2.commands

    step3 = result.steps[2]
    assert step3.rule_id == "check_arp_table_health"
    assert "show ip arp inspection" in step3.commands


def test_arp_junos_vendor_cmds(index_store):
    """Test Junos ARP commands are generated correctly."""
    ctx = PlayContext(
        vendor="junos",
        iface="192.0.2.10",
        area="0.0.0.0",
        auth=None,
        mtu=1500,
    )

    result = run_arp_playbook(ctx, index_store)

    # Verify we get exactly 8 steps
    assert len(result.steps) == 8

    # Check first few steps have expected commands
    step1 = result.steps[0]
    assert step1.rule_id == "check_svi_status"
    assert "show interfaces vlan.192.0.2.10 terse" in step1.commands

    step2 = result.steps[1]
    assert step2.rule_id == "check_arp_entry_lookup"
    assert "show arp no-resolve | match 192.0.2.10" in step2.commands

    step3 = result.steps[2]
    assert step3.rule_id == "check_arp_table_health"
    assert "show ip arp inspection" in step3.commands


def test_arp_step_hash_deterministic(index_store):
    """Test that ARP step hash is stable across multiple runs."""
    ctx = PlayContext(
        vendor="iosxe",
        iface="192.0.2.10",
        area="0.0.0.0",
        auth=None,
        mtu=1500,
    )

    # Run playbook twice
    result1 = run_arp_playbook(ctx, index_store)
    result2 = run_arp_playbook(ctx, index_store)

    # Verify deterministic step order
    assert len(result1.steps) == len(result2.steps) == 8

    # Verify step IDs are in same order
    step_ids1 = [step.rule_id for step in result1.steps]
    step_ids2 = [step.rule_id for step in result2.steps]
    assert step_ids1 == step_ids2

    # Verify commands are same
    for i, (step1, step2) in enumerate(zip(result1.steps, result2.steps)):
        assert step1.commands == step2.commands, f"Commands differ at step {i}"


def test_arp_playbook_structure():
    """Test ARP playbook has correct structure."""
    playbook = create_arp_anomalies_playbook()

    # Verify playbook metadata
    assert playbook.id == "arp-anomalies"
    assert "arp" in playbook.applies_to
    assert "proxy-arp" in playbook.applies_to
    assert "dai" in playbook.applies_to

    # Verify exactly 8 rules
    assert len(playbook.rules) == 8

    # Verify rule IDs are deterministic
    expected_rule_ids = [
        "check_svi_status",
        "check_arp_entry_lookup",
        "check_arp_table_health",
        "check_proxy_arp_config",
        "check_mac_table_lookup",
        "check_arp_gratuitous_signals",
        "check_arp_aging_timers",
        "check_port_security_counters",
    ]

    actual_rule_ids = [rule.id for rule in playbook.rules]
    assert actual_rule_ids == expected_rule_ids


def test_arp_assumptions():
    """Test ARP assumptions are properly structured."""
    assumptions = get_arp_assumptions()

    # Verify we have assumptions
    assert len(assumptions) >= 4

    # Verify assumption structure
    for assumption in assumptions:
        assert "assumption" in assumption
        assert "basis" in assumption
        assert "impact" in assumption

    # Check for specific assumptions
    assumption_texts = [a["assumption"] for a in assumptions]
    assert any("ip belongs to vlan" in a.lower() for a in assumption_texts)
    assert any("arp is enabled" in a.lower() for a in assumption_texts)
    assert any("vendor supports" in a.lower() for a in assumption_texts)
    assert any("svi interface exists" in a.lower() for a in assumption_texts)


def test_arp_operator_actions():
    """Test ARP operator actions are properly structured."""
    actions = get_arp_operator_actions()

    # Verify we have actions
    assert len(actions) >= 7

    # Verify action structure
    for action in actions:
        assert "action" in action
        assert "condition" in action
        assert "priority" in action

    # Check for specific actions
    action_texts = [a["action"] for a in actions]
    assert any("arp entry stale" in a.lower() for a in action_texts)
    assert any("dai drops" in a.lower() for a in action_texts)
    assert any("proxy arp mismatch" in a.lower() for a in action_texts)
    assert any("mac/arp correlation" in a.lower() for a in action_texts)
    assert any("gratuitous arp" in a.lower() for a in action_texts)
    assert any("aging timers" in a.lower() for a in action_texts)
    assert any("port security" in a.lower() for a in action_texts)


def test_arp_citations():
    """Test ARP playbook has proper citations."""
    playbook = create_arp_anomalies_playbook()

    # Check that rules have citations
    for rule in playbook.rules:
        assert len(rule.citations) > 0

    # Check for RFC 826 citations
    rfc_826_citations = []
    for rule in playbook.rules:
        for citation in rule.citations:
            if citation.rfc == 826:
                rfc_826_citations.append(citation)

    assert len(rfc_826_citations) >= 6  # Should have multiple RFC 826 citations

    # Check for RFC 5227 citations
    rfc_5227_citations = []
    for rule in playbook.rules:
        for citation in rule.citations:
            if citation.rfc == 5227:
                rfc_5227_citations.append(citation)

    assert len(rfc_5227_citations) >= 1  # Should have at least one RFC 5227 citation


def test_arp_vendor_support():
    """Test ARP playbook supports multiple vendors."""
    vendors = ["iosxe", "junos", "nxos", "eos"]

    for vendor in vendors:
        ctx = PlayContext(
            vendor=vendor,
            iface="192.0.2.10",
            area="0.0.0.0",
            auth=None,
            mtu=1500,
        )

        # Should not raise exception
        result = run_arp_playbook(ctx, IndexStore("data/index"))
        assert len(result.steps) == 8
