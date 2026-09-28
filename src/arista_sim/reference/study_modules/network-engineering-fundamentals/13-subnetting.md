# 13. Subnetting

**Official unit:** Network Engineering Fundamentals → Network Layer

# Learn

Subnetting applies a prefix to determine the network and host portions of an address. The available individual notes support /8, /16, and /24 interpretation and exact-prefix routing, but do not provide a full borrowed-bit calculation workflow.

```text
/8 = 8 network, 24 host bits
/16 = 16 network, 16 host bits
/24 = 24 network, 8 host bits
```

# Flashcards

**Subnet mask versus subnetting?** A mask marks the boundary; subnetting applies boundaries to network design.

# Knowledge Quiz

1. State the supported bit splits.
2. Explain why `10.1.1.0/24` is more specific than `10.0.0.0/8`.

# Practical Exercise

Identify network/host bit counts and masks for /8, /16, and /24 examples.

# Mastery Check

- [ ] Interpret the supported prefixes accurately.
