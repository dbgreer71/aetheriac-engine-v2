"""
Tests for TCP handshake playbook functionality.
"""

from ae2.playbooks.tcp_handshake import run_tcp_handshake_playbook
from ae2.playbooks.models import PlayContext
from ae2.retriever.index_store import IndexStore


class TestTCPHandshakePlaybook:
    """Test TCP handshake playbook functionality."""

    def test_tcp_handshake_playbook_iosxe(self):
        """Test TCP handshake playbook with IOS-XE vendor."""
        # Create context
        ctx = PlayContext(
            vendor="iosxe",
            dst="203.0.113.10",
            dport="443",
        )

        # Mock store
        store = IndexStore("data/index")

        # Run playbook
        result = run_tcp_handshake_playbook(ctx, store)

        # Verify result
        assert result.playbook_id == "tcp-handshake"
        assert len(result.steps) == 8  # Should have exactly 8 steps
        assert result.vendor == "iosxe"

        # Verify step hash is present and stable
        from ae2.playbooks.utils import compute_steps_hash

        step_hash = compute_steps_hash(result.steps)
        assert len(step_hash) > 0

        # Test deterministic behavior
        result2 = run_tcp_handshake_playbook(ctx, store)
        step_hash2 = compute_steps_hash(result2.steps)
        assert step_hash == step_hash2, "Step hash should be deterministic"

        # Verify specific steps
        assert result.steps[0].check == "Check reachability to 203.0.113.10"
        assert (
            result.steps[1].check
            == "Check if destination 203.0.113.10:443 is listening"
        )
        assert (
            result.steps[2].check
            == "Check if SYN packets are being sent to 203.0.113.10:443"
        )

        # Verify commands are vendor-specific
        assert "show arp 203.0.113.10" in result.steps[0].commands
        assert "show ip tcp connection" in result.steps[2].commands

    def test_tcp_handshake_playbook_junos(self):
        """Test TCP handshake playbook with Junos vendor."""
        # Create context
        ctx = PlayContext(
            vendor="junos",
            dst="203.0.113.10",
            dport="443",
        )

        # Mock store
        store = IndexStore("data/index")

        # Run playbook
        result = run_tcp_handshake_playbook(ctx, store)

        # Verify result
        assert result.playbook_id == "tcp-handshake"
        assert len(result.steps) == 8  # Should have exactly 8 steps
        assert result.vendor == "junos"

        # Verify Junos-specific commands
        assert "show system connections" in result.steps[1].commands
        assert "show security flow session" in result.steps[2].commands

    def test_tcp_handshake_playbook_defaults(self):
        """Test TCP handshake playbook with default values."""
        # Create context with minimal info
        ctx = PlayContext(vendor="iosxe")

        # Mock store
        store = IndexStore("data/index")

        # Run playbook
        result = run_tcp_handshake_playbook(ctx, store)

        # Verify result uses defaults
        assert result.playbook_id == "tcp-handshake"
        assert len(result.steps) == 8
        assert result.context["dst"] == "203.0.113.10"
        assert result.context["dport"] == "443"

    def test_tcp_handshake_playbook_citations(self):
        """Test that TCP playbook includes proper RFC citations."""
        # Create context
        ctx = PlayContext(
            vendor="iosxe",
            dst="203.0.113.10",
            dport="443",
        )

        # Mock store
        store = IndexStore("data/index")

        # Run playbook
        result = run_tcp_handshake_playbook(ctx, store)

        # Verify citations are present
        for step in result.steps:
            assert len(step.citations) > 0, f"Step {step.check} should have citations"

        # Verify specific RFC citations
        rfc_numbers = [
            citation.rfc for step in result.steps for citation in step.citations
        ]
        assert "1122" in rfc_numbers  # Host requirements
        assert "793" in rfc_numbers  # TCP specification
        assert "1812" in rfc_numbers  # Router requirements
        assert "3022" in rfc_numbers  # NAT
        assert "879" in rfc_numbers  # TCP MSS
        assert "1191" in rfc_numbers  # PMTUD
        assert "2979" in rfc_numbers  # Firewall transparency
