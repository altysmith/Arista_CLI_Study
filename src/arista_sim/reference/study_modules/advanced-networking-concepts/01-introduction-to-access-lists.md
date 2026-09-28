# 1. Introduction to Access Lists

# Learn

ACLs filter or classify traffic using header information at Layers 3 and 4. Rules are processed top-down by sequence number, stop on first match, and end with an implicit deny. Put specific matches before general ones.

Create the ACL, then apply it to an interface in the correct inbound or outbound direction.

# Knowledge Quiz

1. Explain implicit deny and exit-on-match.
2. Why does rule order matter?
3. How does traffic direction affect placement?

# Practical Exercise

Deny one host, permit the rest of its subnet, and identify the correct interface direction.

# Mastery Check

- [ ] Predict ACL results from sequence and direction.
