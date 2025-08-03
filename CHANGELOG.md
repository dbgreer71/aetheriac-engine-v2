# Changelog

## [M2.1] ARP anomalies + multi-vendor IR (iosxe/junos/nxos/eos)
- Router: ARP signals, state terms, confidence ≥ 0.60
- Playbook: 8 deterministic steps, RFC 826/5227/802.1Q citations
- Vendor IR: complete ARP intents for 4 vendors
- Assumption ledger included in results
- Eval: added T56–T60, overall 55/60 pass

## [M1.5] LACP/Port-channel troubleshooting
- Added LACP port-channel-down playbook with 8 deterministic steps
- Vendor IR: IOS-XE, Junos, NX-OS, EOS support
- Router: LACP term detection and confidence scoring
- Evaluation: T47-T50 cases added

## [M1.4] OSPF neighbor troubleshooting
- Added OSPF neighbor-down playbook with 8 deterministic steps
- Vendor IR: IOS-XE and Junos support
- Router: OSPF term detection and confidence scoring
- Evaluation: T31-T40 cases added

## [M1.3] TCP handshake troubleshooting
- Added TCP handshake playbook with 8 deterministic steps
- Vendor IR: IOS-XE and Junos support
- Router: TCP term detection and confidence scoring
- Evaluation: T7-T30 cases added

## [M1.2] BGP neighbor troubleshooting
- Added BGP neighbor-down playbook with 8 deterministic steps
- Vendor IR: IOS-XE and Junos support
- Router: BGP term detection and confidence scoring
- Evaluation: T3-T6 cases added

## [M1.1] Initial release
- Core router and assembler functionality
- RFC definition and concept card support
- Hybrid retrieval with BM25 + TF-IDF
- Basic evaluation framework
