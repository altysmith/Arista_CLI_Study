# 12. LAB — Configure Inter-VLAN Routing

# Lab Goal

Provide Layer 3 connectivity between VLANs and verify gateways and routes.

# Tasks

1. Build VLANs 10 and 20 with endpoint access ports.
2. Choose router-on-a-stick or multilayer-switch SVIs.
3. Configure the trunk path.
4. Configure `10.1.1.1/24` and `20.1.1.1/24` as VLAN gateways.
5. Enable required interfaces and `ip routing` when using SVIs.
6. Verify connected routes and gateway reachability.
7. Test inter-VLAN traffic.
8. Introduce one tag, trunk, or gateway error and troubleshoot it.

# Success Criteria

- [ ] Both VLANs reach their gateways.
- [ ] The Layer 3 device has both connected routes.
- [ ] Inter-VLAN traffic succeeds after repair.
