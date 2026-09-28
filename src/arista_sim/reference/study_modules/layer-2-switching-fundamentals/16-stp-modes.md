# 16. STP Modes

# Learn

Classic STP (802.1D) uses blocked ports and can take roughly 50 seconds after timeout plus listening/learning. RSTP (802.1W) uses alternate ports for faster recovery.

PVST builds a tree per VLAN, enabling different roots but producing many BPDUs. Rapid PVST adds rapid behavior but retains per-VLAN BPDU scale. MST (802.1S), used in the Arista notes, groups VLANs into instances so each instance elects a root and sends one set of BPDUs.

# Knowledge Quiz

1. Compare STP and RSTP recovery.
2. State PVST’s benefit and scaling issue.
3. Explain how MST instances reduce BPDU load.

# Practical Exercise

Place VLANs 10–20 in MST instance 1 and VLANs 30–40 in instance 2; identify the number of independent root elections.

# Mastery Check

- [ ] Compare STP, RSTP, PVST, Rapid PVST, and MST.
