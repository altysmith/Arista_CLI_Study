# 2. Creating a Network Diagram Using LLDP

# Learn

`show lldp neighbors` displays directly connected devices and their interfaces. `show lldp neighbors detail` exposes more TLVs. Start at one switch, record local port, neighbor name, and remote port, then connect to each neighbor and repeat down every branch.

`show lldp` displays transmit interval, holdtime, reinitialization delay, enabled TLVs, and enabled ports.

# Flashcards

**Best starting command?** `show lldp neighbors`.  
**Why visit each neighbor?** LLDP does not see across routed or nonadjacent links.

# Knowledge Quiz

1. What fields are needed for a diagram?
2. Why must discovery be repeated on neighboring switches?

# Practical Exercise

Create a table of local device/port, neighbor device/port, management IP, and capabilities, then convert the table into a topology diagram.

# Mastery Check

- [ ] Build a topology from LLDP output.
