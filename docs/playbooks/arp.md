# ARP Anomalies Playbook

**Endpoint**: `POST /troubleshoot/arp-anomalies`
**Auto**: `POST /query?mode=auto` (router detects ARP + state terms)

## Overview

The ARP anomalies playbook provides deterministic troubleshooting for Address Resolution Protocol issues across multiple vendors. It includes 8 deterministic steps covering SVI status, ARP entry lookup, DAI/inspection health, proxy ARP configuration, MAC/ARP correlation, gratuitous ARP signals, aging timers, and port security counters.

## Examples

### Auto (IOS-XE)
```bash
curl -s -X POST "http://localhost:8001/query?mode=auto" \
  -H "Content-Type: application/json" \
  -d '{"query":"iosxe arp incomplete 192.0.2.10 vlan 10"}' | jq
```

### Direct endpoint (NX-OS)
```bash
curl -s -X POST "http://localhost:8001/troubleshoot/arp-anomalies" \
  -H "Content-Type: application/json" \
  -d '{"vendor":"nxos","iface":"Vlan20","vlan":"20"}' | jq
```

### Junos ARP duplicate
```bash
curl -s -X POST "http://localhost:8001/query?mode=auto" \
  -H "Content-Type: application/json" \
  -d '{"query":"junos duplicate arp on vlan.20 for 198.51.100.7"}' | jq
```

### EOS DAI drops
```bash
curl -s -X POST "http://localhost:8001/troubleshoot/arp-anomalies" \
  -H "Content-Type: application/json" \
  -d '{"vendor":"eos","iface":"Vlan40","vlan":"40"}' | jq
```

## Outputs

- **steps**: 8 deterministic troubleshooting steps
- **step_hash**: Deterministic hash for identical inputs
- **citations**: RFC 826 (ARP), RFC 5227 (ARP Probe), IEEE 802.1Q (VLAN)
- **assumptions**: Comprehensive ledger with facts, assumptions, and operator actions

## Supported Vendors

- **IOS-XE**: `show ip arp vlan 10`, `show ip arp inspection`, `show mac address-table`
- **Junos**: `show arp no-resolve`, `show interfaces vlan.10 terse`, `show ethernet-switching table`
- **NX-OS**: `show ip arp vrf all | inc 192.0.2.10`, `show ip arp inspection`
- **EOS**: `show ip arp | include 192.0.2.10`, `show ip arp inspection`

## Router Detection

The router automatically detects ARP troubleshooting queries when they contain:
- ARP terms: "arp", "proxy-arp", "gratuitous", "garp", "dai", "inspection"
- State terms: "incomplete", "duplicate", "poison", "drops", "stale"
- Vendor + ARP + state terms trigger confidence ≥ 0.60

## Assumption Ledger

The playbook includes a comprehensive assumption ledger:

**Facts**:
- Vendor commands are guidance; no device-state claims
- DAI/Inspection may drop ARP frames if bindings absent

**Assumptions**:
- User can run show commands on target device
- If VLAN unspecified, SVI or trunk context applies

**Operator Actions**:
- Collect outputs from steps 1–3; note MAC/IP/VLAN alignment
- If DAI drops suspected, verify DHCP Snooping bindings
