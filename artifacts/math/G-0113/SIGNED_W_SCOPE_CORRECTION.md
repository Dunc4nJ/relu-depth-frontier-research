# Scope correction for the G-0113c v1 signed-W census

The frozen v1 producer and its output use phrases such as "semantic orbit" for
the common-edge-cancelled signed-W certificate.  Read those phrases narrowly:
they refer only to the nonlinear signed hinge part, up to S11 relabeling and
global sign reversal.  They do **not** identify complete graphical atom
columns.

If a full pair has branches `C+A` and `C+B`, then

```text
max(C+A,C+B) = C + max(A,B).
```

Cancelling `C` preserves the nonlinear comparison but discards the additive
common-edge contribution.  Consequently, two v1 records with the same signed-W
certificate can still differ as complete ordered-cone columns when their
common loop/nonloop content differs.  The v1 counts and map remain exact for
the stated nonlinear quotient and useful as a coarsening, but a later exact
solver must either:

1. split columns by an uncancelled full pair-template certificate; or
2. add and prove sufficient common-edge basis columns so the discarded linear
   contributions are controlled independently.

G-0113 adopts option 1 in a separately preregistered v2 refinement.  No MAX11
target rank was evaluated between v1 and this correction.
