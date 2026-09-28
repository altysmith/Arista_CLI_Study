# 2. ACL Types

# Learn

Standard ACLs match source IPv4 only. IP ACLs can match source/destination IP, ports, and protocol. MAC ACLs match Layer 2 source/destination MAC and EtherType protocols such as ARP, LLDP, or LACP.

```text
ip access-list standard NAME
ip access-list NAME
mac access-list NAME
ip access-group NAME in|out
```

# Knowledge Quiz

1. Choose the correct ACL type for source-only, service-port, and MAC filtering.
2. What does `/32` identify?
3. Why are MAC ACLs applied inbound in the notes?

# Practical Exercise

Permit one host to one server, permit another host broadly, and rely on implicit deny for everything else.

# Mastery Check

- [ ] Select, write, apply, and verify the appropriate ACL type.
