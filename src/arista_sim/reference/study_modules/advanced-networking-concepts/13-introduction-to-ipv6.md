# 13. Introduction to IPv6

# Learn

IPv6 is a 128-bit Layer 3 address written as eight 16-bit hexadecimal hextets. The lesson uses `/64`: 64 network bits and 64 device bits.

IPv6 replaces broadcast functions with multicast, replaces ARP with NDP, has enough globally unique space to reduce NAT dependence, and can coexist with IPv4 using dual-stack or tunneling approaches.

Remove leading zeros in a hextet and compress one consecutive zero run with `::`; `::` may appear only once.

# Knowledge Quiz

1. Describe IPv6 size and notation.
2. State the compression rules.
3. Compare IPv6 multicast/NDP with IPv4 broadcast/ARP.

# Practical Exercise

Compress and expand `2001:0001:0000:0000:0000:AF23:082E:0001`.

# Mastery Check

- [ ] Read, compress, and expand IPv6 addresses.
