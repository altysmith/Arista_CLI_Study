# 14. IPv6 Address Types

# Learn

Unspecified is `::/128`; loopback is `::1/128`. Global unicast is `2000::/3`; unique local is `FC00::/7`; link-local is `FE80::/10`, is non-routable, and supports local neighbor/routing relationships. Interfaces can have global and link-local addresses simultaneously.

Multicast is `FF00::/8` and provides one-to-many delivery. Anycast assigns the same unicast address to multiple devices and routes to the closest instance.

EUI-64 can derive a 64-bit interface identifier from a 48-bit MAC by inserting `FFFE` and flipping the seventh bit.

# Knowledge Quiz

1. Match each address type to its prefix and purpose.
2. Explain link-local behavior.
3. Compare multicast and anycast.

# Practical Exercise

Classify sample addresses and derive an EUI-64 identifier from the lesson’s MAC example.

# Mastery Check

- [ ] Identify IPv6 address types and scopes.
