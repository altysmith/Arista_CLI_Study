# 10. What Is a Subnet Mask?

**Official unit:** Network Engineering Fundamentals → Network Layer

# Learn

A subnet mask distinguishes network bits from host bits. The cross-referenced notes show:

```text
255.0.0.0 ↔ /8
255.255.0.0 ↔ /16
255.255.255.0 ↔ /24
```

Classless routing updates carry the mask and preserve the exact network; classful updates omit it and rely on default class interpretation.

# Flashcards

**/24 mask?** 255.255.255.0.  
**What does /24 mean?** 24 network bits and 8 host bits.

# Knowledge Quiz

1. Match /8, /16, and /24 to masks.
2. Explain network versus host bits.
3. Explain why carrying a mask matters.

# Practical Exercise

For each of /8, /16, and /24, state network bits, host bits, and dotted mask.

# Mastery Check

- [ ] Translate between the supported prefixes and masks.
