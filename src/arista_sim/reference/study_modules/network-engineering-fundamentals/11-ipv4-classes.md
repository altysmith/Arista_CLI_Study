# 11. IPv4 Classes

**Official unit:** Network Engineering Fundamentals → Network Layer

# Learn

| Class | Range | Default |
|---|---|---|
| A | 1.0.0.0–126.255.255.255 | /8 |
| B | 128.0.0.0–191.255.255.255 | /16 |
| C | 192.0.0.0–223.255.255.255 | /24 |
| D | 224.0.0.0–239.255.255.255 | Multicast |
| E | 240.0.0.0–254.255.255.255 | Experimental |

`127.0.0.0/8` is reserved for loopback. Classful addressing is historical; modern boundaries use prefixes.

# Flashcards

**Class D use?** Multicast.  
**Loopback range?** 127.0.0.0–127.255.255.255.

# Knowledge Quiz

1. Match A/B/C to ranges and masks.
2. Identify D, E, and loopback.

# Practical Exercise

Classify sample addresses by first octet and provide the A/B/C default prefix.

# Mastery Check

- [ ] Recall ranges, default prefixes, and special classes.
