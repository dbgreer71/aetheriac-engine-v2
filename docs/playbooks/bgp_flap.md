# BGP Flap Troubleshooting Playbook

## Overview

The BGP Flap troubleshooting playbook provides deterministic troubleshooting for BGP neighbor flap issues. This playbook follows RFC 4271 (BGP-4) and RFC 5082 (GTSM) standards to systematically identify and resolve BGP session instability.

## Playbook Steps

### Step 1: Check Neighbor Flap History
**Check:** Check BGP neighbor flap history and last reset reason
**Commands:**
- **IOS-XE:** `show ip bgp neighbors {neighbor} | include flap`
- **Junos:** `show bgp neighbor {neighbor} | match flap`

**Citations:** RFC 4271 Section 6.5
**Interpretation:** Review recent flap patterns and identify root causes of previous session drops.

### Step 2: Verify Keepalive/Hold Timers
**Check:** Verify keepalive and hold timer configuration
**Commands:**
- **IOS-XE:** `show ip bgp neighbors {neighbor} | include timers`
- **Junos:** `show bgp neighbor {neighbor} | match timers`

**Citations:** RFC 4271 Section 10
**Interpretation:** Ensure timer configurations are consistent between peers.

### Step 3: Check GTSM/TTL Configuration
**Check:** Check GTSM/TTL configuration
**Commands:**
- **IOS-XE:** `show ip bgp neighbors {neighbor} | include ttl`
- **Junos:** `show bgp neighbor {neighbor} | match ttl`

**Citations:** RFC 5082 Section 3
**Interpretation:** Verify TTL values are appropriate and not causing adjacency drops.

### Step 4: Check Policy Churn
**Check:** Check import/export policy changes
**Commands:**
- **IOS-XE:** `show ip bgp neighbors {neighbor} advertised-routes`
- **Junos:** `show bgp neighbor {neighbor} advertised-routes`

**Citations:** RFC 7454 Section 5.1
**Interpretation:** Monitor policy changes that may destabilize BGP sessions.

### Step 5: Monitor Prefix Churn
**Check:** Monitor prefix update/withdraw frequency
**Commands:**
- **IOS-XE:** `show ip bgp neighbors {neighbor} received-routes`
- **Junos:** `show bgp neighbor {neighbor} received-routes`

**Citations:** RFC 7454 Section 2.1
**Interpretation:** Identify excessive prefix updates/withdraws indicating upstream issues.

### Step 6: Check Transport Health
**Check:** Check TCP transport health and retransmissions
**Commands:**
- **IOS-XE:** `show ip bgp neighbors {neighbor} | include transport`
- **Junos:** `show bgp neighbor {neighbor} | match transport`

**Citations:** RFC 4271 Section 6.8
**Interpretation:** Verify underlying TCP transport is healthy.

### Step 7: Check Dampening Effect
**Check:** Check route dampening configuration and status
**Commands:**
- **IOS-XE:** `show ip bgp dampening`
- **Junos:** `show bgp damping`

**Citations:** RFC 7454 Section 2.3
**Interpretation:** Ensure dampening is not blocking legitimate routes.

### Step 8: Monitor Device Load
**Check:** Monitor device CPU/memory during flap events
**Commands:**
- **IOS-XE:** `show processes cpu`
- **Junos:** `show system processes cpu`

**Citations:** RFC 7454 Section 1
**Interpretation:** Check for resource constraints during BGP processing.

## Assumptions

- BGP neighbor is configured and should be stable
- Network connectivity between peers is functional
- Device has sufficient resources for BGP processing
- Policy configuration is intentional and correct
- Upstream network changes are legitimate

## Operator Actions

1. **High Priority:** Check BGP neighbor status and flap history
2. **High Priority:** Verify keepalive/hold timer configuration
3. **Medium Priority:** Check GTSM/TTL configuration
4. **Medium Priority:** Monitor policy changes and their impact
5. **Medium Priority:** Investigate prefix update/withdraw patterns
6. **High Priority:** Check transport layer health
7. **Low Priority:** Review dampening configuration
8. **Medium Priority:** Monitor device resource utilization

## Notes

- This playbook does not claim to diagnose specific device states
- Results should be interpreted in context of network topology
- Vendor-specific commands may vary by platform version
- Always verify findings with additional diagnostic commands
