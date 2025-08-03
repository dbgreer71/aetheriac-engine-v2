"""Golden tests for ARP anomalies playbook."""

import pytest
from ae2.api.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


def test_arp_iosxe_vendor_cmds(client):
    """Test IOS-XE ARP commands render correctly."""
    r = client.post(
        "/troubleshoot/arp-anomalies",
        json={"vendor": "iosxe", "iface": "Vlan10", "vlan": "10"},
    )
    assert r.status_code == 200
    j = r.json()

    # Check first 3 steps include expected IOS-XE commands
    steps = j.get("steps", [])
    assert len(steps) == 8

    # Step 1: SVI status
    assert any("show ip interface vlan" in cmd for cmd in steps[0].get("commands", []))

    # Step 2: ARP entry lookup
    assert any("show ip arp" in cmd for cmd in steps[1].get("commands", []))

    # Step 3: DAI status
    assert any("show ip arp inspection" in cmd for cmd in steps[2].get("commands", []))


def test_arp_junos_vendor_cmds(client):
    """Test Junos ARP commands render correctly."""
    r = client.post(
        "/troubleshoot/arp-anomalies",
        json={"vendor": "junos", "iface": "vlan.10", "vlan": "10"},
    )
    assert r.status_code == 200
    j = r.json()

    # Check first 3 steps include expected Junos commands
    steps = j.get("steps", [])
    assert len(steps) == 8

    # Step 1: SVI status
    assert any("show interfaces vlan" in cmd for cmd in steps[0].get("commands", []))

    # Step 2: ARP entry lookup
    assert any("show arp no-resolve" in cmd for cmd in steps[1].get("commands", []))


def test_arp_nxos_vendor_cmds(client):
    """Test NX-OS ARP commands render correctly."""
    r = client.post(
        "/troubleshoot/arp-anomalies",
        json={"vendor": "nxos", "iface": "Vlan20", "vlan": "20"},
    )
    assert r.status_code == 200
    j = r.json()

    # Check at least one NX-OS command renders
    steps = j.get("steps", [])
    assert len(steps) == 8

    # Step 1: SVI status
    assert any("show ip interface vlan" in cmd for cmd in steps[0].get("commands", []))


def test_arp_eos_vendor_cmds(client):
    """Test EOS ARP commands render correctly."""
    r = client.post(
        "/troubleshoot/arp-anomalies",
        json={"vendor": "eos", "iface": "Vlan30", "vlan": "30"},
    )
    assert r.status_code == 200
    j = r.json()

    # Check at least one EOS command renders
    steps = j.get("steps", [])
    assert len(steps) == 8

    # Step 1: SVI status
    assert any("show ip interface vlan" in cmd for cmd in steps[0].get("commands", []))


def test_arp_step_hash_deterministic(client):
    """Test ARP step hash is deterministic across runs."""
    # First run
    r1 = client.post(
        "/troubleshoot/arp-anomalies",
        json={"vendor": "iosxe", "iface": "Vlan10", "vlan": "10"},
    )
    assert r1.status_code == 200
    hash1 = r1.json().get("step_hash")

    # Second run
    r2 = client.post(
        "/troubleshoot/arp-anomalies",
        json={"vendor": "iosxe", "iface": "Vlan10", "vlan": "10"},
    )
    assert r2.status_code == 200
    hash2 = r2.json().get("step_hash")

    # Hashes should be identical
    assert hash1 == hash2
    assert hash1 is not None
    assert len(hash1) > 0


def test_arp_assumptions_present(client):
    """Test ARP playbook includes assumption ledger."""
    r = client.post(
        "/troubleshoot/arp-anomalies",
        json={"vendor": "iosxe", "iface": "Vlan10", "vlan": "10"},
    )
    assert r.status_code == 200
    j = r.json()

    # Check assumptions are present
    assumptions = j.get("assumptions", {})
    assert "facts" in assumptions
    assert "assumptions" in assumptions
    assert "operator_actions" in assumptions

    # Check content
    assert len(assumptions["facts"]) > 0
    assert len(assumptions["assumptions"]) > 0
    assert len(assumptions["operator_actions"]) > 0
