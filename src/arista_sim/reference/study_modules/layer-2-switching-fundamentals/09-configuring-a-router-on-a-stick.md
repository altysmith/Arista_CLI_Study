# 9. Configuring a Router on a Stick

# Learn

Prepare switch VLANs, endpoint access ports, and the router-facing trunk. On the router, enable the physical interface and create one subinterface/default gateway per VLAN.

```text
interface ethernet 3.10
 encapsulation dot1q vlan 10
 ip address 10.1.1.1/24
interface ethernet 3.20
 encapsulation dot1q vlan 20
 ip address 20.1.1.1/24
```

The routing table maps each subnet to its subinterface.

# Knowledge Quiz

1. What must be configured on the switch first?
2. What binds a subinterface to a VLAN?
3. What role does each subinterface IP serve?

# Practical Exercise

Configure VLAN 10 and 20 gateways on router subinterfaces and verify both connected routes.

# Mastery Check

- [ ] Configure and verify router-on-a-stick.
