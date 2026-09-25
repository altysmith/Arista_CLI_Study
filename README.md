# Arista EOS Network Foundations Simulator

A local, dependency-free training simulator that teaches EOS CLI discovery and configuration workflow. Milestone 1 implements a small but stateful EOS-style shell; it does not emulate EOS or switch hardware.

## Browser lab

The campus release adds two fictional three-switch/four-host break/fix tickets: a staff access-port fault and a student trunk fault. Switch consoles expose topology-derived LLDP and MAC learning; the host ping panel tests same-subnet connectivity and shows host ARP. Grading checks both host pairs, Layer 2 isolation, and preservation of management VLAN 99. This fixed, loop-free model does not simulate routing, STP convergence, LACP, MLAG, ACL enforcement, or traffic timing.

For durable saves across refreshes and server restarts, run `python -m arista_sim.web --data-path user_data/progress.sqlite3`. The Windows/macOS browser launchers enable this automatically. Switching exercises resumes each exercise's saved configuration; Reset clears only that exercise. Configurations save independently from EOS startup configuration. Terminal output and learned tables are transient. The hosted app is for one authorized owner, with progress shared across their devices.

See [Pi deployment](docs/pi-deployment.md) for the private subdomain, service, backups, and rollback procedure.

The browser-based practice environment provides a real terminal backed by the same stateful simulator, selectable access-VLAN and existing-trunk exercises, contextual objectives and hints, reset controls, and state-based grading. Lab-specific starting configurations are restored whenever an exercise is reset. A searchable command-reference drawer groups common EOS navigation, verification, switching, routing, LACP/MLAG, ACL, and QoS commands; selecting one places it at the prompt without executing it.

- On Windows, double-click `run_web_lab.bat`.
- On macOS, double-click `run_web_lab.command`.

The launcher opens `http://127.0.0.1:8765` in your default browser. Keep its terminal window open while practicing; press Ctrl+C there when you are finished.

You can also start it manually:

```console
python -m arista_sim.web
```

## Run it

On Windows, double-click `run_simulator.bat`.

On macOS, double-click `run_simulator.command`. The first time you run it, macOS may ask you to confirm that you want to open it.

You can also run the simulator from PowerShell or Terminal:

```console
python -m arista_sim
```

If the package has not been installed, both launchers use the repository's `src` directory directly. The macOS launcher looks for Python 3.11 or newer in common Homebrew locations and in Codex's bundled runtime.

Try this interaction:

```text
switch> enable
switch# configure
switch(config)# hostname SW1
SW1(config)# vlan 20
SW1(config-vlan-20)# name STUDENTS
SW1(config-vlan-20)# exit
SW1(config)# interface ethernet 1
SW1(config-if-Et1)# description Student-PC
SW1(config-if-Et1)# switchport mode access
SW1(config-if-Et1)# switchport access vlan 20
SW1(config-if-Et1)# no shutdown
SW1(config-if-Et1)# end
SW1# show vlan
SW1# show interfaces ethernet 1 switchport
SW1# show interfaces trunk
SW1# show running-config
```

Use `?` at any point to discover the commands or arguments valid there. The Windows console displays help immediately without adding `?` to the command. Up/Down arrows recall command history on Windows, macOS, and Linux. Unique abbreviations such as `conf` and `int et1` work; ambiguous abbreviations fail.

The simulator now includes the command-first Network Foundations pack covering management addressing, VLANs and inter-VLAN routing, STP, LACP/MLAG, routed interfaces, static routes, RIP, OSPFv2, ACL/control-plane/service ACL workflows, foundational QoS, and IPv6 addressing. The exact Academy lab designs will be added only after their command requirements are confirmed.

Examples of state-derived verification commands include:

```text
show vlan [VLAN_ID]
show interfaces status
show interfaces trunk
show interfaces [INTERFACE] switchport
show interfaces [INTERFACE] vlans
show ip interface brief
show ip route
show lldp neighbors
show spanning-tree
show port-channel dense
show mlag
show ip protocols
show ip access-lists
show policy-map
show ipv6 interface brief
show ipv6 route
```

See [docs/network-foundations-command-coverage.md](docs/network-foundations-command-coverage.md) for the lab-by-lab command inventory, placeholders, and topology-dependent limits.

## Test it

```powershell
python -m unittest discover -s tests -v
```

See [docs/architecture.md](docs/architecture.md), [docs/authority.md](docs/authority.md), and [docs/compatibility.md](docs/compatibility.md) for design, evidence, and accuracy limits.

## Study sections and future PDF labs

The browser offers Network Admin Prep, an L1 Certification Study Lab Kit, five note-derived L1 domain sections, and Campus Troubleshooting while retaining the individual practice picker. The note-derived sections are Network Engineering Fundamentals, Arista EOS Fundamentals, Layer 2 Switching Fundamentals, Layer 3 Routing Fundamentals, and Advanced Networking Concepts. They turn the supplied master notes into focused recall checkpoints and link to supported EOS practice; the terminal does not claim to emulate every topology, protocol, or security feature in those notes. The L1 kit is independent practice material, not an official certification exam or emulator; it organizes EOS workflow, VLAN, trunk, campus fault-isolation, and local MLAG study into a repeatable route. Section choices are remembered on this browser; existing server lab saves keep their original IDs. Knowledge checkpoints reveal model answers and do not count as graded lab completions. The terminal remains EOS-only.

Sections live in src/arista_sim/reference/sections.json. Each section has a stable id, title, description, topics, and sources. Each topic references existing lab IDs and optional question/answer checkpoints. A lab may appear in multiple sections without duplicating its progress.

For future supplied PDFs, create a section or extend a topic, split the material into focused labs, and record the document title and page references in each lab brief/objectives. Add simulator checks only for supported behavior; label conceptual checkpoints separately. This is an authoring workflow, not an automatic PDF upload/import feature.
