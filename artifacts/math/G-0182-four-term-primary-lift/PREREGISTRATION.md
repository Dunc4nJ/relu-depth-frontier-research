# G-0182 freeze — first four-term kernel lift into the old primary span

Frozen at `2026-09-01T10:01:10Z`, after exploratory discovery of the candidate
identity but before an independent replay.  This is a post-discovery
verification freeze, not an outcome-blind discovery preregistration.

## Frozen candidate

The candidate file is `candidate_identity.json`.  In function notation it is

\[
q_{821}-q_{1630}-q_{2986}+q_{3944}
=-2p_{11134}-p_{12930}+p_{16701}+p_{22121}+p_{24222}
+p_{36968}-p_{122205}.
\]

The four (q)'s are frozen G-0179 STAR-outside-primary records.  The seven
(p)'s are frozen G-0113 old-primary records.  The exploratory route selected
all old primary records of signed mass at most two, evaluated their complete
normal forms, and solved a 340-coordinate exact system.  That route had already
reported a zero residual before this freeze; it is not the promotion gate.

## Decisive frozen inputs

| object | SHA-256 |
|---|---|
| candidate identity | `b345639a47faf6b18d728648f891b913a55a7217a741b9537187da2dd3751d47` |
| G-0113 old-primary solver input | `093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8` |
| G-0179 STAR record census | `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4` |
| G-0109 independent evaluator source | `dfe2638f33c58fd3dfc6c5bd8e6f6ad2059a6eb47986a7e9b76f255b72da2126` |
| G-0109 independent evaluator binary | `e487f78b5f8c4f2f5b3b7764abbb742c6b2a47007d78561e4e125fc829498426` |
| G-0179 evaluator library | `8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73` |
| G-0179 evaluator CLI source | `128093d8f664f70036bec75f82df107413c338703b651206221e8da8fe2ce6e2` |
| G-0179 evaluator binary | `ba629a044408e170235523a6f578c55d3201d7be37bb07acf86e27d409a00824` |

## Independent promotion gate

A fresh verifier must reconstruct the eleven controlled records directly from
the two frozen source documents and must not consume the exploratory solve's
normal-form output.  It must then:

1. confirm that the seven primary sequences are present in the G-0113 primary
   census, are loopless, and match the controlled record bytes;
2. confirm that the four STAR sequences match the G-0179 census;
3. run both frozen normal-form implementations on the same canonical input;
4. require literal equality of their eleven complete normal forms;
5. combine all 11 linear coordinates and every hinge direction in the union
   using the candidate coefficients, and require the exact residual to be
   empty;
6. record the union-coordinate census and a canonical semantic digest;
7. add one to the coefficient of (p_{11134}) and require a nonzero residual;
8. re-hash every input after the replay.

Failure of any gate is a failed candidate.  Reselecting old-primary columns or
altering a coefficient requires a new freeze.

## Consequence if the gate passes

The right side is an explicit element of the old primary span (O).  Therefore
the support-four exact restriction relation from G-0181 lifts to a complete
characteristic-zero function identity in (O).  This is a full-function
statement, not a finite-panel fit.

## Claim boundary

One lift does not establish that all 478 exact G-0181 kernel vectors lie in
(O), so it does not yet prove the STAR quarantine theorem.  It also does not
decide MAX11 membership in (O), ansatz completeness, or an unrestricted
neural-network lower bound.  Its value is that it validates a concrete
kernel-to-(O) mechanism that can now be generalized.
