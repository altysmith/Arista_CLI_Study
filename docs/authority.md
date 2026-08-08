# Authority and curriculum scope

The simulator uses three levels of authority:

1. Official EOS documentation defines CLI and networking behavior.
2. Arista Academy Network Foundations course and exam material determines feature priority.
3. Local lab scenarios define learner-facing exercises and acceptance tests.

## Verified EOS behavior

The official EOS 4.36.1F CLI manual confirms:

- EXEC (`switch>`), Privileged EXEC (`switch#`), Global Configuration (`switch(config)#`), Interface Configuration (`switch(config-if-Et24)#`), and protocol-specific modes.
- `enable`, `configure`, `exit`, `end`, and `disable` mode navigation.
- Case-insensitive keywords and truncated keywords only when the abbreviation is unique. The manual's own example rejects `con` as ambiguous and accepts `conf` as `configure`.
- `?` lists commands at the current level, filters keywords from a partial token, and lists the next keywords or arguments.
- `show running-config`, and separate running/startup configurations saved with `write` or `copy running-config startup-config`.
- `show interfaces [INTERFACE] trunk` displays configuration and status for trunk interfaces.
- `show mac address-table` is the EOS command for displaying learned and configured MAC table entries.

Primary behavior source: [Arista EOS 4.36.1F Command-Line Interface](https://www.arista.com/en/um-eos/eos-command-line-interface-cli).

Switching command sources: [Virtual LANs](https://www.arista.com/en/um-eos/eos-virtual-lans-vlans) and [Data Transfer](https://www.arista.com/en/um-eos/eos-data-transfer).

## Network Foundations priorities

The supplied Network Foundations course datasheet prioritizes:

1. Networking fundamentals and protocols.
2. EOS fundamentals and CLI configuration.
3. VLANs, trunks, inter-VLAN routing, STP, LACP, and MLAG.
4. IPv4, static and dynamic routing.
5. ACLs/security, QoS, IPv6, and CloudVision/automation.

The current official Associate exam datasheet adds an important practical emphasis: VLAN/STP, MLAG, port-channels, VARP and SVIs, static routing and OSPF, ACLs, IPv6, and systematic verification/troubleshooting in leaf-spine scenarios.

Official curriculum sources:

- [Network Foundations course datasheet](https://www.training.arista.com/hubfs/Track%20Datasheets/Foundations.pdf)
- [Network Foundations Associate exam datasheet](https://www.training.arista.com/hubfs/Arista_Academy_Exam_Datasheets/Network%20Foundations.pdf)
- [Arista Academy learning pathways](https://www.training.arista.com/learning-pathways)

## Supplied-file note

The supplied Network Foundations PDF contains the complete three-page V2.0 course outline. The supplied file named `EOS-User-Manual.pdf` contains only a one-page browser print of the online manual outline (`1 of 5,387`), not the 5,387 pages of manual content. Behavioral verification therefore uses the official live EOS manual linked above.

As of August 8, 2026, Arista describes Network Foundations as the Associate accreditation. Legacy Level 1 maps to Network Foundations Associate; the older Level 1-5 exams reached end-of-life on December 31, 2025.
