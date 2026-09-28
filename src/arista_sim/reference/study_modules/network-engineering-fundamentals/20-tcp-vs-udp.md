# 20. TCP vs UDP

**Official unit:** Network Engineering Fundamentals → Transport and Application Layer

# Learn

TCP provides a connection-oriented reliable byte stream using connection establishment, sequence numbers, acknowledgments, retransmission, ordered delivery, and receive flow control.

UDP provides a simpler connectionless datagram service without TCP-style establishment, reliable delivery, ordered byte stream, retransmission, or receive-window flow control.

```text
TCP handshake: SYN → SYN-ACK → ACK
```

UDP has less built-in machinery, but it is not universally faster; performance also depends on latency, loss, congestion, application design, encryption, retransmission, and server performance.

# Flashcards

**Connection-oriented protocol?** TCP.  
**Connectionless protocol?** UDP.  
**TCP handshake?** SYN, SYN-ACK, ACK.

# Knowledge Quiz

1. Compare TCP and UDP services.
2. Explain the handshake.
3. Explain why UDP is not automatically faster.

# Practical Exercise

For a failed TCP service, determine whether SYN was sent, SYN-ACK returned, and ACK completed. If the handshake succeeds, move toward the application.

# Mastery Check

- [ ] Compare TCP and UDP accurately.
- [ ] Troubleshoot a basic TCP handshake.
