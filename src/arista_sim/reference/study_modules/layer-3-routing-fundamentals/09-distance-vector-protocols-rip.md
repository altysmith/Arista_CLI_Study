# 9. Distance Vector Protocols (RIP)

# Learn

Distance is how far away a network is; vector is the direction/next hop. RIP exchanges its full routing table every 30 seconds and increments hop count. Routers converge only after updates propagate.

Directly connected routes beat learned duplicates because their administrative distance is lower. RIP metric 16 marks a network unreachable, making convergence and failure propagation slow.

# Knowledge Quiz

1. Define distance and vector.
2. Explain periodic full-table exchange.
3. What does metric 16 mean?

# Practical Exercise

Trace a route across three routers over two update cycles and increment the hop count at each exchange.

# Mastery Check

- [ ] Explain RIP learning, convergence, and limitations.
