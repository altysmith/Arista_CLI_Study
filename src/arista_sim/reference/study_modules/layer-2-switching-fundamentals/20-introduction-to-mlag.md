# 20. Introduction to MLAG

# Learn

MLAG extends LAG across two switches. The two-switch MLAG domain agrees on a common LACP system ID so a downstream device sees one logical system. The domain supports two devices, not three.

MLAG enables dual-homed switches and LACP-capable endpoints. The downstream device needs LACP; MLAG-specific configuration resides on the upstream pair. It avoids wasting an uplink to STP blocking and provides link/switch redundancy.

# Knowledge Quiz

1. What problem does MLAG solve beyond LAG?
2. Why is a shared system ID necessary?
3. What is the maximum domain size?

# Practical Exercise

Draw a server with two NICs connected to two MLAG peers and trace behavior after one link or one peer fails.

# Mastery Check

- [ ] Explain MLAG domain, system ID, dual-homing, and limits.
