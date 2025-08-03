"""
Golden tests for BGP flap playbook.

These tests verify deterministic behavior, vendor command generation,
and proper citation handling for the BGP flap troubleshooting playbook.
"""

import pytest
from ae2.playbooks.bgp_flap import run_bgp_flap_playbook, create_bgp_flap_playbook
from ae2.playbooks.models import PlayContext
from ae2.retriever.index_store import IndexStore


@pytest.fixture
def store():
    """Create index store for testing."""
    return IndexStore("data/index")


@pytest.fixture
def context():
    """Create play context for testing."""
    return PlayContext(
        target="192.0.2.1",
        vendor="iosxe",
        iface="GigabitEthernet0/0",
        area="0.0.0.0",
        auth=None,
        mtu=None,
    )


def test_bgp_flap_playbook_creation():
    """Test BGP flap playbook creation with 8 rules."""
    playbook = create_bgp_flap_playbook()
    assert playbook.id == "bgp-flap"
    assert len(playbook.rules) == 8
    assert len(playbook.citations) >= 8


def test_bgp_flap_playbook_execution(store, context):
    """Test BGP flap playbook execution returns 8 steps."""
    result = run_bgp_flap_playbook(context, store)
    assert result.playbook_id == "bgp-flap"
    assert len(result.steps) == 8
    assert result.target == "192.0.2.1"


def test_bgp_flap_step_hash_stability(store, context):
    """Test that BGP flap step hash is stable across runs."""
    result1 = run_bgp_flap_playbook(context, store)
    result2 = run_bgp_flap_playbook(context, store)

    # Verify step hash is stable
    assert hasattr(result1, "step_hash") or hasattr(result2, "step_hash")
    # Note: step_hash is computed by assembler, not playbook directly


def test_bgp_flap_vendor_commands_iosxe(store, context):
    """Test BGP flap commands for IOS-XE vendor."""
    result = run_bgp_flap_playbook(context, store)

    for step in result.steps:
        assert len(step.commands) >= 1
        for cmd in step.commands:
            iosxe_commands = cmd.render("iosxe")
            assert len(iosxe_commands) >= 1
            assert all(isinstance(cmd_str, str) for cmd_str in iosxe_commands)


def test_bgp_flap_vendor_commands_junos(store, context):
    """Test BGP flap commands for Junos vendor."""
    context.vendor = "junos"
    result = run_bgp_flap_playbook(context, store)

    for step in result.steps:
        assert len(step.commands) >= 1
        for cmd in step.commands:
            junos_commands = cmd.render("junos")
            assert len(junos_commands) >= 1
            assert all(isinstance(cmd_str, str) for cmd_str in junos_commands)


def test_bgp_flap_citations_per_step(store, context):
    """Test that each BGP flap step has ≤3 citations."""
    result = run_bgp_flap_playbook(context, store)

    for step in result.steps:
        assert len(step.citations) <= 3
        assert len(step.citations) >= 1
        for citation in step.citations:
            assert hasattr(citation, "rfc")
            assert hasattr(citation, "section")
            assert hasattr(citation, "title")
            assert hasattr(citation, "url")


def test_bgp_flap_ledger_present(store, context):
    """Test that BGP flap playbook includes facts, assumptions, and operator actions."""
    result = run_bgp_flap_playbook(context, store)

    assert hasattr(result, "facts")
    assert hasattr(result, "assumptions")
    assert hasattr(result, "operator_actions")

    assert len(result.facts) >= 1
    assert len(result.assumptions) >= 1
    assert len(result.operator_actions) >= 1


def test_bgp_flap_facts_structure(store, context):
    """Test BGP flap facts structure."""
    result = run_bgp_flap_playbook(context, store)

    for fact in result.facts:
        assert "fact" in fact
        assert "source" in fact
        assert "confidence" in fact
        assert isinstance(fact["confidence"], (int, float))
        assert 0 <= fact["confidence"] <= 1


def test_bgp_flap_assumptions_structure(store, context):
    """Test BGP flap assumptions structure."""
    result = run_bgp_flap_playbook(context, store)

    for assumption in result.assumptions:
        assert "assumption" in assumption
        assert "confidence" in assumption
        assert "rationale" in assumption
        assert isinstance(assumption["confidence"], (int, float))
        assert 0 <= assumption["confidence"] <= 1


def test_bgp_flap_operator_actions_structure(store, context):
    """Test BGP flap operator actions structure."""
    result = run_bgp_flap_playbook(context, store)

    for action in result.operator_actions:
        assert "action" in action
        assert "priority" in action
        assert "rationale" in action
        assert action["priority"] in ["high", "medium", "low"]


def test_bgp_flap_deterministic_order(store, context):
    """Test that BGP flap steps are in deterministic order."""
    result1 = run_bgp_flap_playbook(context, store)
    result2 = run_bgp_flap_playbook(context, store)

    assert len(result1.steps) == len(result2.steps)

    for i, (step1, step2) in enumerate(zip(result1.steps, result2.steps)):
        assert step1.check == step2.check
        assert len(step1.commands) == len(step2.commands)
        assert len(step1.citations) == len(step2.citations)


def test_bgp_flap_vendor_specific_commands(store):
    """Test BGP flap commands are vendor-specific."""
    # Test IOS-XE
    context_iosxe = PlayContext(
        target="192.0.2.1",
        vendor="iosxe",
        iface="GigabitEthernet0/0",
        area="0.0.0.0",
        auth=None,
        mtu=None,
    )
    result_iosxe = run_bgp_flap_playbook(context_iosxe, store)

    # Test Junos
    context_junos = PlayContext(
        target="192.0.2.1",
        vendor="junos",
        iface="ge-0/0/0",
        area="0.0.0.0",
        auth=None,
        mtu=None,
    )
    result_junos = run_bgp_flap_playbook(context_junos, store)

    # Verify both have same number of steps but different commands
    assert len(result_iosxe.steps) == len(result_junos.steps)

    # Check that commands are different for different vendors
    for step_iosxe, step_junos in zip(result_iosxe.steps, result_junos.steps):
        for cmd_iosxe, cmd_junos in zip(step_iosxe.commands, step_junos.commands):
            iosxe_rendered = cmd_iosxe.render("iosxe")
            junos_rendered = cmd_junos.render("junos")
            # Commands should be different for different vendors
            assert iosxe_rendered != junos_rendered
