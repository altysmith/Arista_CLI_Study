# 16. DNS

**Official unit:** Network Engineering Fundamentals → Network Protocols

# Learn

When an IP destination works but its hostname fails, investigate DNS: resolver configuration, resolver reachability, response correctness, and the requested record.

```text
ip name-server <server-address>
show hosts
```

The notes list DNS on UDP/TCP port 53.

# Flashcards

**IP works, name fails?** Focus on DNS.  
**DNS port?** UDP/TCP 53.

# Knowledge Quiz

1. State the four DNS checks.
2. Give the configuration and verification commands.

# Practical Exercise

Troubleshoot a working IP ping with a failing hostname in dependency order.

# Mastery Check

- [ ] Separate DNS failure from IP reachability failure.
