# 3. LAB — Creating a Network Diagram Using LLDP

# Lab Goal

Discover a Layer 2 topology and document it accurately.

# Tasks

1. Run `show lldp neighbors` on the starting switch.
2. Record each local interface, neighbor system name, and neighbor port.
3. Use `show lldp neighbors detail` for management IP and capabilities.
4. Visit each discovered switch and repeat.
5. Draw links with interface labels on both ends.
6. Validate every drawn link from both devices where possible.

# Verification

- [ ] Every LLDP neighbor appears in the diagram.
- [ ] Both ends of each link are labeled.
- [ ] The diagram distinguishes switches, routers, and endpoints.
- [ ] Unknown or missing neighbors are documented rather than guessed.

# Reflection

Explain why LLDP alone cannot prove devices beyond the directly connected neighbor.
