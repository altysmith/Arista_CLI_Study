# 8. Metric and Administrative Distance

# Learn

A metric selects the best path learned by the same protocol; lower is best. Metrics may use hop count, bandwidth, delay, load, or reliability. Equal metrics can enable ECMP load balancing.

Administrative distance ranks trust between different route sources; lower is preferred. The notes list connected 0, static 1, OSPF 110, IS-IS 115, RIP 120, and BGP 200.

# Knowledge Quiz

1. Metric versus administrative distance?
2. When is ECMP used?
3. Which wins: OSPF or RIP, using the listed defaults?

# Practical Exercise

Select a route first among different protocols using AD, then among same-protocol paths using metric.

# Mastery Check

- [ ] Apply AD and metric in the correct order.
