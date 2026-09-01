# G-0183 freeze — G-0181 basis-column 0 lift into the old primary span

Frozen at `2026-09-01T10:15:25Z`, after exploratory discovery and an
exploratory two-evaluator replay of the candidate, but before writing and
executing the repository verifier.  This is a post-discovery verification
freeze.  It is not an outcome-blind discovery preregistration, and the prior
`/tmp` replay is not the promotion gate.

## Frozen candidate

The candidate file is `candidate_identity.json`, SHA-256
`97e2916db4da6f9f76fd3d86fbec7d5ada72c462a66e7a554ccdebf03c21a2ef`.
In function notation it is

\[
\begin{aligned}
10(&q_{447}-q_{511}-q_{1418}-q_{1630}+q_{1757}+q_{2124})={}&
-20p_{1336}+20p_{1722}-2p_{4396}+10p_{4533}-7p_{5341}\\
&&-20p_{7087}-15p_{11134}-30p_{12930}+5p_{14460}+52p_{15947}\\
&&+20p_{16542}-10p_{16701}+2p_{17761}-10p_{18041}+10p_{20675}\\
&&+10p_{22121}-p_{22607}-20p_{22895}-3p_{23096}-p_{23517}+10p_{32861}.
\end{aligned}
\]

The six \(q\)'s are frozen G-0179 STAR-outside-primary records.  The 21
\(p\)'s are frozen G-0113 old-primary records.  Exploratory discovery evaluated
the complete normal forms of all 495 old-primary records of signed mass at
most three, solved a 5,612-coordinate system, and then observed this primitive
integer candidate with left scale ten.  The modular discovery matrices had
rank 215 at each of 1,000,003 and 1,000,033, but this freeze makes **no** claim
that the rational rank is 215.  Promotion rests only on direct exact replay of
the displayed identity.

## Frozen source bindings

| object | SHA-256 |
|---|---|
| candidate identity | `97e2916db4da6f9f76fd3d86fbec7d5ada72c462a66e7a554ccdebf03c21a2ef` |
| G-0181 relation-0 full-normal-form summary | `788c0be7b4889c9e00d550ddca352e25695465d6bf064068df746c129ef4a966` |
| G-0181 exact left-kernel basis | `56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232` |
| G-0113 old-primary solver input | `093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8` |
| G-0179 STAR record census | `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4` |
| G-0109 independent evaluator source | `dfe2638f33c58fd3dfc6c5bd8e6f6ad2059a6eb47986a7e9b76f255b72da2126` |
| G-0109 independent evaluator binary | `e487f78b5f8c4f2f5b3b7764abbb742c6b2a47007d78561e4e125fc829498426` |
| G-0179 evaluator library | `8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73` |
| G-0179 evaluator CLI source | `128093d8f664f70036bec75f82df107413c338703b651206221e8da8fe2ce6e2` |
| G-0179 evaluator binary | `ba629a044408e170235523a6f578c55d3201d7be37bb07acf86e27d409a00824` |

## Fresh verification gate

After this freeze is committed, a fresh verifier must reconstruct all 27
controlled records directly from the two frozen source documents and must not
consume any exploratory normal-form or solve output.  It must:

1. require the 21 primary records to exist in the 163,740-record G-0113
   census, to be loopless, and to have signed mass at most three;
2. require the six STAR records to exist in the 5,773-record G-0179 census and
   each to have exactly one residual loop;
3. run the frozen G-0109 and G-0179 normal-form implementations on one
   canonical 27-record input and require literal equality of all outputs;
4. combine all 11 linear coordinates and every hinge direction appearing in
   any of the 27 complete normal forms with the frozen integer coefficients;
5. require zero exact residual, record the raw union census, and require the
   common semantic digest on both sides to match;
6. add one to the coefficient of \(p_{1336}\) and require a nonzero residual;
7. re-hash every input after the replay and refuse overwrite or binding drift.

Failure of any gate refutes this candidate.  Altering a coefficient or
reselecting a primary record requires a new freeze.

## Consequence if the gate passes

The displayed 21-term right side is an explicit element of the frozen old
primary span \(O\).  Exact equality of complete ordered-chamber normal forms,
together with full \(S_{11}\)-symmetry, proves that the G-0181 basis-column 0
six-term STAR relation lies in \(O\) as a full characteristic-zero function.
This is stronger than agreement on the finite G-0180 restriction panel.

## Strict claim boundary

G-0182 certifies one different G-0181 basis vector.  A successful G-0183
replay would therefore classify exactly 2 of the 478 basis vectors.  It does
not classify the other 476, prove \(\ker(R_{d_0=1})\subseteq O\), establish the
full STAR quarantine, decide MAX11 membership, prove primary-family or neural
ansatz completeness, or imply any unrestricted depth/width lower bound.

The creation consumer is the next exact quarantine decision; this freeze
blocks promotion of relation 0 without a source-bound independent replay.  It
retires if the candidate is refuted or superseded by a stronger audited batch
certificate.
