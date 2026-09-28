# 21. LAB — Configuring LACP and MLAG

# Lab Goal

Build and verify an LACP bundle, then use an MLAG pair to dual-home a downstream device.

# Tasks

1. Confirm intended links with `show lldp neighbors`.
2. Configure matching member settings.
3. Create an LACP Port-Channel with at least one active side.
4. Verify with `show port-channel dense`, interface status, and spanning tree.
5. Configure the two-switch MLAG domain and common system behavior.
6. Attach the downstream LACP Port-Channel across both peers.
7. Verify all members forward as one logical bundle.
8. Test one member-link failure and one peer failure.
9. Document expected and observed forwarding.

# Success Criteria

- [ ] LACP negotiates successfully.
- [ ] Member settings are consistent.
- [ ] MLAG appears as one logical LACP system downstream.
- [ ] Traffic survives the tested link and peer failures.
