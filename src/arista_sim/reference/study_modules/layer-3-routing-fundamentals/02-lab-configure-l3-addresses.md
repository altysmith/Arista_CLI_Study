# 2. LAB — Configure L3 Addresses

# Lab Goal

Address routed interfaces and verify connected networks.

# Tasks

1. Assign LAN-facing addresses from each LAN subnet.
2. Address the router-to-router link with a `/30` (`255.255.255.252`).
3. Enable the interfaces.
4. Run `show ip route` and identify every `C` route.
5. Ping each directly connected neighbor.
6. Correct one intentionally wrong prefix or address.

# Success Criteria

- [ ] Every interface belongs to the intended subnet.
- [ ] Connected routes appear automatically.
- [ ] Direct neighbors respond.
