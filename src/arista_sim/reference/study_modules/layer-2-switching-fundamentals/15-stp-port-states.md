# 15. STP Port States

# Learn

The lesson’s classic STP sequence is disabled, listening, learning, and forwarding, with blocked as the non-forwarding redundant outcome. Listening examines BPDUs and elections for about 15 seconds. Learning builds tables for another 15 seconds. Forwarding sends and receives data; convergence is complete.

```text
Disabled → Listening → Learning → Forwarding
                    ↘ Blocked
```

# Knowledge Quiz

1. What occurs in listening and learning?
2. Which ports reach forwarding?
3. Why does classic convergence take time?

# Practical Exercise

Given a newly connected redundant port, trace its possible state transitions and LED behavior from the notes.

# Mastery Check

- [ ] Explain every state and transition.
