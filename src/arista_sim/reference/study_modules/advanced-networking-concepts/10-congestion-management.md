# 10. Congestion Management

# Learn

Outbound traffic waits in queues/buffers. A full FIFO queue drops packets and provides no prioritization.

Strict-priority queues serve higher priority first, but can starve lower queues. Round-robin rotates among queues after priority traffic. Weighted round-robin allocates different bandwidth shares to traffic classes.

# Knowledge Quiz

1. What happens when a buffer fills?
2. Explain starvation.
3. Compare strict priority and weighted round-robin.

# Practical Exercise

Allocate voice, HTTP, SSH, and FTP among priority and weighted queues without starving lower classes.

# Mastery Check

- [ ] Select queue behavior appropriate to traffic needs.
