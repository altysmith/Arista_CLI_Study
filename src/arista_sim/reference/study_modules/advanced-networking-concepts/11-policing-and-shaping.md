# 11. Policing and Shaping

# Learn

Policing enforces a committed information rate (CIR) and drops traffic exceeding the allowed rate, with burst capacity allowing temporary excess after idle periods.

Shaping controls outbound rate by buffering and releasing packets smoothly instead of immediately dropping them. It introduces delay and uses queueing to meet a target rate.

# Knowledge Quiz

1. Compare policing and shaping.
2. Define CIR and burst.
3. Which mechanism buffers excess traffic?

# Practical Exercise

Choose policing or shaping at a 1-Gbps interface facing a 200-Mbps service and explain the packet behavior.

# Mastery Check

- [ ] Predict drop, buffer, and delay behavior.
