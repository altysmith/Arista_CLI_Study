# 4. DHCP Snooping

# Learn

A rogue DHCP server can answer a Discovery first and redirect client traffic. DHCP snooping makes the switch inspect DHCP messages. Trusted interfaces may receive Offers; Offers on untrusted interfaces are dropped.

```text
ip dhcp snooping
ip dhcp snooping vlan 10
```

The feature is not enabled by default. Its binding table records IP address, MAC address, and interface.

# Knowledge Quiz

1. Explain the rogue-server attack.
2. Compare trusted and untrusted ports.
3. Name the binding-table fields.

# Practical Exercise

Trust the legitimate server/uplink path, leave endpoint ports untrusted, and predict handling of a rogue Offer.

# Mastery Check

- [ ] Configure and explain DHCP snooping protection.
