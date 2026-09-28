# 8. Inter-VLAN Routing

# Learn

Different VLANs are different subnets and require Layer 3 routing. A Layer 2 switch cannot route between them.

Methods: separate router interfaces, router-on-a-stick subinterfaces, or SVIs on a multilayer switch. Separate interfaces consume physical ports. Router-on-a-stick uses one trunk but routes in software. An MLS has MAC and routing tables and routes in hardware.

# Knowledge Quiz

1. Why can’t a Layer 2 switch route VLAN traffic?
2. Compare the three methods.
3. Why are SVIs generally faster in the lesson model?

# Practical Exercise

Choose a design for two VLANs, then for dozens of VLANs, and justify the Layer 3 gateway location.

# Mastery Check

- [ ] Explain all three inter-VLAN methods.
