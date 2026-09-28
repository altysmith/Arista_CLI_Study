# 14. STP Operations

# Learn

Switches exchange BPDUs to destination `01:80:C2:00:00:00`. A bridge ID includes priority and system MAC. The lowest priority becomes root; ties use the lowest MAC.

Each non-root switch chooses one root port with the lowest path cost; higher bandwidth means lower cost. Each Ethernet segment elects one designated port. On a point-to-point redundant link, the non-designated side blocks.

# Flashcards

**Root election order?** Lowest priority, then lowest MAC.  
**Root port?** Best path from a non-root switch to the root.

# Knowledge Quiz

1. Explain root election.
2. Differentiate root and designated ports.
3. Explain path cost and bandwidth.

# Practical Exercise

Given three bridge IDs and link costs, elect the root and identify root, designated, and blocked ports.

# Mastery Check

- [ ] Perform a basic STP election.
