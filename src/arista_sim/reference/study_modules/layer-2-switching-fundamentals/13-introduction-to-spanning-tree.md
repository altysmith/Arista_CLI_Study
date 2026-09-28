# 13. Introduction to Spanning Tree

# Learn

Layer 2 loops repeatedly circulate flooded BUM traffic and can create broadcast storms. STP is the IEEE 802.1D Layer 2 loop-prevention protocol. It blocks redundant ports while retaining standby paths that can activate after a failure.

STP runs on switchports, not Layer 3 interfaces. Its spanning-tree algorithm selects an active loop-free topology before a storm develops.

# Flashcards

**What does STP prevent?** Layer 2 loops.  
**Why retain blocked links?** Redundant failover.

# Knowledge Quiz

1. Explain a broadcast storm.
2. Explain how blocking creates a loop-free topology.
3. Why does STP operate only at Layer 2?

# Practical Exercise

Draw three switches in a triangle, choose one redundant link to block, and show the failover path after an active link fails.

# Mastery Check

- [ ] Explain loop formation, prevention, and standby paths.
