# Architecture and command-pack plan

## Boundaries

- `cli/command_tree.py`: declarative syntax tree, unique-prefix resolution, help, and typed argument parsing.
- `cli/session.py`: mode stack, prompt, command dispatch, and user-visible errors.
- `models/device.py`: structured running and startup state.
- `renderers.py`: derives `show` output and running configuration from state.
- Later `simulation/`: forwarding and topology logic, deliberately absent from Milestone 1.
- Later `labs/`: declarative scenarios and state-based validation, deliberately absent from Milestone 1.

The command transcript is never the source of truth. Commands mutate `DeviceState`; renderers and future validators read that state.

## Command-tree design

Each mode owns a tree of literal and typed-argument nodes. Resolution occurs one token at a time:

1. Exact literal wins.
2. Otherwise a single case-insensitive prefix wins.
3. Multiple literal prefixes are ambiguous.
4. Typed arguments are attempted only when no literal matches.
5. A terminal node invokes a handler; a nonterminal end is incomplete.

Aliases such as `Ethernet`, `Et`, and compact `Et1` are normalized by an interface parser, not by special-casing complete command strings. Contextual help walks the same tree used for execution, preventing help and actual syntax from drifting apart.

## State model

`DeviceState` owns the hostname, VLAN map, interface map, and a deep-copied startup snapshot. VLANs and interfaces are structured dataclasses. The running configuration is rendered deterministically from those objects.

This lets future switching/routing engines depend on the same state without parsing rendered configuration text.

## Testing strategy

- Unit-level CLI sessions exercise transitions, abbreviation, ambiguity, help, incomplete/invalid input, and argument validation.
- State/rendering tests prove commands change structured state and verification output reflects it.
- Persistence tests prove startup state is separate from later running changes.
- A scripted acceptance transcript covers the complete Milestone 1 interaction.
- Future features must pair configuration tests with verification commands and state-based lab validation.

## Baseline acceptance

- The reference transcript in the README succeeds.
- `conf` and `int et1` resolve; `con` is ambiguous.
- `?`, `show ?`, `interface ?`, and `switchport ?` are contextual.
- Wrong-mode, incomplete, and invalid arguments fail without mutating state.
- `show vlan`, interface switchport output, and running-config are derived from state.
- Saving startup configuration creates a distinct snapshot.

