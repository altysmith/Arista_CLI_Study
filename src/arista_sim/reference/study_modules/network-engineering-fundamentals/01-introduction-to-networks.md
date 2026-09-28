# 1. Introduction to Networks

**Official unit:** Network Engineering Fundamentals → Network Introduction

**Primary source:** Introduction to Networks

# Learn

A network is a group of components connected together to provide services, including information access, resource sharing, and voice/VoIP communication.

```text
Network
├── Endpoints
├── Network devices
└── Connectivity
```

Endpoints include PCs, laptops, smartphones, servers, tablets, and printers. Network devices include switches, hubs, modems, routers, bridges, access points, firewalls, IPS, and IDS. Connectivity can be wired or wireless.

## Topologies

- **Point-to-point:** one link between two devices; one path.
- **Bus:** devices share one cable; the notes associate it with coaxial cable.
- **Token ring:** devices form a ring; communication travels one direction.
- **Star:** endpoints connect to a central device; loss of that device loses connectivity.
- **Mesh:** multiple paths provide redundancy, at greater cost and complexity.

Physical topology is how devices are cabled. Logical topology is how traffic moves or the network behaves internally.

The notes introduce LAN, MAN, WAN and the network characteristics cost, redundancy, availability, speed, scalability, and security without further definitions.

# Flashcards

**What three parts form the network mental model?**  
Endpoints, network devices, and connectivity.

**What is the benefit of mesh?**  
Redundancy.

**What is physical topology?**  
How devices are physically connected.

**What is logical topology?**  
How traffic moves or the network behaves internally.

# Knowledge Quiz

1. Define a network using the notes.
2. Contrast endpoints with network devices.
3. Identify the five topology types.
4. Explain the tradeoff of mesh.
5. Explain physical versus logical topology.

# Practical Exercise

Draw a star network and identify its central failure point. Then draw a mesh and identify the redundant paths and its cost/complexity tradeoff.

# Mastery Check

- [ ] Explain the network-component model.
- [ ] Recognize each topology from a diagram.
- [ ] Distinguish physical from logical topology.
