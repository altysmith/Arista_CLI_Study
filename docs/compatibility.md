# EOS compatibility

## Campus browser exercises

The campus tickets add a fixed, loop-free, three-switch Layer 2 model, with four fixed-address hosts. LLDP and interface link status derive from links and administrative state. Simulated host ARP/ICMP traffic traverses access and trunk ports with native/allowed VLAN handling and learns source MAC addresses. Host ARP is shown in the topology panel. Grading does not generate traffic. Learning tables clear on configuration/navigation commands and server restart; aging, timers, routing, STP convergence, LACP, MLAG and ACL enforcement remain outside this model. The single-device compatibility table below describes the original standalone exercises.

This file prevents simulated behavior from being mistaken for verified EOS behavior.

| Feature | Status | Notes |
|---|---|---|
| CLI mode prompts/navigation | Supported | EXEC, privileged EXEC, global, VLAN, interface, RIP, ACL, MLAG, control-plane, management-SSH, class-map, and policy-map modes |
| Unique command abbreviation | Supported | Token-level literals plus interface aliases |
| Contextual `?` | Supported | Immediate current-level, partial-keyword, and next-token help in the Windows console |
| Command history | Supported | Up/Down arrows recall commands entered in the current session on Windows, macOS, and Linux |
| Tab completion | Partial | Unique completion and ambiguous choices work in the Windows console; cursor movement editing is not implemented |
| Parent-mode command inheritance | Partial | Navigation is modeled; broad execution of every parent-mode command from child modes is not yet implemented |
| Hostname | Supported | Prompt changes immediately |
| VLAN create/name/remove | Supported | Structured state, reset forms, and filtered/all `show vlan` |
| Ethernet description/admin state | Supported | `shutdown` and `no shutdown` |
| Access switchport | Supported | Mode, access VLAN, and reset forms |
| Trunk switchport | Supported | Mode, native VLAN, allowed VLAN lists/ranges, edit actions, and reset forms |
| Layer 2 verification | Supported | `show interfaces status`, `trunk`, `switchport`, and `vlans` are state-derived |
| Running configuration | Supported | Rendered from structured state |
| Startup configuration | Supported | Save/copy snapshot only; reload is not implemented |
| Interface operational state | Partial | No physical topology exists, so operational status is simulated as connected when admin-up |
| Layer 2 forwarding/MAC learning | Not implemented | Planned after interface/VLAN command coverage |
| LLDP | Partial | Command discovery and honest empty output; no peer topology exists yet |
| STP | Partial | Configuration and state-derived local display; no multi-switch election or convergence engine |
| LACP and MLAG | Partial | Stateful configuration and verification; no peer negotiation or MLAG forwarding engine |
| IPv4 addressing and static routing | Supported | Management, routed Ethernet, SVI, loopback, subinterface, connected-route, and static-route practice |
| ARP and MAC learning | Partial | Diagnostic commands are present but correctly report no learned entries without a topology engine |
| RIP | Partial | Stateful network/redistribution configuration and verification; no neighbor exchange or route learning |
| OSPFv2 | Partial | Stateful process/router-ID/network configuration and verification; no adjacency or route exchange |
| IPv6 addressing and static routing | Supported | Interface addresses, global forwarding setting, static routes, and verification |
| ACL/security | Partial | IPv4 ACL editing plus interface, control-plane, and SSH service attachment; no packet enforcement/counters |
| QoS | Partial | Class-map, policy-map, marking/policer configuration and attachment; no ASIC queues or traffic effects |
| CloudVision | Not implemented | Lab 17 is a graphical portal workflow and remains separate from the EOS CLI simulator |
| Hardware/ASIC behavior | Not implemented | Explicitly out of initial scope |
