# 11. LAB — Configure VLANs

# Lab Goal

Create VLANs across two switches and prove correct access/trunk behavior.

# Tasks

1. Create and name VLANs 10 and 20 on both switches.
2. Assign endpoint interfaces as access ports.
3. Configure the inter-switch interfaces as trunks.
4. Allow VLANs 10 and 20.
5. Verify using `show vlan`, `show interfaces status`, and `show interfaces <port> trunk`.
6. Test same-VLAN communication across switches.
7. Remove one VLAN from the allowed list, observe failure, and restore it.

# Success Criteria

- [ ] Correct VLAN membership on both switches.
- [ ] Trunk operational with intended allowed VLANs.
- [ ] Same-VLAN traffic succeeds across the trunk.
- [ ] The induced allowed-VLAN fault is identified and repaired.
