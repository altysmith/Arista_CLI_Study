# 4. Static Routing

# Learn

Static routing manually adds fixed routing-table entries.

```text
ip route 20.1.1.0/24 e2
ip route 20.1.1.0/24 30.1.1.2
ip route 0.0.0.0/0 30.1.1.2
```

Use an exit interface on an appropriate point-to-point path or a next-hop address on a multipoint network. Return routes are required. `S` marks static and `S*` a candidate default route.

# Knowledge Quiz

1. Compare exit-interface and next-hop routes.
2. Why is one-way routing insufficient?
3. Explain `0.0.0.0/0`.

# Practical Exercise

Configure reciprocal static routes between two LANs and verify with `show ip route` and ping.

# Mastery Check

- [ ] Configure destination, return, and default static routes.
