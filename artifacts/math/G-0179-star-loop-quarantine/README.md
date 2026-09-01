# G-0179 — exact STAR loop quarantine

Status: **the preregistered full-rank gate failed**.  The exact square is
singular: it contains 90 duplicate-column pairs and two duplicate-row pairs.
Its exact modular rank is 5,291 over each preregistered prime, 1,000,003 and
1,000,033.  Therefore the conditional theorem below was not promoted.

The high-leverage observation is a support separation.  Every one of the
163,740 old primary signed-\(W\) columns is loopless, so it has no
ordered-chamber hinge with \(d_0\ne0\).  Every one of the 5,773 frozen
`STAR`-outside-primary classes has exactly one residual loop, so it has
candidate hinges with \(d_0=1\).  `MAX11` is linear on the ordered chamber and
has zero on all such hinges.

Two `STAR` classes are already in the old space: sequence 1548 is exactly
\(5E\), and sequence 4259 is exactly
\(2p_{5341}-p_{66223}\).  A target-blind structural matching selected 5,771
distinct active primitive \(d_0=1\) directions for the remaining 5,771
classes.  The matching alone proves nothing about rank.  The exact determinant
was the gate, and it vanished modulo both frozen primes.

Had the frozen square been nonsingular, the remaining `STAR` columns would add a direct
5,771-dimensional summand, but no combination of that summand can help any
target with zero selected hinges.  Therefore, within the full frozen
common-apex `STAR` family, `MAX11` membership is exactly the same as membership
in the old primary span augmented by the two pure ordered-chamber-linear,
zero-interior-hinge carriers \(5E,5L\).

That is a target-membership theorem for this frozen extension, not a claim that
`STAR` adds no functions, not a proof that the old family misses `MAX11`, and
not an unrestricted neural-network lower bound.

The original outcome-blind theorem, hashes, commands, and branches remain
unaltered in [PREREGISTRATION.md](PREREGISTRATION.md).  The exact outcome and
its claim boundary are recorded in [RESULT.md](RESULT.md).  A separately
frozen expansion may still test whether additional active \(d_0=1\) directions
make the full restriction injective; that would be a new experiment, not a
reinterpretation of this failed gate.
