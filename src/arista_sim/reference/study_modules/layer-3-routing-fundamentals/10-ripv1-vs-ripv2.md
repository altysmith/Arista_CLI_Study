# 10. RIPv1 vs. RIPv2

# Learn

RIPv1 sends full tables every 30 seconds by broadcast, has no authentication, uses hop count, supports 15 hops, uses 16 as unreachable, has AD 120, and is classful.

RIPv2 uses multicast `224.0.0.9`, supports authentication, includes subnet masks, and sends triggered poison updates after failures. It retains the 15-hop scalability limit.

# Knowledge Quiz

1. Compare update delivery, authentication, and mask handling.
2. What is route poisoning?
3. What limitation remains in RIPv2?

# Practical Exercise

Given a failure, compare when and how RIPv1 and RIPv2 inform neighbors.

# Mastery Check

- [ ] Distinguish RIPv1 and RIPv2 precisely.
