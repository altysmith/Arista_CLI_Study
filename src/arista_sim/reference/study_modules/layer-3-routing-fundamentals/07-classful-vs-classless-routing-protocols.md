# 7. Classful vs. Classless Routing Protocols

# Learn

Classful protocols omit subnet masks and rely on default address-class boundaries. Classless protocols include the prefix and preserve exact networks.

```text
Classful:  10.1.1.0/24 advertised as 10.0.0.0/8
Classless: 10.1.1.0/24 advertised exactly
```

The notes classify RIPv1 as classful and RIPv2, OSPF, IS-IS, and BGP as classless.

# Knowledge Quiz

1. What information does classful routing omit?
2. Why can that cause incorrect forwarding?
3. Classify the listed protocols.

# Practical Exercise

Compare route tables learned from `10.1.1.0/24` and `10.2.2.0/24` using classful versus classless advertisements.

# Mastery Check

- [ ] Explain why modern routing requires prefixes.
