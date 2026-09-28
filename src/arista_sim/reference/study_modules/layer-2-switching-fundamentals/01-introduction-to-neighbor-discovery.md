# 1. Introduction to Neighbor Discovery

# Learn

IPv6 NDP discovers local devices, MAC addresses, routers, prefixes, duplicate addresses, and reachability. RS asks for routers; RA supplies gateway/prefix information; NS asks who owns an IPv6 address; NA answers; Redirect supplies better-hop information.

LLDP is a Layer 2 protocol enabled by default on Arista ports. It works without IP, routing, TCP, or UDP and discovers directly connected devices only. Advertisements populate the neighbor table and contain TLVs such as system name, port, management IP, PoE, TTL, and capabilities.

# Flashcards

**RS/RA?** Router request and reply.  
**NS/NA?** IPv6 owner request and reply.  
**LLDP scope?** Direct neighbors only.

# Knowledge Quiz

1. Compare the NDP messages.
2. Explain why LLDP works before Layer 3 configuration.
3. Name five LLDP TLVs.

# Practical Exercise

Identify which NDP message discovers a router versus an IPv6 owner, then list the information expected in an LLDP neighbor entry.

# Mastery Check

- [ ] Explain NDP messages and LLDP scope.
