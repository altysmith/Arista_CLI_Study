# 18. NTP

**Official unit:** Network Engineering Fundamentals → Network Protocols

# Learn

NTP synchronizes time. Accurate timestamps are essential for trustworthy logs and incident correlation.

```text
ntp server <server-address>
show ntp status
show ntp associations
```

The notes list NTP as UDP port 123.

# Flashcards

**NTP port?** UDP 123.  
**Verification commands?** `show ntp status` and `show ntp associations`.

# Knowledge Quiz

1. Why is synchronized time operationally important?
2. Give the configuration and verification commands.

# Practical Exercise

Investigate untrustworthy timestamps by checking associations, status, and configured server.

# Mastery Check

- [ ] Configure and verify NTP.
