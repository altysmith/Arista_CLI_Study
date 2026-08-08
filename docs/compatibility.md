# EOS compatibility

This file prevents simulated behavior from being mistaken for verified EOS behavior.

| Feature | Status | Notes |
|---|---|---|
| CLI mode prompts/navigation | Supported | EXEC, privileged EXEC, global, VLAN, and Ethernet interface modes |
| Unique command abbreviation | Supported | Token-level literals plus interface aliases |
| Contextual `?` | Supported | Current level, partial keyword, and next-token help |
| Tab completion | Partial | Unique completion and ambiguous choices work in the Windows console; advanced line editing is not implemented |
| Parent-mode command inheritance | Partial | Navigation is modeled; broad execution of every parent-mode command from child modes is not yet implemented |
| Hostname | Supported | Prompt changes immediately |
| VLAN create/name | Supported | Structured state and `show vlan` |
| Ethernet description/admin state | Supported | `shutdown` and `no shutdown` |
| Access switchport | Supported | Mode and access VLAN |
| Trunk switchport | Partial | Mode is stored; allowed/native VLAN commands are not yet implemented |
| Running configuration | Supported | Rendered from structured state |
| Startup configuration | Supported | Save/copy snapshot only; reload is not implemented |
| Interface operational state | Partial | No physical topology exists, so operational status is simulated as connected when admin-up |
| Layer 2 forwarding/MAC learning | Not implemented | Planned after interface/VLAN command coverage |
| STP, LACP, MLAG, VARP | Not implemented | Network Foundations priorities after base switching |
| IPv4/IPv6, ARP, routing, OSPF | Not implemented | Future milestones |
| ACL/security, QoS, CloudVision | Not implemented | Future curriculum scope |
| Hardware/ASIC behavior | Not implemented | Explicitly out of initial scope |
