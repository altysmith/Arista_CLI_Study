# 18. Introduction to Link Aggregation

# Learn

Link aggregation combines physical interfaces into one logical Port-Channel so STP treats parallel links as one path. LAG provides load balancing, built-in loop prevention, and member-link failover; the Port-Channel stays up while at least one member remains.

Members require matching speed, duplex, access/trunk settings, allowed VLANs, and STP settings. Traditional LAG is one device to one device.

# Knowledge Quiz

1. Why would STP otherwise block parallel links?
2. Name three LAG benefits.
3. List required consistency settings.

# Practical Exercise

Compare two independent 10G links with a two-member Port-Channel during normal operation and one-link failure.

# Mastery Check

- [ ] Explain LAG behavior, requirements, and failover.
