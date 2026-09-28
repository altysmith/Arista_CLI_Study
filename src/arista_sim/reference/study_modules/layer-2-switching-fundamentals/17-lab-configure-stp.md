# 17. LAB — Configure STP

# Lab Goal

Verify and influence a loop-free STP topology, then test reconvergence.

# Tasks

1. Build a redundant three-switch topology.
2. Run `show spanning-tree` on every switch.
3. Record the root bridge and each root, designated, and blocked/alternate port.
4. Adjust bridge priority to make the intended switch root.
5. Recheck roles and forwarding state.
6. Disable the active root-port link and observe the alternate path.
7. Restore the link and document reconvergence.

# Success Criteria

- [ ] Intended root elected.
- [ ] One loop-free forwarding topology exists.
- [ ] Port roles match expected costs.
- [ ] Connectivity survives the tested failure after convergence.
