# 7. Configuring VLANs Between Switches

# Learn

A trunk extends VLANs between switches.

```text
interface ethernet 3
 switchport mode trunk
 switchport trunk allowed vlan 10,20
```

Verify with `show vlan`, `show interfaces status`, and `show interfaces ethernet 3 trunk`. If VLAN 20 is not allowed, VLAN 20 endpoints on opposite switches cannot communicate even when both access ports belong to VLAN 20.

# Knowledge Quiz

1. Why is a trunk required?
2. What does the allowed list control?
3. Which command verifies trunk status and allowed VLANs?

# Practical Exercise

Build VLANs 10 and 20 on two switches, trunk their uplink, allow both VLANs, test, then remove VLAN 20 and predict the result.

# Mastery Check

- [ ] Configure and troubleshoot an inter-switch trunk.
