# 10. Configuring Inter-VLAN Routing with SVIs

# Learn

An SVI is a logical Layer 3 interface on a multilayer switch and normally serves as a VLAN’s default gateway.

```text
ip routing
interface vlan 10
 ip address 10.1.1.1/24
 no shutdown
interface vlan 20
 ip address 20.1.1.1/24
 no shutdown
```

Create the VLANs and trunk the L2-to-MLS connection. The routing table then contains connected routes through SVI 10 and SVI 20.

# Knowledge Quiz

1. What does `ip routing` enable?
2. Why must the VLAN and SVI both exist?
3. What is the SVI’s endpoint role?

# Practical Exercise

Create VLANs 10/20, trunk the uplink, configure both SVIs, enable routing, and verify inter-VLAN reachability.

# Mastery Check

- [ ] Configure and verify SVI routing.
