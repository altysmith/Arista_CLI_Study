# 3. What Is SysDB?

# Learn

SysDB is EOS’s system database and shared source of device state, including VLANs, links, routes, and control-plane information. Agents such as forwarding, LACP, and LED processes publish or consume state through it.

The notes emphasize process restart and overload protection as architectural advantages: agents can be isolated while shared state remains available.

# Knowledge Quiz

1. What information does SysDB store?
2. How do agents use shared state?
3. Why does process isolation improve resilience?

# Practical Exercise

Map VLAN, route, LACP, forwarding, and LED state to the agents that consume it.

# Mastery Check

- [ ] Explain SysDB’s shared-state role.
