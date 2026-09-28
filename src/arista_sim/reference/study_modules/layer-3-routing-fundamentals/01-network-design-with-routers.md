# 1. Network Design with Routers

**Official unit:** Layer 3 Routing Fundamentals → Introduction to Routers

# Learn

Routers are Layer 3 devices. Each router interface connects to a different IP network and receives an address from that subnet. The interface can serve as the subnet’s default gateway.

A router’s routing table contains destination IP networks. `show ip route` displays it, and `C` marks a directly connected route. When a destination exists in the table, the router forwards toward it; without a route, the router drops the packet rather than flooding it.

Routers connect LANs, connect LANs or data centers to WANs, and provide inter-VLAN routing. A design may use different technologies on different interfaces, including Ethernet, fiber, DSL, ATM, MPLS, or cellular. Where multiple paths exist, routing protocols can select a best path.

```text
LAN → Router → WAN/ISP → Router → Remote LAN/Data Center
```

# Flashcards

**What does a routing table contain?** Destination IP networks.  
**What does C mean in `show ip route`?** Directly connected.  
**What happens without a route?** The router drops the packet.

# Knowledge Quiz

1. Why does every routed interface need an address from its connected subnet?
2. Compare router no-route behavior with switch unknown-unicast behavior.
3. Name three router use cases.
4. Why might a design include multiple routed paths?

# Practical Exercise

Design a topology connecting a campus LAN and data center through a WAN. Label every routed link with a different subnet, identify each gateway, and predict the directly connected entries on every router.

# Mastery Check

- [ ] Explain router interfaces, gateways, and routing tables.
- [ ] Identify directly connected routes.
- [ ] Draw a basic LAN–WAN–LAN routed design.
