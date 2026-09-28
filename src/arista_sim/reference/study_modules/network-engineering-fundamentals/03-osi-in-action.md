# 3. OSI in Action

**Official unit:** Network Engineering Fundamentals → Network Introduction

# Learn

Layer 7 provides application services such as HTTP, FTP, SMTP, SSH/Telnet, and RTP. Layer 6 handles representation, encryption/decryption, and compression. Layer 5 establishes, manages, and terminates sessions.

Layer 4 handles handshaking, segmentation, sequencing, retransmission, and flow control; its header includes ports and sequence information. Layer 3 provides IP addressing and routing. Layer 2 uses source/destination MAC addresses and CRC for hop-to-hop delivery. Layer 1 transmits bits on the medium.

```text
Data → Segment → Packet → Frame → Bits
```

Encapsulation adds headers down the stack; de-encapsulation removes them at the receiver.

# Flashcards

**MAC addresses belong to which layer?** Layer 2.  
**IP and routing?** Layer 3.  
**Ports and segmentation?** Layer 4.

# Knowledge Quiz

1. Describe the responsibilities of Layers 1–7.
2. Explain the segment/packet/frame relationship.
3. Explain encapsulation and de-encapsulation.

# Practical Exercise

Trace an application message down the stack and identify the new information added at Layers 4, 3, and 2.

# Mastery Check

- [ ] Associate MAC, IP, and ports with the correct layers.
- [ ] Explain encapsulation in both directions.
