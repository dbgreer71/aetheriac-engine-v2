"""
Golden tests for LACP/Port-channel down playbook.

These tests verify deterministic behavior and vendor-specific command generation
for the LACP troubleshooting playbook.
"""

import pytest
import os
from ae2.playbooks.lacp_port_channel_down import (
    run_lacp_playbook,
    create_lacp_port_channel_playbook,
    get_lacp_assumptions,
    get_lacp_operator_actions,
)
from ae2.playbooks.models import PlayContext
from ae2.retriever.index_store import IndexStore


@pytest.fixture
def index_store():
    """Create index store for testing."""
    os.environ["ENABLE_DENSE"] = "0"
    return IndexStore("data/index")


def test_lacp_iosxe_commands_minimal(index_store):
    """Test IOS-XE LACP commands are generated correctly."""
    ctx = PlayContext(
        vendor="iosxe",
        iface="Port-channel1",
        area="0.0.0.0",
        auth=None,
        mtu=1500,
    )

    result = run_lacp_playbook(ctx, index_store)

    # Verify we get exactly 8 steps
    assert len(result.steps) == 8

    # Check first few steps have expected commands
    step1 = result.steps[0]
    assert step1.rule_id == "check_bundle_members_status"
    assert "show etherchannel summary" in step1.commands
    assert "show interfaces Port-channel1" in step1.commands

    step2 = result.steps[1]
    assert step2.rule_id == "check_lacp_actor_partner_state"
    assert "show lacp neighbor Port-channel1" in step2.commands
    assert "show lacp interfaces Port-channel1" in step2.commands

    step3 = result.steps[2]
    assert step3.rule_id == "check_lacp_key_system_priority"
    assert "show lacp neighbor Port-channel1" in step3.commands


def test_lacp_junos_commands_minimal(index_store):
    """Test Junos LACP commands are generated correctly."""
    ctx = PlayContext(
        vendor="junos",
        iface="ae1",
        area="0.0.0.0",
        auth=None,
        mtu=1500,
    )

    result = run_lacp_playbook(ctx, index_store)

    # Verify we get exactly 8 steps
    assert len(result.steps) == 8

    # Check first few steps have expected commands
    step1 = result.steps[0]
    assert step1.rule_id == "check_bundle_members_status"
    assert "show lacp interfaces" in step1.commands
    assert "show interfaces ae1 extensive" in step1.commands

    step2 = result.steps[1]
    assert step2.rule_id == "check_lacp_actor_partner_state"
    assert "show lacp interfaces ae1" in step2.commands

    step3 = result.steps[2]
    assert step3.rule_id == "check_lacp_key_system_priority"
    assert "show lacp interfaces ae1" in step3.commands


def test_lacp_step_hash_stable(index_store):
    """Test that LACP step hash is stable across multiple runs."""
    ctx = PlayContext(
        vendor="iosxe",
        iface="Port-channel1",
        area="0.0.0.0",
        auth=None,
        mtu=1500,
    )

    # Run playbook twice
    result1 = run_lacp_playbook(ctx, index_store)
    result2 = run_lacp_playbook(ctx, index_store)

    # Verify deterministic step order
    assert len(result1.steps) == len(result2.steps) == 8

    # Verify step IDs are in same order
    step_ids1 = [step.rule_id for step in result1.steps]
    step_ids2 = [step.rule_id for step in result2.steps]
    assert step_ids1 == step_ids2

    # Verify commands are same
    for i, (step1, step2) in enumerate(zip(result1.steps, result2.steps)):
        assert step1.commands == step2.commands, f"Commands differ at step {i}"


def test_lacp_playbook_structure():
    """Test LACP playbook has correct structure."""
    playbook = create_lacp_port_channel_playbook()

    # Verify playbook metadata
    assert playbook.id == "lacp-port-channel-down"
    assert "lacp" in playbook.applies_to
    assert "etherchannel" in playbook.applies_to
    assert "port-channel" in playbook.applies_to

    # Verify exactly 8 rules
    assert len(playbook.rules) == 8

    # Verify rule IDs are deterministic
    expected_rule_ids = [
        "check_bundle_members_status",
        "check_lacp_actor_partner_state",
        "check_lacp_key_system_priority",
        "check_admin_mode_mismatch",
        "check_mtu_speed_duplex_mismatch",
        "check_vlan_trunk_consistency",
        "check_stp_blocking_state",
        "check_errdisable_sanity",
    ]

    actual_rule_ids = [rule.id for rule in playbook.rules]
    assert actual_rule_ids == expected_rule_ids


def test_lacp_assumptions():
    """Test LACP assumptions are properly structured."""
    assumptions = get_lacp_assumptions()

    # Verify we have assumptions
    assert len(assumptions) >= 3

    # Verify assumption structure
    for assumption in assumptions:
        assert "assumption" in assumption
        assert "basis" in assumption
        assert "impact" in assumption

    # Check for specific assumptions
    assumption_texts = [a["assumption"] for a in assumptions]
    assert any("bundle logical name" in a.lower() for a in assumption_texts)
    assert any("lacp is enabled" in a.lower() for a in assumption_texts)
    assert any("vendor supports" in a.lower() for a in assumption_texts)


def test_lacp_operator_actions():
    """Test LACP operator actions are properly structured."""
    actions = get_lacp_operator_actions()

    # Verify we have actions
    assert len(actions) >= 5

    # Verify action structure
    for action in actions:
        assert "action" in action
        assert "condition" in action
        assert "priority" in action

    # Check for specific actions
    action_texts = [a["action"] for a in actions]
    assert any("admin mode" in a.lower() for a in action_texts)
    assert any("lacp key" in a.lower() for a in action_texts)
    assert any("mtu" in a.lower() for a in action_texts)
    assert any("vlan trunk" in a.lower() for a in action_texts)
    assert any("errdisable" in a.lower() for a in action_texts)


def test_lacp_citations():
    """Test LACP playbook has proper citations."""
    playbook = create_lacp_port_channel_playbook()

    # Check that rules have citations
    for rule in playbook.rules:
        assert len(rule.citations) > 0

    # Check for IEEE 802.1AX citations
    ieee_citations = []
    for rule in playbook.rules:
        for citation in rule.citations:
            if "802.1AX" in citation.title:
                ieee_citations.append(citation)

    assert len(ieee_citations) >= 4  # Should have multiple IEEE 802.1AX citations


def test_lacp_vendor_support():
    """Test LACP playbook supports multiple vendors."""
    vendors = ["iosxe", "junos", "nxos", "eos"]

    for vendor in vendors:
        ctx = PlayContext(
            vendor=vendor,
            iface="Port-channel1",
            area="0.0.0.0",
            auth=None,
            mtu=1500,
        )

        # Should not raise exception
        result = run_lacp_playbook(ctx, IndexStore("data/index"))
        assert len(result.steps) == 8
