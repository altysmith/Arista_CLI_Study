# Network Foundations command coverage

This is the command-first curriculum map for the 17 Academy labs shown in the supplied photos. It is deliberately not a set of guided lab designs. The exact Academy task pages will later provide device names, interface assignments, IP addresses, and expected topology results.

Authority order:

1. Arista EOS documentation defines command syntax and CLI behavior.
2. The Arista Academy Network Foundations datasheet and lab list define priority.
3. Future local lab scenarios define simulator acceptance tests.

Placeholders such as `<VLAN_ID>`, `<INTERFACE>`, and `<PREFIX>` must be replaced with values from the actual Academy lab task.

## Lab 1 - Accessing the lab environment

This is a platform-access workflow, not an EOS configuration family. No additional simulated EOS command is required. Once connected, use `enable` to enter privileged EXEC mode.

## Lab 2 - Introduction to EOS CLI

```text
?
enable
disable
configure terminal
exit
end
show version
show running-config
show startup-config
copy running-config startup-config
write
```

Unique abbreviations, contextual `?`, Tab completion, and Up/Down command history are supported.

## Lab 3 - Management connectivity

```text
interface Management1
description <TEXT>
ip address <IPv4/PREFIX>
shutdown
no shutdown
ip route 0.0.0.0/0 <NEXT_HOP>
show ip interface brief
show ip route
ping <DESTINATION>
traceroute <DESTINATION>
```

The simulator stores the management address and default route. `ping` and `traceroute` are discoverable but do not invent success without peer topology.

## Lab 4 - Understanding network protocols

```text
show interfaces
show interfaces status
show ip interface brief
show ip route
show arp
show ip arp
show mac address-table
show ip protocols
ping <DESTINATION>
traceroute <DESTINATION>
```

ARP and MAC-learning views are honest empty tables until multi-device forwarding is added.

## Lab 5 - LLDP network diagram

```text
show lldp neighbors
show lldp neighbors detail
show lldp neighbors detailed
```

The command and output format are present. The current single-device simulator reports no neighbors; a future topology engine will populate the table.

## Lab 6 - VLANs and trunks

```text
vlan <VLAN_ID>
name <VLAN_NAME>
no name
no vlan <VLAN_ID>
interface <INTERFACE>
switchport
switchport mode access
switchport access vlan <VLAN_ID>
switchport mode trunk
switchport trunk native vlan <VLAN_ID>
switchport trunk allowed vlan <LIST>
switchport trunk allowed vlan all
switchport trunk allowed vlan none
switchport trunk allowed vlan add <LIST>
switchport trunk allowed vlan remove <LIST>
switchport trunk allowed vlan except <LIST>
show vlan
show vlan <VLAN_ID>
show interfaces status
show interfaces trunk
show interfaces <INTERFACE> switchport
show interfaces <INTERFACE> vlans
```

## Lab 7 - Inter-VLAN routing

Router-on-a-stick:

```text
interface Ethernet<PORT>.<SUBINTERFACE>
encapsulation dot1q vlan <VLAN_ID>
ip address <IPv4/PREFIX>
no shutdown
```

Switched virtual interfaces:

```text
ip routing
interface Vlan<VLAN_ID>
ip address <IPv4/PREFIX>
no shutdown
no autostate
show ip interface brief
show ip route
```

## Lab 8 - Spanning Tree Protocol

```text
spanning-tree mode mstp
spanning-tree mode rstp
spanning-tree mode rapid-pvst
spanning-tree vlan <VLAN_ID> priority <0-61440>
interface <INTERFACE>
spanning-tree portfast
spanning-tree portfast auto
spanning-tree portfast edge
spanning-tree portfast network
spanning-tree portfast normal
spanning-tree port-priority <0-240>
no spanning-tree portfast
show spanning-tree
```

Priority values are validated in EOS increments: bridge priority by 4096 and port priority by 16. Topology election is not yet simulated; configured values and deterministic local port state are displayed.

## Lab 9 - LACP and MLAG

```text
interface Ethernet<START>-<END>
channel-group <ID> mode active
channel-group <ID> mode passive
channel-group <ID> mode on
no channel-group
interface Port-Channel<ID>
mlag <ID>
show port-channel
show port-channel dense

mlag configuration
domain-id <DOMAIN_ID>
local-interface vlan <VLAN_ID>
peer-address <IPv4_ADDRESS>
peer-link port-channel <ID>
shutdown
no shutdown
show mlag
```

The simulator derives port-channel membership from Ethernet configuration. MLAG reports configuration completeness without claiming that a nonexistent peer is active.

## Lab 10 - Layer 3 addresses

```text
ip routing
interface Ethernet<PORT>
no switchport
ip address <IPv4/PREFIX>
no ip address
interface Loopback<ID>
ip address <IPv4/PREFIX>
interface Vlan<VLAN_ID>
ip address <IPv4/PREFIX>
show ip interface brief
show ip route
show interfaces <INTERFACE> switchport
```

## Lab 11 - Static routing

