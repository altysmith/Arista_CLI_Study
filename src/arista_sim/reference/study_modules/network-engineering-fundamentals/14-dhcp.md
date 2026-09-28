# 14. DHCP

**Official unit:** Network Engineering Fundamentals → Network Protocols

# Learn

DHCP means Dynamic Host Configuration Protocol. The notes show a client Discovery broadcast followed by a server Offer. A rogue server can race the legitimate offer and redirect traffic.

DHCP snooping marks offer-facing paths trusted and drops offers received on untrusted interfaces. Its binding table records IP address, MAC address, and interface.

# Flashcards

**Discovery is sent by whom?** Client.  
**Offer is sent by whom?** Server.

# Knowledge Quiz

1. Explain the Discovery/Offer exchange.
2. Explain rogue-server risk and DHCP snooping.
3. Name binding-table fields.

# Practical Exercise

Classify a DHCP-server uplink as trusted and an endpoint access port as untrusted; predict rogue-offer handling.

# Mastery Check

- [ ] Explain DHCP behavior and snooping protection.
