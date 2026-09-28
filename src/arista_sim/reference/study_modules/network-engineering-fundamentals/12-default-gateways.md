# 12. Default Gateways

**Official unit:** Network Engineering Fundamentals → Network Layer

# Learn

A router interface uses an address from its connected subnet and acts as that subnet’s default gateway. A host sends remote-destination traffic to the gateway; the router checks its routing table and forwards when a route exists or drops when none exists.

`show ip route` displays routes; `C` identifies a directly connected network.

# Flashcards

**Default gateway role?** The local Layer 3 path toward other networks.  
**What does C mean?** Directly connected.

# Knowledge Quiz

1. Why must a gateway interface belong to the local subnet?
2. Trace host-to-remote traffic.
3. Compare router no-route behavior with switch unknown-unicast behavior.

# Practical Exercise

Map `10.1.1.1/24` and `20.1.1.1/24` router interfaces to their connected networks.

# Mastery Check

- [ ] Explain and troubleshoot the default-gateway path.
