# 11. Link-State Routing

# Learn

OSPF and IS-IS are link-state protocols. Each router develops a complete topology view. OSPF discovers neighbors with multicast Hellos, builds an adjacency table, floods LSAs, builds a common LSDB, constructs a topology tree, runs Dijkstra SPF, and installs best routes.

OSPF cost reflects bandwidth; higher bandwidth means lower cost. Topology changes trigger immediate LSAs rather than waiting for the periodic LSDB refresh.

Useful verification includes `show ip ospf neighbor`.

# Knowledge Quiz

1. Explain Hello, adjacency, LSA, LSDB, SPF, and route installation.
2. Compare link state with distance vector.
3. How does bandwidth affect OSPF cost?

# Practical Exercise

From a four-router topology, list the LSAs each router originates and explain how every router builds the same map.

# Mastery Check

- [ ] Explain OSPF startup, convergence, and change handling.
