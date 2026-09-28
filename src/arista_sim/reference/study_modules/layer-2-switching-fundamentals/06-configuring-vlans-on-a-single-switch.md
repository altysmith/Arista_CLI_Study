# 6. Configuring VLANs on a Single Switch

# Learn

```text
vlan 10
 name blue
interface ethernet 7
 switchport mode access
 switchport access vlan 10
```

Use `show vlan`, `show interfaces status`, and `show running-config interfaces ethernet 7` to verify VLAN existence, port membership, state, duplex, speed, and configuration.

# Knowledge Quiz

1. Which command creates VLAN 10?
2. Which commands make Ethernet 7 an access port in VLAN 10?
3. Name three verification commands.

# Practical Exercise

Create VLANs 10 and 20, name them, assign endpoint ports, and verify both VLAN membership and running configuration.

# Mastery Check

- [ ] Create, assign, and verify VLANs on one switch.
