# 8. L2 Devices Learning and Forwarding

**Official unit:** Network Engineering Fundamentals → Data Link Layer

# Learn

Unicast is one-to-one, multicast one-to-many, and broadcast one-to-all; the broadcast MAC is `FF:FF:FF:FF:FF:FF`.

Hubs are Layer 1, half-duplex repeaters in one collision domain. Bridges are software-based Layer 2 devices. Switches are hardware-forwarding, full-duplex Layer 2 devices that learn source MAC addresses and ports.

Known unicast is forwarded toward a known destination. Unknown unicast is flooded except back toward the source port. Broadcast and multicast are flooded in the lesson model. BUM means Broadcast, Unknown unicast, Multicast.

# Flashcards

**What does a switch learn?** Source MAC and receiving port.  
**What is BUM?** Broadcast, Unknown unicast, Multicast.

# Knowledge Quiz

1. Compare hubs, bridges, and switches.
2. Explain known and unknown unicast handling.
3. Explain CSMA/CD and half-duplex collisions.

# Practical Exercise

Given an empty MAC table, trace learning and flooding for the first exchange between two endpoints.

# Mastery Check

- [ ] Predict switch learning and forwarding behavior.