```text
ip route <IPv4_PREFIX> <NEXT_HOP_OR_INTERFACE>
no ip route <IPv4_PREFIX> <NEXT_HOP_OR_INTERFACE>
show ip route
show running-config
ping <DESTINATION>
traceroute <DESTINATION>
```

Connected and static routes are state-derived. Reachability remains topology-dependent.

## Lab 12 - Routing protocols

The Academy datasheet explicitly identifies RIP in this section, so the first implemented dynamic-routing workflow is:

```text
router rip
network <IPv4_NETWORK>
no network <IPv4_NETWORK>
redistribute connected
redistribute static
no redistribute connected
no redistribute static
show ip protocols
show ip rip database
show ip rip neighbors
show ip route
```

The datasheet also teaches link-state routing, and the Associate objectives identify OSPF. The core EOS OSPFv2 workflow is therefore included:

```text
router ospf <PROCESS_ID>
router-id <IPv4_ADDRESS>
network <IPv4_PREFIX> area <AREA_ID>
no network <IPv4_PREFIX> area <AREA_ID>
redistribute connected
redistribute static
redistribute rip
no redistribute <SOURCE>
show ip ospf
show ip ospf neighbor
show ip ospf interface brief
show ip protocols
show ip route
```

The simulator accepts the official CIDR form of the OSPF `network` command. Neighbor formation and learned routes require a future multi-device topology.

## Lab 13 - ACLs

IPv4 ACL definition and data-plane application:

```text
ip access-list <ACL_NAME>
[<SEQUENCE>] permit <PROTOCOL> <SOURCE> <DESTINATION> [SERVICE]
[<SEQUENCE>] deny <PROTOCOL> <SOURCE> <DESTINATION> [SERVICE]
remark <TEXT>
no <SEQUENCE>
interface <INTERFACE>
ip access-group <ACL_NAME> in
ip access-group <ACL_NAME> out
ipv4 access-group <ACL_NAME> in
ipv4 access-group <ACL_NAME> out
show ip access-lists
show ip access-lists <ACL_NAME>
```

Control-plane ACL:

```text
control-plane
ip access-group <ACL_NAME> in
no ip access-group <ACL_NAME> in
```

SSH service ACL:

```text
management ssh
ip access-group <ACL_NAME> in
no ip access-group <ACL_NAME> in
show management ssh ip access-list
```

ACL counters and packet enforcement require simulated traffic and are not yet claimed.

## Lab 14 - Troubleshooting ACLs

```text
show ip access-lists
show ip access-lists <ACL_NAME>
show running-config
show ip interface brief
show management ssh ip access-list
no <SEQUENCE>
no ip access-group <ACL_NAME> in
no ip access-group <ACL_NAME> out
```

These commands support configuration inspection and correction. Hit counters remain outside the single-device model.

## Lab 15 - Quality of Service

```text
class-map type qos match-any <CLASS_NAME>
match ip access-group <ACL_NAME>
policy-map type quality-of-service <POLICY_NAME>
class <CLASS_NAME>
set cos <0-7>
set dscp <0-63>
set traffic-class <0-7>
police cir <RATE> [bc <BURST>]
interface <INTERFACE>
service-policy type qos input <POLICY_NAME>
service-policy type qos output <POLICY_NAME>
show policy-map
```

Policy construction and attachment are stateful. Hardware queues, traffic classification, counters, policing, and shaping effects are not emulated.

## Lab 16 - IPv6 addressing

```text
ipv6 unicast-routing
no ipv6 unicast-routing
interface <INTERFACE>
ipv6 address <IPv6/PREFIX>
no ipv6 address
ipv6 route <IPv6_PREFIX> <NEXT_HOP_OR_INTERFACE>
no ipv6 route <IPv6_PREFIX> <NEXT_HOP_OR_INTERFACE>
show ipv6 interface brief
show ipv6 route
ping <IPv6_ADDRESS>
```

## Lab 17 - Navigating CloudVision Portal

CloudVision Portal is a graphical/web workflow, not an EOS CLI command family. It should be taught later with screenshots or a dedicated UI simulation, separate from the EOS parser.

## Verified EOS references

- [EOS CLI](https://www.arista.com/en/um-eos/eos-command-line-interface-cli)
- [LLDP](https://www.arista.com/en/um-eos/eos-link-layer-discovery-protocol)
- [Spanning Tree Protocol](https://www.arista.com/en/um-eos/eos-spanning-tree-protocol)
- [Port Channels and LACP](https://www.arista.com/en/um-eos/eos-port-channels-and-lacp)
- [MLAG](https://www.arista.com/en/um-eos/eos-multi-chassis-link-aggregation)
- [IPv4](https://www.arista.com/en/um-eos/eos-ipv4)
- [RIP](https://www.arista.com/en/um-eos/eos-routing-information-protocol-rip)
- [OSPFv2](https://www.arista.com/en/um-eos/eos-open-shortest-path-first-version-2)
- [ACLs and Service ACLs](https://www.arista.com/en/um-eos/eos-acls-and-route-maps)
- [Quality of Service](https://www.arista.com/en/um-eos/eos-quality-of-service)
- [IPv6](https://www.arista.com/en/um-eos/eos-ipv6)
