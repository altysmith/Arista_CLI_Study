# 15. ICMP

**Official unit:** Network Engineering Fundamentals → Network Protocols

# Learn

ICMP means Internet Control Message Protocol. `ping` checks reachability. The ICMP header includes type, code, and checksum. The notes list Type 0 echo, Type 8 echo reply, and Type 3 destination unreachable.

`tracert` helps identify where a path stops responding. Probe methods vary by implementation, so traceroute is not universally ICMP.

# Flashcards

**Type 3?** Destination unreachable.  
**Ping versus tracert?** Reachability versus path-hop isolation.

# Knowledge Quiz

1. Name the ICMP header fields and listed types.
2. Explain how tracert narrows failure scope.

# Practical Exercise

Use ping first, then tracert to identify the last responsive hop.

# Mastery Check

- [ ] Interpret basic ICMP reachability results.
