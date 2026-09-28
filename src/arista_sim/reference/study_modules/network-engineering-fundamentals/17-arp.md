# 17. ARP

**Official unit:** Network Engineering Fundamentals → Network Protocols

# Learn

ARP resolves a local IPv4 next hop to an Ethernet MAC address. A host sends an ARP request, receives a reply, and stores the IP-to-MAC mapping in its ARP table. This lets it address a frame to the default gateway.

ARP poisoning can falsely replace that mapping. ARP inspection can validate replies against DHCP snooping bindings.

# Flashcards

**What does ARP resolve?** Local IPv4 next hop to MAC.  
**What does the ARP table store?** IP-to-MAC mappings.

# Knowledge Quiz

1. Trace request, reply, and table creation.
2. Explain why ARP is required before sending to a gateway.
3. Explain the poisoning risk.

# Practical Exercise

Trace a host learning its gateway MAC and then constructing the outbound Ethernet frame.

# Mastery Check

- [ ] Explain ARP’s local next-hop role.
