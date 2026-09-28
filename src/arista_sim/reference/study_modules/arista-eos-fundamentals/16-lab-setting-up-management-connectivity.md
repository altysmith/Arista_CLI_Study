# 16. LAB — Setting Up Management Connectivity

# Lab Goal

Configure and verify reliable out-of-band switch management.

# Tasks

1. Enter `interface Management0`.
2. Place it in the `MGMT` VRF.
3. Assign the provided management `/24` address.
4. Verify interface state and management routing.
5. Test reachability to the management gateway/services.
6. Inspect `show running-config`, `all`, `diffs`, `interfaces`, and `sanitized` output.
7. Recognize existing CloudVision, API, AAA, and RADIUS management configuration.
8. Create a secured local administrative user and verify it.

# Success Criteria

- [ ] Management0 is addressed, operational, and isolated in MGMT.
- [ ] Remote management reachability works.
- [ ] Shared configuration output is sanitized.
- [ ] The access path remains independent of production traffic.
