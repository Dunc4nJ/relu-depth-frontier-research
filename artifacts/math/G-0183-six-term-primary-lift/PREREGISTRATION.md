# G-0183 freeze — second exact kernel-to-primary lift candidate

Frozen at `2026-09-01T10:15:03Z`, after exploratory discovery of the
candidate identity but before the independent replay. This is a post-discovery
verification freeze, not an outcome-blind discovery preregistration.

## Frozen candidate

The candidate file is `candidate_identity.json`, SHA-256
`df295599ac4e0f3fc94666198d9aa075b081866efa8a7e5dcf43a67edb76220e`.
In function notation it is

\[
\begin{aligned}
10(q_{447}-q_{511}-q_{1418}-q_{1630}+q_{1757}+q_{2124})
={}&-20p_{1336}+20p_{1722}-2p_{4396}+10p_{4533}-7p_{5341}\\
&-20p_{7087}-15p_{11134}-30p_{12930}+5p_{14460}+52p_{15947}\\
&+20p_{16542}-10p_{16701}+2p_{17761}-10p_{18041}+10p_{20675}\\
&+10p_{22121}-p_{22607}-20p_{22895}-3p_{23096}-p_{23517}
  +10p_{32861}.
\end{aligned}
\]

The six \(q\)'s are frozen G-0179 STAR-outside-primary records. The 21
\(p\)'s are frozen G-0113 old-primary records of signed mass at most three.
The left side is ten times G-0181 rational-kernel basis column 0.

The exploratory route evaluated all 495 mass-at-most-three old-primary
records, observed equal modular ranks for the primary and target-augmented
systems at two primes, and then found and exactly replayed the displayed
rational solution. Those discovery computations had already reported zero
residual; they are not the promotion gate.

## Decisive frozen inputs

| object | SHA-256 |
|---|---|
| candidate identity | `df295599ac4e0f3fc94666198d9aa075b081866efa8a7e5dcf43a67edb76220e` |
| G-0113 old-primary solver input | `093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8` |
| G-0179 STAR record census | `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4` |
| G-0109 evaluator source | `dfe2638f33c58fd3dfc6c5bd8e6f6ad2059a6eb47986a7e9b76f255b72da2126` |
| G-0109 evaluator binary | `e487f78b5f8c4f2f5b3b7764abbb742c6b2a47007d78561e4e125fc829498426` |
| G-0179 evaluator library | `8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73` |
| G-0179 evaluator CLI source | `128093d8f664f70036bec75f82df107413c338703b651206221e8da8fe2ce6e2` |
| G-0179 evaluator binary | `ba629a044408e170235523a6f578c55d3201d7be37bb07acf86e27d409a00824` |

## Independent promotion gate

A fresh verifier, written only after this freeze, must reconstruct all 27
controlled records directly from the two source censuses and must not read the
exploratory normal forms, matrix, or solution receipt. It must:

1. confirm exact candidate bytes and all frozen source hashes;
2. confirm that all 21 primary records belong to the old-primary census, are
   loopless, and have signed mass at most three;
3. confirm that all six STAR records have exactly one residual loop;
4. run both frozen complete-normal-form implementations on one canonical input
   and require literal equality of all 27 outputs;
5. combine every hinge direction in the full union and all 11 linear
   coordinates with the frozen coefficients, requiring an exactly zero
   characteristic-zero residual;
6. record the raw coordinate census and canonical semantic digests;
7. add one to the coefficient of \(p_{1336}\) and require a nonzero residual;
8. re-hash every frozen input after replay.

Any failed gate rejects this candidate. Altering a coefficient or selecting a
different primary column requires a new freeze.

## Consequence if the gate passes

The displayed right side is explicitly in the frozen old-primary span \(O\).
Therefore this G-0181 basis vector lifts from the finite restriction kernel to
a complete characteristic-zero CPWL function identity in \(O\). Together
with G-0182, this would certify two independent kernel directions in \(O\).

## Claim boundary

Even if certified, two directions do not classify the 478-dimensional exact
G-0181 kernel. The result would not prove the full STAR quarantine, decide
MAX11 membership in \(O\), establish ansatz completeness, or give an
unrestricted neural-network lower bound.
