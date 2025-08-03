# OSPF LSA Storm Troubleshooting Playbook

## Overview

The OSPF LSA Storm troubleshooting playbook provides deterministic troubleshooting for OSPF LSA storm issues. This playbook follows RFC 2328 (OSPF Version 2) standards to systematically identify and resolve excessive LSA generation and flooding.

## Playbook Steps

### Step 1: Check LSA Retransmit Queues
**Check:** Check LSA retransmit queues and queue depths
**Commands:**
- **IOS-XE:** `show ip ospf retransmission-list`
- **Junos:** `show ospf retransmit-list`

**Citations:** RFC 2328 Section 13
**Interpretation:** Identify overflowing retransmit queues indicating storm conditions.

### Step 2: Verify LSA Pacing/Throttle
**Check:** Verify LSA pacing and throttle configuration
**Commands:**
- **IOS-XE:** `show ip ospf interface | include pacing`
- **Junos:** `show ospf interface | match pacing`

**Citations:** RFC 2328 Section 16.1
**Interpretation:** Ensure proper LSA pacing prevents storm propagation.

### Step 3: Check Max-LSA Limits
**Check:** Check Max-LSA configuration and limits
**Commands:**
- **IOS-XE:** `show ip ospf max-lsa`
- **Junos:** `show ospf max-lsa`

**Citations:** RFC 2328 Section 12.4
**Interpretation:** Verify limits protect against excessive LSAs.

### Step 4: Monitor DR/BDR Stability
**Check:** Monitor DR/BDR election stability
**Commands:**
- **IOS-XE:** `show ip ospf neighbor | include DR`
- **Junos:** `show ospf neighbor | match DR`

**Citations:** RFC 2328 Section 9.1
**Interpretation:** Check for DR/BDR churn causing LSA storms.

### Step 5: Identify Misconfigurations
**Check:** Identify misconfigurations generating LSAs
**Commands:**
- **IOS-XE:** `show ip ospf database | include generator`
- **Junos:** `show ospf database | match generator`

**Citations:** RFC 2328 Section 12.5
**Interpretation:** Find misconfigurations generating excess LSAs.

### Step 6: Analyze LSA Type Distribution
**Check:** Analyze LSA type distribution (1/2/3/5/7)
**Commands:**
- **IOS-XE:** `show ip ospf database | include Type`
- **Junos:** `show ospf database | match Type`

**Citations:** RFC 2328 Section 12
**Interpretation:** Identify abnormal LSA type patterns.

### Step 7: Check SPF Throttle/Timers
**Check:** Check SPF throttle and timer configuration
**Commands:**
- **IOS-XE:** `show ip ospf spf-throttle`
- **Junos:** `show ospf spf-throttle`

**Citations:** RFC 2328 Section 16.1
**Interpretation:** Verify SPF throttle prevents excessive computation.

### Step 8: Check Interface Errors/Drops
**Check:** Check interface errors and drops
**Commands:**
- **IOS-XE:** `show interface | include errors`
- **Junos:** `show interface | match errors`

**Citations:** RFC 2328 Section 8.2
**Interpretation:** Identify interface issues triggering LSA floods.

## Assumptions

- OSPF network should be stable under normal conditions
- Network topology is relatively stable
- Device has sufficient resources for OSPF processing
- OSPF configuration is intentional and correct
- Interface errors are not normal

## Operator Actions

1. **High Priority:** Check LSA retransmit queues and clear if needed
2. **High Priority:** Verify LSA pacing and throttle configuration
3. **Medium Priority:** Check Max-LSA limits and adjust if necessary
4. **Medium Priority:** Monitor DR/BDR election stability
5. **High Priority:** Identify and correct misconfigurations
6. **Medium Priority:** Analyze LSA type distribution patterns
7. **Medium Priority:** Check SPF throttle configuration
8. **High Priority:** Resolve interface errors and drops

## Notes

- This playbook does not claim to diagnose specific device states
- Results should be interpreted in context of network topology
- Vendor-specific commands may vary by platform version
- Always verify findings with additional diagnostic commands
- LSA storms can be caused by legitimate network changes
