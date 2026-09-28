# 5. Introduction to Trunking Protocols 802.1Q

# Learn

Access ports carry one VLAN and normally connect endpoints. Trunks carry multiple VLANs between infrastructure devices. 802.1Q adds a VLAN tag so the receiving switch can place a frame into the correct VLAN; the 12-bit VLAN ID supports 4094 usable VLAN IDs in the notes.

The native VLAN crosses an 802.1Q trunk untagged. Trunks allow all VLANs by default but can restrict allowed VLANs.

# Flashcards

**Access versus trunk?** One VLAN versus multiple VLANs.  
**Native VLAN traffic?** Untagged on the trunk.

# Knowledge Quiz

1. Why is tagging needed?
2. Explain the native VLAN.
3. Why restrict allowed VLANs?

# Practical Exercise

Trace a tagged VLAN 10 frame across a trunk and describe tag removal before an access port.

# Mastery Check

- [ ] Explain access, trunk, tagging, native, and allowed VLANs.
