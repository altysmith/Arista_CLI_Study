# 5. IP Source Guard and ARP Inspection

# Learn

IP Source Guard validates a port’s source IP/MAC against DHCP snooping bindings and drops mismatches, limiting spoofing. Static bindings can support statically addressed devices.

Dynamic ARP inspection validates ARP replies against the same bindings on untrusted ports, limiting ARP poisoning that redirects gateway traffic for denial-of-service or man-in-the-middle attacks.

# Knowledge Quiz

1. What does IP Source Guard validate?
2. Explain ARP poisoning.
3. Why does the DHCP snooping table support both controls?

# Practical Exercise

Given IP/MAC/interface bindings, classify legitimate, spoofed-IP, spoofed-MAC, and poisoned-ARP traffic.

# Mastery Check

- [ ] Explain and troubleshoot both source-validation controls.
