# 14. Network Address Translation (NAT)

# Learn

IPv4 NAT translates private inside addresses to public outside addresses. Private ranges in the notes are `10.0.0.0/8`, `172.16.0.0/12`, and `192.168.0.0/16`.

Static NAT maps one inside address to one public address. Dynamic NAT assigns addresses from a public pool. PAT/overload maps many inside sessions to one public address by tracking ports.

```text
Static:  one-to-one
Dynamic: many-to-pool
PAT:     many-to-one using ports
```

The router maintains a translation table. ACLs identify eligible inside traffic; NAT activates on the outbound interface in the notes’ workflow.

# Knowledge Quiz

1. Name the private ranges.
2. Compare static, dynamic, and PAT.
3. How does PAT distinguish simultaneous sessions?

# Practical Exercise

Build a PAT table for two inside hosts using the same source port and show how unique outside ports keep the sessions distinct.

# Mastery Check

- [ ] Select and explain the appropriate NAT type.
