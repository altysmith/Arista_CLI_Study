# 19. Configuring Link Aggregation

# Learn

Verify physical peers with LLDP and current STP roles before bundling.

```text
interface ethernet 1-2
 channel-group 1 mode on       ! static
 channel-group 1 mode active   ! LACP
```

LACP must be active/active or active/passive, never passive/passive. Static and LACP cannot be mixed. Verify with `show port-channel`, `show port-channel dense`, `show interfaces status`, and `show spanning-tree`. Configure switching behavior on `interface port-channel 1`.

# Knowledge Quiz

1. Compare static mode and LACP.
2. Explain active/passive rules.
3. Does the Port-Channel number have to match remotely?

# Practical Exercise

Build a two-link LACP Port-Channel, verify forwarding, remove one member, and confirm the logical interface stays up.

# Mastery Check

- [ ] Configure, verify, and troubleshoot static LAG and LACP.
