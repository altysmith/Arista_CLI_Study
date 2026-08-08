# Arista EOS Network Foundations Simulator

A local, dependency-free training simulator that teaches EOS CLI discovery and configuration workflow. Milestone 1 implements a small but stateful EOS-style shell; it does not emulate EOS or switch hardware.

## Run it

Double-click `run_simulator.bat`, or run:

```powershell
python -m arista_sim
```

If the package has not been installed, the batch file and the command above use the repository's `src` directory directly.

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
SW1# show running-config
```

Use `?` at any point to discover the commands or arguments valid there. The Windows console displays help immediately without adding `?` to the command. Up/Down arrows recall command history. Unique abbreviations such as `conf` and `int et1` work; ambiguous abbreviations fail.

## Test it

```powershell
python -m unittest discover -s tests -v
```

See [docs/architecture.md](docs/architecture.md), [docs/authority.md](docs/authority.md), and [docs/compatibility.md](docs/compatibility.md) for design, evidence, and accuracy limits.
